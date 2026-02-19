import sys
from pathlib import Path

from loguru import logger

from evaluation import config
from evaluation.evaluator import FeedbackEvaluator, EvaluationResult


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def get_available_sets() -> list:
    """Get list of available test sets."""
    sets_dir = Path(config.SETS_DIR)
    if not sets_dir.exists():
        return []
    return sorted([d.name for d in sets_dir.iterdir() if d.is_dir()])


async def run_evaluations(
    evaluator: FeedbackEvaluator, test_sets: list, language: str
) -> list[EvaluationResult]:
    all_results = []

    for ts in test_sets:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Evaluating test set: {ts}")
        logger.info(f"{'=' * 80}\n")

        results = await evaluator.evaluate_set(ts, language=language)
        all_results.extend(results)

        if results:
            logger.info(f"Completed {len(results)} evaluations for {ts}")

    return all_results
