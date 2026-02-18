# AI Feedback Evaluation Pipeline

A comprehensive evaluation system for assessing the quality of AI-generated feedback by comparing style coaching recommendations against reference answers using semantic similarity metrics.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Evaluations](#running-evaluations)
- [Understanding Results](#understanding-results)
- [Viewing in Langfuse](#viewing-in-langfuse)
- [Prompt Tuning Workflow](#prompt-tuning-workflow)
- [Adding Test Cases](#adding-test-cases)

## Overview

This evaluation pipeline helps you:

- **Measure feedback quality** by comparing AI-generated style coaching against expert reference answers
- **Track improvements** over time using Langfuse experiments
- **Tune prompts** systematically by comparing different prompt versions
- **Identify weaknesses** in specific coaching categories (Rhythm & Timing, Volume & Tone, etc.)

## How It Works

### Evaluation Process

1. **Load Test Case**: Reads video file, payload (challenge details), and reference answer
2. **Generate Feedback**: Calls `get_feedback_from_video()` directly (no HTTP requests)
3. **Extract Style Coaching**: Parses the "Style Coaching Recommendations" section from the response
4. **Calculate Similarity**: Uses embeddings to compute semantic similarity between generated and reference coaching
5. **Score & Track**: Assigns similarity scores and logs results to Langfuse
6. **Report**: Generates summary with pass/fail status based on similarity threshold

### Architecture

The evaluation pipeline integrates directly with the AI feedback system:

- **No HTTP overhead**: Calls AI functions directly instead of making API requests
- **Same code path**: Uses the exact same `get_feedback_from_video()` function as the production API
- **Faster execution**: No network latency or authentication overhead
- **Easier debugging**: Direct function calls make it easier to trace issues

### Similarity Scoring

The pipeline uses **semantic similarity** via embeddings rather than exact text matching:

- Generates embeddings for both generated and reference coaching using Google's `text-embedding-004` model
- Calculates cosine similarity between embedding vectors
- Scores range from 0.0 (completely different) to 1.0 (identical meaning)
- Default passing threshold: **0.75** (configurable in `evaluation/constants.py`)

This approach measures whether the AI coaching conveys the same meaning as the reference, even if worded differently.

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (for dependency management)
- Google AI API key (for embeddings)
- Langfuse account (optional, for tracking)

### Setup

1. Navigate to the ai_feedback directory:
```bash
cd /home/lorbi/Desktop/ALL-CMDG/propractice-ai/ai_feedback
```

2. Install dependencies:
```bash
poetry install
```

## Configuration

### Environment Variables

The evaluation pipeline uses the same `.env` file as the main application (`ai_feedback/.env`).

**Required variables (must be set in `ai_feedback/.env`):**

```env
# AI API key (required for embeddings and feedback generation)
AI_API_KEY=your_google_ai_api_key

# Langfuse configuration (optional, for tracking)
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

**How to get these credentials:**

- **AI_API_KEY**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
  - Sign in with your Google account
  - Click "Get API key" or "Create API key"
  - Copy the generated key

- **LANGFUSE_SECRET_KEY & LANGFUSE_PUBLIC_KEY**: Get from [Langfuse](https://cloud.langfuse.com)
  - Sign up or log in to Langfuse
  - Navigate to Settings → API Keys
  - Create a new API key pair
  - Copy both the secret and public keys

### Evaluation Constants

Evaluation-specific settings are in `evaluation/constants.py`:

```python
SIMILARITY_THRESHOLD = 0.75  # Minimum score to pass (0.0 to 1.0)
EMBEDDING_MODEL = "text-embedding-004"  # Google's embedding model
```

You can adjust `SIMILARITY_THRESHOLD` in this file to change the passing criteria.

## Running Evaluations

### Using Makefile (Recommended)

From the `ai_feedback` directory:

**Evaluate all test sets:**
```bash
make evaluate
```

**Evaluate a specific set:**
```bash
make evaluate-set SET=set_1 EXP=baseline
```

**Run with custom experiment name:**
```bash
make evaluate-experiment NAME=prompt_v2
```

### Using Python Directly

From the `ai_feedback/evaluation` directory:

**Evaluate all test sets:**
```bash
poetry run python run_evaluation.py --all --experiment baseline
```

**Evaluate specific set:**
```bash
poetry run python run_evaluation.py --set set_1 --experiment baseline
```

**Disable Langfuse tracking:**
```bash
poetry run python run_evaluation.py --all --no-langfuse
```

**Verbose logging:**
```bash
poetry run python run_evaluation.py --all --verbose
```

### Command-Line Options

- `--set SET_NAME`: Evaluate specific test set (e.g., `set_1`)
- `--all`: Evaluate all available test sets
- `--experiment NAME`: Experiment name for Langfuse tracking (default: "baseline")
- `--language LANG`: Language for feedback generation (default: "English")
- `--verbose`: Enable debug logging
- `--no-langfuse`: Disable Langfuse tracking

**Examples:**

```bash
# Evaluate all sets with verbose logging
poetry run python run_evaluation.py --all --verbose

# Evaluate specific set with custom experiment name
poetry run python run_evaluation.py --set set_1 --experiment prompt_v2

# Evaluate in Spanish without Langfuse
poetry run python run_evaluation.py --all --language Spanish --no-langfuse
```

## Understanding Results

### Console Output

The evaluation prints a summary table:

```
================================================================================
EVALUATION SUMMARY - Experiment: baseline
================================================================================
Total test cases: 3
Passed: 2 (66.7%)
Failed: 1 (33.3%)
Average similarity: 0.782
Threshold: 0.750

--------------------------------------------------------------------------------
Test Case            Similarity   Status    
--------------------------------------------------------------------------------
set_1/1              0.823        ✓ PASS    
set_1/2              0.756        ✓ PASS    
set_1/3              0.698        ✗ FAIL    
================================================================================
```

### Similarity Scores

- **Overall Similarity**: Semantic similarity between entire generated and reference coaching text
- **Category Similarities**: Per-category scores (Rhythm & Timing, Volume & Tone, etc.)
- **Pass/Fail**: Based on whether overall similarity exceeds threshold

### What the Scores Mean

- **0.90 - 1.00**: Excellent - Nearly identical meaning
- **0.75 - 0.89**: Good - Similar meaning with minor variations
- **0.60 - 0.74**: Fair - Related but noticeable differences
- **0.00 - 0.59**: Poor - Significantly different meaning

## Viewing in Langfuse

See [LANGFUSE_GUIDE.md](LANGFUSE_GUIDE.md) for detailed instructions on viewing and comparing evaluation results in Langfuse.

## Prompt Tuning Workflow

### Step 1: Establish Baseline

Run evaluation with current prompts:
```bash
make evaluate-experiment NAME=baseline
```

Note the average similarity score and pass rate.

### Step 2: Modify Prompts

Edit prompts in `ai_feedback/constants/prompts.py` to address identified weaknesses.

### Step 3: Run New Evaluation

Evaluate with a new experiment name:
```bash
make evaluate-experiment NAME=prompt_v2
```

### Step 4: Compare in Langfuse

Review similarity scores and improvements in Langfuse dashboard.

### Step 5: Iterate

Continue refining until reaching target quality.

## Adding Test Cases

See the main README for details on adding new test cases and test sets.

## Troubleshooting

### Common Issues

**"AI_API_KEY must be set"**
- Set `AI_API_KEY` in `ai_feedback/.env`
- Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)

**"No test sets found"**
- Ensure test set directories exist under `ai_feedback/data/sets/`

**"Failed to initialize Langfuse"**
- Check Langfuse credentials in `ai_feedback/.env`
- Set `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY`
- Get credentials from [Langfuse Settings](https://cloud.langfuse.com)
- Use `--no-langfuse` flag to run without tracking

**Low similarity scores**
- Review generated vs reference coaching manually
- Adjust `SIMILARITY_THRESHOLD` in `evaluation/constants.py` if needed
- Improve prompts to better match reference style

**API authentication errors**
- Verify API is running at configured URL
- Check `LOGIN_USERNAME` and `LOGIN_PASSWORD` in `ai_feedback/.env`

## Best Practices

1. **Establish baseline first**: Always run baseline evaluation before making changes
2. **Use descriptive experiment names**: e.g., "prompt_v2_more_specific" instead of "test1"
3. **Track changes**: Document what changed between experiments
4. **Review failures**: Manually review failed cases to understand why
5. **Iterate incrementally**: Make one change at a time for clear attribution
6. **Maintain reference quality**: Ensure reference answers represent ideal coaching
7. **Regular evaluation**: Run evaluations after any prompt changes
