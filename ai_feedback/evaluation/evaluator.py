"""
Feedback evaluator that calls AI functions directly and logs via Langfuse Datasets.

Each video/test-case is a *dataset item* (input + expected_output).
Each experiment run (e.g. "baseline") becomes a *dataset run* column in
Langfuse, with per-item scores and automatic run-level aggregation.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from langfuse import Langfuse
from loguru import logger

from ai_feedback.ai import get_feedback_from_video
from ai_feedback.constants.prompts import VIDEO_ANALYSIS_PROMPT, SPEECH_ANALYSIS_SKIPPED
from ai_feedback.models import ScriptDetails
from evaluation import config
from evaluation.config import SIMILARITY_THRESHOLD
from evaluation.extractor import (
    extract_style_coaching,
    extract_style_coaching_by_category,
)
from evaluation.similarity import SimilarityCalculator

DATASET_NAME = "ai_feedback_eval"


def _coaching_has_content(s: str) -> bool:
    """True when the coaching string contains more than just category labels."""
    return bool(re.sub(r'[^:]+:', '', s).strip())


def _prompt_snapshot(prompt: str) -> dict:
    """Return a compact fingerprint + preview of a prompt string.

    Stored in Langfuse metadata so you can always tell which exact prompt
    version produced a given evaluation run.
    """
    digest = hashlib.sha256(prompt.encode()).hexdigest()[:12]
    return {
        "prompt_hash": digest,
        "prompt_preview": prompt[:300].strip(),
        "prompt_full": prompt,
    }


@dataclass
class EvaluationResult:
    """Result of a single test case evaluation."""

    test_set: str
    test_case: str
    video_path: str
    generated_coaching: str
    reference_coaching: str
    overall_similarity: float
    category_similarities: Dict[str, float]
    passed: bool
    session_id: str
    accuracy: float
    confidence: float


class FeedbackEvaluator:
    """Evaluates AI feedback quality by comparing against reference answers."""

    def __init__(
            self,
            similarity_calculator: SimilarityCalculator,
            langfuse_client: Optional[Langfuse] = None,
            experiment_name: str = "baseline",
    ):
        self.similarity_calculator = similarity_calculator
        self.langfuse_client = langfuse_client
        self.experiment_name = experiment_name
        self.trace_name = "evaluation"
        # Stable tag for every trace produced in this single evaluator run,
        # format: evaluation_YYYYMMDD_HHMMSS
        self.pipeline_run = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ------------------------------------------------------------------
    # Dataset setup
    # ------------------------------------------------------------------

    def ensure_dataset(self) -> None:
        """Get-or-create the Langfuse dataset (safe to call on every run)."""
        if not self.langfuse_client:
            return
        try:
            # Try to fetch first — if it exists we get it back without error
            self.langfuse_client.get_dataset(DATASET_NAME)
            logger.info(f"Dataset '{DATASET_NAME}' already exists — reusing it")
        except Exception:
            # Dataset doesn't exist yet — create it
            try:
                self.langfuse_client.create_dataset(
                    name=DATASET_NAME,
                    description=(
                        "AI feedback evaluation dataset. "
                        "Each item is one video test case with its reference coaching answer."
                    ),
                )
                logger.info(f"Dataset '{DATASET_NAME}' created in Langfuse")
            except Exception as create_err:
                logger.error(f"Failed to create dataset '{DATASET_NAME}': {create_err}")
                raise

    def upsert_dataset_items(self) -> None:
        """Sync all video test-cases from disk into the Langfuse dataset.

        Uses the stable ``id`` field (``set_X/Y``) so repeated runs are
        idempotent: existing items are **updated** with the latest payload
        and reference answers (so changes on disk are reflected immediately),
        and new items are created automatically.
        """
        if not self.langfuse_client:
            return

        sets_dir = Path(config.SETS_DIR)
        if not sets_dir.exists():
            logger.warning(f"Sets directory not found: {sets_dir}")
            return

        for set_dir in sorted(sets_dir.iterdir()):
            if not set_dir.is_dir():
                continue
            test_set = set_dir.name

            for video_file in sorted(set_dir.glob("*.*")):
                test_case = video_file.stem
                item_id = f"{test_set}/{test_case}"

                # Load payload
                payload_path = Path(config.CHALLENGES_DIR) / f"payload_{test_case}.json"
                if not payload_path.exists():
                    logger.warning(f"Payload not found, skipping item: {item_id}")
                    continue

                with open(payload_path) as f:
                    payload = json.load(f)

                # Load reference answer
                answer_path = Path(config.ANSWERS_DIR) / test_set / f"{test_case}.json"
                if not answer_path.exists():
                    logger.warning(f"Reference answer not found, skipping item: {item_id}")
                    continue

                with open(answer_path) as f:
                    reference_answer = json.load(f)

                try:
                    # Langfuse upserts by `id`: if the item exists its
                    # input / expected_output are updated in-place, so
                    # changes to payloads or reference answers are picked
                    # up automatically on every run.
                    self.langfuse_client.create_dataset_item(
                        dataset_name=DATASET_NAME,
                        id=item_id,
                        input={
                            "video_path": str(video_file),
                            "test_set": test_set,
                            "test_case": test_case,
                            "question": payload.get("question", ""),
                            "keyElements": payload.get("keyElements", []),
                            "briefing": payload.get("briefing", ""),
                        },
                        expected_output=reference_answer,
                    )
                    logger.debug(f"Dataset item upserted: {item_id}")
                except Exception as e:
                    logger.warning(f"Failed to upsert dataset item {item_id}: {e}")

        logger.info(
            f"Dataset items synced to '{DATASET_NAME}' "
            f"(new items created, changed items updated, unchanged items skipped by Langfuse)"
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    async def evaluate_test_case(
            self,
            test_set: str,
            test_case: str,
            video_path: str,
            payload: Dict[str, Any],
            reference_answer: Dict[str, str],
            language: str = "English",
    ) -> EvaluationResult:
        """Evaluate a single test case and return the result.

        If a Langfuse client is available, the trace is linked to the
        dataset item via ``item.run()`` and scores are attached automatically.
        """
        logger.info(f"Evaluating {test_set}/{test_case}")

        script_details = ScriptDetails(
            question=payload.get("question", ""),
            keyElements=payload.get("keyElements", []),
            briefing=payload.get("briefing", ""),
        )

        result = await get_feedback_from_video(
            video_filename=video_path,
            script_details=script_details,
            user_id=payload.get("user_id", "evaluation"),
            tags=payload.get("tags", []),
            language=language,
        )

        feedback = result["feedback"]
        average_score = result["accuracy"]
        confidence_score = result.get("confidence", 0)
        session_id = result["session_id"]

        logger.info(f"Generated feedback for {test_set}/{test_case}, session_id: {session_id}")

        # Map structured categories for comparison
        generated_categories = {
            "rhythm_and_timing": result.get("rhythm_and_timing").assessment if result.get("rhythm_and_timing") else "",
            "volume_and_tone": result.get("volume_and_tone").assessment if result.get("volume_and_tone") else "",
            "emotional_authenticity": result.get("emotional_authenticity").assessment if result.get("emotional_authenticity") else "",
            "confidence_detail": result.get("confidence_detail").assessment if result.get("confidence_detail") else "",
        }

        # Normalize "skipped" message to empty string for comparison
        for cat, text in generated_categories.items():
            if SPEECH_ANALYSIS_SKIPPED in text:
                generated_categories[cat] = ""

        # Prepare reference categories and normalize them for comparison
        reference_categories = {}
        for key, val in reference_answer.items():
            if isinstance(val, dict) and "assessment" in val:
                reference_categories[key] = val["assessment"]
            elif isinstance(val, str) and key in generated_categories:
                # Handle case where reference is just a string and key matches
                reference_categories[key] = val

        generated_coaching = "\n\n".join(
            [f"{cat}: {text}" for cat, text in generated_categories.items()]
        )

        reference_coaching = "\n\n".join(
            [f"{cat}: {text}" for cat, text in reference_categories.items()]
        )

        if not _coaching_has_content(generated_coaching) and not _coaching_has_content(reference_coaching):
            # Both sides are empty — correct match.
            overall_similarity = 1.0
        elif generated_coaching and reference_coaching:
            overall_similarity = self.similarity_calculator.calculate_similarity(
                generated_coaching, reference_coaching
            )
        else:
            overall_similarity = 0.0

        category_similarities: Dict[str, float] = {}

        for category in generated_categories:
            generated_text = generated_categories.get(category, "")
            reference_text = reference_categories.get(category, "")
            if not generated_text and not reference_text:
                # Both sides empty — correct "nothing to assess" prediction.
                category_similarities[category] = 1.0
            elif generated_text and reference_text:
                category_similarities[category] = self.similarity_calculator.calculate_similarity(
                    generated_text, reference_text
                )
            else:
                # One side has content, the other doesn’t — genuine mismatch.
                category_similarities[category] = 0.0

        passed = overall_similarity >= SIMILARITY_THRESHOLD

        return EvaluationResult(
            test_set=test_set,
            test_case=test_case,
            video_path=video_path,
            generated_coaching=generated_coaching,
            reference_coaching=reference_coaching,
            overall_similarity=overall_similarity,
            category_similarities=category_similarities,
            passed=passed,
            session_id=session_id,
            accuracy=average_score,
            confidence=confidence_score,
        )

    async def evaluate_test_case_with_dataset(
            self,
            test_set: str,
            test_case: str,
            video_path: str,
            payload: Dict[str, Any],
            reference_answer: Dict[str, str],
            language: str = "English",
    ) -> EvaluationResult:
        """Evaluate one test case, linking the trace to the Langfuse dataset run.

        Uses ``item.run()`` so the trace is automatically associated with the
        dataset item and the experiment run, giving you the table view in Langfuse.
        """
        item_id = f"{test_set}/{test_case}"

        if not self.langfuse_client:
            # No Langfuse — fall back to plain evaluation
            return await self.evaluate_test_case(
                test_set, test_case, video_path, payload, reference_answer, language
            )

        try:
            dataset = self.langfuse_client.get_dataset(DATASET_NAME)
            dataset_item = next((i for i in dataset.items if i.id == item_id), None)
        except Exception as e:
            logger.warning(f"Could not fetch dataset item {item_id}: {e}")
            dataset_item = None

        if dataset_item is None:
            logger.warning(f"Dataset item '{item_id}' not found — running without dataset link")
            return await self.evaluate_test_case(
                test_set, test_case, video_path, payload, reference_answer, language
            )

        result: Optional[EvaluationResult] = None

        try:
            _ps = _prompt_snapshot(VIDEO_ANALYSIS_PROMPT)
            with dataset_item.run(
                    # pipeline_run is unique per invocation (timestamp generated in
                    # __init__), so each `make evaluate` call creates a NEW column
                    # in Langfuse Dataset → Runs instead of overwriting the previous one.
                    run_name=self.pipeline_run,
                    run_description=f"Experiment: {self.experiment_name} | {self.pipeline_run}",
                    run_metadata={
                        "experiment": self.experiment_name,
                        "threshold": SIMILARITY_THRESHOLD,
                        "pipeline_run": self.pipeline_run,
                        # Full prompt snapshot — one authoritative copy per run
                        "video_analysis_prompt_hash": _ps["prompt_hash"],
                        "video_analysis_prompt_preview": _ps["prompt_preview"],
                        "video_analysis_prompt_full": _ps["prompt_full"],
                    },
            ) as root_span:
                result = await self.evaluate_test_case(
                    test_set, test_case, video_path, payload, reference_answer, language
                )

                # Attach the output to the span
                root_span.update(
                    name=self.trace_name,
                    output={
                        "generated_coaching": result.generated_coaching,
                        "overall_similarity": result.overall_similarity,
                        "passed": result.passed,
                    },
                    metadata={
                        "session_id": result.session_id,
                        "accuracy": result.accuracy,
                        "confidence": result.confidence,
                        # Lightweight reference — hash lets you cross-check the run_metadata
                        "video_analysis_prompt_hash": _ps["prompt_hash"],
                    },
                    tags=[self.experiment_name, test_set, self.pipeline_run],
                )

                # Score this item within the run
                root_span.score_trace(
                    name="overall_similarity",
                    value=result.overall_similarity,
                    comment=f"Threshold: {SIMILARITY_THRESHOLD}",
                )
                root_span.score_trace(
                    name="passed",
                    value=1.0 if result.passed else 0.0,
                    comment=f"Threshold: {SIMILARITY_THRESHOLD}",
                )
                for category, similarity in result.category_similarities.items():
                    score_name = (
                        f"similarity_{category.lower().replace(' ', '_').replace('&', 'and')}"
                    )
                    root_span.score_trace(name=score_name, value=similarity)

            logger.info(
                f"Logged to dataset run '{self.experiment_name}': "
                f"{item_id} → similarity={result.overall_similarity:.3f}"
            )

        except Exception as e:
            logger.warning(f"Failed to log dataset run for {item_id}: {e}")
            if result is None:
                result = await self.evaluate_test_case(
                    test_set, test_case, video_path, payload, reference_answer, language
                )

        return result

    async def evaluate_set(
            self, test_set: str, language: str = "English"
    ) -> List[EvaluationResult]:
        """Evaluate all test cases in a test set."""
        results = []

        sets_dir = Path(config.SETS_DIR)
        set_dir = sets_dir / test_set

        if not set_dir.exists():
            logger.error(f"Test set directory not found: {set_dir}")
            return results

        video_files = sorted(set_dir.glob("*.*"))
        if not video_files:
            logger.warning(f"No video files found in {set_dir}")
            return results

        for video_file in video_files:
            test_case = video_file.stem

            payload_path = Path(config.CHALLENGES_DIR) / f"payload_{test_case}.json"
            if not payload_path.exists():
                logger.error(f"Payload file not found: {payload_path}")
                continue

            with open(payload_path) as f:
                payload = json.load(f)

            answer_path = Path(config.ANSWERS_DIR) / test_set / f"{test_case}.json"
            if not answer_path.exists():
                logger.warning(f"Reference answer not found: {answer_path}")
                continue

            with open(answer_path) as f:
                reference_answer = json.load(f)

            try:
                result = await self.evaluate_test_case_with_dataset(
                    test_set=test_set,
                    test_case=test_case,
                    video_path=str(video_file),
                    payload=payload,
                    reference_answer=reference_answer,
                    language=language,
                )
                results.append(result)

                status = "✓ PASS" if result.passed else "✗ FAIL"
                logger.info(
                    f"{test_set}/{test_case}: {result.overall_similarity:.3f} — {status}"
                )

            except Exception as e:
                logger.error(f"Failed to evaluate {test_set}/{test_case}: {e}")
                continue

        return results

    def print_summary(self, results: List[EvaluationResult]) -> None:
        """Print evaluation summary to the terminal."""
        if not results:
            logger.info("No results to summarize")
            return

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        avg_similarity = sum(r.overall_similarity for r in results) / total

        logger.info(
            f"""
            {'=' * 80}
            EVALUATION SUMMARY — Experiment: {self.experiment_name}
            {'=' * 80}
            Total test cases : {total}
            Passed           : {passed} ({passed / total * 100:.1f}%)
            Failed           : {total - passed} ({(total - passed) / total * 100:.1f}%)
            Avg similarity   : {avg_similarity:.3f}
            Threshold        : {SIMILARITY_THRESHOLD}
            {'-' * 80}
            {'Test Case':<25} {'Similarity':<12} {'Status'}
            {'-' * 80}"""
        )

        for r in results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            test_name = f"{r.test_set}/{r.test_case}"
            logger.info(f"{test_name:<25} {r.overall_similarity:<12.3f} {status}")

        logger.info("=" * 80 + "\n")
