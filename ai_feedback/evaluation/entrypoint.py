#!/usr/bin/env python3
"""
CLI for running AI feedback evaluations.
"""

import asyncio
import sys
from pathlib import Path
import click
from loguru import logger
from langfuse import Langfuse

from evaluation.utils import setup_logging, get_available_sets, run_evaluations

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation import config
from evaluation.similarity import SimilarityCalculator
from evaluation.evaluator import FeedbackEvaluator


@click.command()
@click.option(
    "--set",
    "test_set",
    type=str,
    default="set_1",
    show_default=True,
    help="Test set to evaluate (e.g., set_1)",
)
@click.option("--all", "evaluate_all", is_flag=True, help="Evaluate all test sets")
@click.option(
    "--experiment",
    type=str,
    default="baseline",
    show_default=True,
    help="Experiment name for tracking in Langfuse",
)
@click.option(
    "--language",
    type=str,
    default="English",
    help="Language for feedback generation (default: English)",
)
@click.option(
    "--api-url",
    type=str,
    default="http://localhost:8080",
    help="API base URL (default: from config)",
)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--no-langfuse", is_flag=True, help="Disable Langfuse tracking")
def main(test_set, evaluate_all, experiment, language, api_url, verbose, no_langfuse):
    """Run evaluation on AI feedback quality."""

    # Setup logging
    setup_logging(verbose)

    # Get test sets to evaluate
    if evaluate_all:
        test_sets = get_available_sets()
        if not test_sets:
            logger.error(f"No test sets found in {config.SETS_DIR}")
            sys.exit(1)
        logger.info(f"Found {len(test_sets)} test sets: {', '.join(test_sets)}")
    else:
        test_sets = [test_set]

    # Check if AI API key is set
    if not config.AI_API_KEY:
        logger.error("AI_API_KEY environment variable must be set")
        sys.exit(1)

    # Initialize similarity calculator
    logger.info("Initializing similarity calculator...")
    similarity_calculator = SimilarityCalculator(api_key=config.AI_API_KEY)

    # Initialize Langfuse if enabled
    langfuse_client = None
    if not no_langfuse:
        try:
            logger.info("Initializing Langfuse client...")
            langfuse_client = Langfuse()
            logger.info("Langfuse client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            logger.warning("Continuing without Langfuse tracking")

    # Initialize evaluator
    evaluator = FeedbackEvaluator(
        similarity_calculator=similarity_calculator,
        langfuse_client=langfuse_client,
        experiment_name=experiment,
    )

    # Run async evaluations
    all_results = asyncio.run(run_evaluations(evaluator, test_sets, language))

    # Print summary
    if all_results:
        evaluator.print_summary(all_results)

        # Flush Langfuse
        if langfuse_client:
            logger.info("Flushing Langfuse data...")
            langfuse_client.flush()
            logger.info("Langfuse data flushed successfully")

        logger.info(f"\n✓ Evaluation complete! Experiment: {experiment}")
        if langfuse_client:
            logger.info(f"View results in Langfuse dashboard")

        sys.exit(0)
    else:
        logger.error("No evaluations were completed")
        sys.exit(1)


if __name__ == "__main__":
    main()
