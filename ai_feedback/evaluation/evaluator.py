"""
Feedback evaluator that calls AI functions directly instead of via HTTP.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

from langfuse import Langfuse
from loguru import logger

from ai_feedback.ai import get_feedback_from_video
from ai_feedback.models import ScriptDetails
from evaluation import config
from evaluation.config import SIMILARITY_THRESHOLD
from evaluation.extractor import (
    extract_style_coaching,
    extract_style_coaching_by_category,
)
from evaluation.similarity import SimilarityCalculator


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
        """
        Initialize evaluator.

        Args:
            similarity_calculator: Calculator for semantic similarity
            langfuse_client: Optional Langfuse client for tracking
            experiment_name: Name of the experiment for tracking
        """
        self.similarity_calculator = similarity_calculator
        self.langfuse_client = langfuse_client
        self.experiment_name = experiment_name

    async def evaluate_test_case(
        self,
        test_set: str,
        test_case: str,
        video_path: str,
        payload: Dict[str, Any],
        reference_answer: Dict[str, str],
        language: str = "English",
    ) -> EvaluationResult:
        """
        Evaluate a single test case.

        Args:
            test_set: Name of the test set
            test_case: Test case identifier
            video_path: Path to video file
            payload: Feedback input payload
            reference_answer: Reference coaching answer
            language: Language for feedback generation

        Returns:
            EvaluationResult with similarity scores and metadata
        """
        logger.info(f"Evaluating {test_set}/{test_case}")

        # Create script details from payload
        script_details = ScriptDetails(
            question=payload.get("question", ""),
            keyElements=payload.get("keyElements", []),
            briefing=payload.get("briefing", ""),
        )

        # Generate feedback using AI function directly
        (
            feedback,
            average_score,
            confidence_score,
            rhythm_timing,
            volume_tone,
            emotional_authenticity,
            confidence_detail,
            session_id,
        ) = await get_feedback_from_video(
            video_filename=video_path,
            script_details=script_details,
            user_id=payload.get("user_id", "evaluation"),
            tags=payload.get("tags", []),
            language=language,
        )

        logger.info(
            f"Generated feedback for {test_set}/{test_case}, session_id: {session_id}"
        )

        # Extract style coaching from generated feedback
        generated_coaching = extract_style_coaching(feedback)

        if not generated_coaching:
            logger.warning(
                f"Could not extract style coaching from feedback for {test_set}/{test_case}"
            )
            logger.debug(
                f"Feedback content:\n{feedback[:500]}..."
            )  # Show first 500 chars
            generated_coaching = ""

        # Prepare reference coaching text
        reference_coaching = "\n\n".join(
            [f"{category}: {text}" for category, text in reference_answer.items()]
        )

        # Calculate overall similarity
        overall_similarity = 0.0
        if generated_coaching and reference_coaching:
            overall_similarity = self.similarity_calculator.calculate_similarity(
                generated_coaching, reference_coaching
            )

        # Calculate category-wise similarities
        category_similarities = {}
        generated_categories = extract_style_coaching_by_category(feedback)

        for category, reference_text in reference_answer.items():
            generated_text = generated_categories.get(category, "")

            if generated_text and reference_text:
                similarity = self.similarity_calculator.calculate_similarity(
                    generated_text, reference_text
                )
                category_similarities[category] = similarity
            else:
                category_similarities[category] = 0.0

        # Determine if passed
        passed = overall_similarity >= SIMILARITY_THRESHOLD

        # Create result
        result = EvaluationResult(
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

        # Log to Langfuse if available
        if self.langfuse_client:
            self._log_to_langfuse(result, payload, feedback)

        return result

    def _log_to_langfuse(
        self, result: EvaluationResult, payload: Dict[str, Any], full_feedback: str
    ):
        """Log evaluation result to Langfuse (v3 API)."""
        try:
            trace_id = self.langfuse_client.create_trace_id()

            # Create the trace via a span
            with self.langfuse_client.start_as_current_span(
                name=f"eval_{result.test_set}_{result.test_case}",
                input={"video_path": result.video_path, "payload": payload},
                output={
                    "feedback": full_feedback,
                    "extracted_coaching": result.generated_coaching,
                },
            ) as span:
                span.update(
                    metadata={
                        "experiment": self.experiment_name,
                        "test_set": result.test_set,
                        "test_case": result.test_case,
                        "session_id": result.session_id,
                        "accuracy": result.accuracy,
                        "confidence": result.confidence,
                    },
                    tags=[self.experiment_name, result.test_set],
                )
                trace_id = self.langfuse_client.get_current_trace_id()

            # Log scores against the trace
            self.langfuse_client.create_score(
                trace_id=trace_id,
                name="overall_similarity",
                value=result.overall_similarity,
                comment=f"Threshold: {SIMILARITY_THRESHOLD}",
            )

            for category, similarity in result.category_similarities.items():
                score_name = f"similarity_{category.lower().replace(' ', '_').replace('&', 'and')}"
                self.langfuse_client.create_score(
                    trace_id=trace_id,
                    name=score_name,
                    value=similarity,
                )

            self.langfuse_client.create_score(
                trace_id=trace_id,
                name="passed",
                value=1.0 if result.passed else 0.0,
                comment=f"Threshold: {SIMILARITY_THRESHOLD}",
            )

            logger.info(f"Logged evaluation to Langfuse, trace_id: {trace_id}")

        except Exception as e:
            logger.warning(f"Failed to log to Langfuse: {e}")

    async def evaluate_set(
        self, test_set: str, language: str = "English"
    ) -> List[EvaluationResult]:
        """
        Evaluate all test cases in a test set.

        Args:
            test_set: Name of the test set directory
            language: Language for feedback generation

        Returns:
            List of evaluation results
        """
        results = []

        # Get paths
        sets_dir = Path(config.SETS_DIR)
        set_dir = sets_dir / test_set

        if not set_dir.exists():
            logger.error(f"Test set directory not found: {set_dir}")
            return results

        # Get video files
        video_files = sorted(set_dir.glob("*.*"))

        if not video_files:
            logger.warning(f"No video files found in {set_dir}")
            return results

        # Process each video - payload is loaded per video from its filename stem
        # e.g. 1.webm -> payload_1.json
        for video_file in video_files:
            test_case = video_file.stem  # filename without extension

            # Load payload for this specific video
            payload_path = (
                Path(config.CHALLENGES_DIR) / f"payload_{test_case}.json"
            )

            if not payload_path.exists():
                logger.error(f"Payload file not found: {payload_path}")
                continue

            with open(payload_path, "r") as f:
                payload = json.load(f)

            # Load reference answer
            answer_path = (
                Path(config.ANSWERS_DIR) / test_set / f"{test_case}.json"
            )

            if not answer_path.exists():
                logger.warning(f"Reference answer not found: {answer_path}")
                continue

            with open(answer_path, "r") as f:
                reference_answer = json.load(f)

            # Evaluate test case
            try:
                result = await self.evaluate_test_case(
                    test_set=test_set,
                    test_case=test_case,
                    video_path=str(video_file),
                    payload=payload,
                    reference_answer=reference_answer,
                    language=language,
                )
                results.append(result)

                # Print result
                status = "✓ PASS" if result.passed else "✗ FAIL"
                logger.info(
                    f"{test_set}/{test_case}: {result.overall_similarity:.3f} - {status}"
                )

            except Exception as e:
                logger.error(f"Failed to evaluate {test_set}/{test_case}: {e}")
                continue

        return results

    def print_summary(self, results: List[EvaluationResult]):
        """Print evaluation summary."""
        if not results:
            logger.info("No results to summarize")
            return

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        avg_similarity = sum(r.overall_similarity for r in results) / total
        logger.info(
            f"""
                    {'=' * 80}
                    EVALUATION SUMMARY - Experiment: {self.experiment_name}
                    {'=' * 80}
                    Total test cases: {total}
                    Passed: {passed} ({passed / total * 100:.1f}%)
                    Failed: {total - passed} ({(total - passed) / total * 100:.1f}%)
                    Average similarity: {avg_similarity:.3f}
                    Threshold: {SIMILARITY_THRESHOLD}
                    {'-' * 80}
                    {'Test Case':<20} {'Similarity':<12} {'Status':<10}
                    {'-' * 80}
                    """
        )

        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            test_name = f"{result.test_set}/{result.test_case}"
            logger.info(
                f"{test_name:<20} {result.overall_similarity:<12.3f} {status:<10}"
            )

        logger.info("=" * 80 + "\n")
