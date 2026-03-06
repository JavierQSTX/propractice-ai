"""
Extract style coaching recommendations from AI feedback responses.
"""

from typing import Dict, Optional

STYLE_COACHING_HEADER = "## Style Coaching Recommendations"
SPEECH_ANALYSIS_SKIPPED_MARKER = "Style Assessment skipped"


def extract_style_coaching(feedback: str) -> Optional[str]:
    """
    Extract the Style Coaching Recommendations section from feedback.
    Uses simple string splitting for robustness.
    """
    # Normalize escaped newlines to real newlines
    feedback = feedback.replace("\\n", "\n")

    if STYLE_COACHING_HEADER not in feedback:
        return None

    # Split on the header and take everything after it
    after_header = feedback.split(STYLE_COACHING_HEADER, 1)[1].strip()

    # Skip if it's the "skipped" message
    if SPEECH_ANALYSIS_SKIPPED_MARKER in after_header:
        return None

    # Stop at the next ## section if any
    if "\n##" in after_header:
        after_header = after_header.split("\n##", 1)[0].strip()

    return after_header if after_header else None


def extract_style_coaching_by_category(feedback: str) -> Dict[str, str]:
    """
    Extract style coaching recommendations separated by category.
    Uses simple string splitting for robustness.
    """
    # Normalize escaped newlines
    feedback = feedback.replace("\\n", "\n")

    coaching_text = extract_style_coaching(feedback)
    if not coaching_text:
        return {}

    categories = {
        "Rhythm & Timing": "",
        "Volume & Tone": "",
        "Emotional Authenticity": "",
        "Confidence": "",
        "Visual Presence": "",
    }

    for category in categories:
        marker = f"{category}:"
        if marker not in coaching_text:
            continue

        # Take text after the category marker
        after = coaching_text.split(marker, 1)[1].strip()

        # Stop at the next category
        for other in categories:
            if other == category:
                continue
            other_marker = f"{other}:"
            if other_marker in after:
                after = after.split(other_marker, 1)[0].strip()

        # Strip leading dash/bullet if present
        after = after.lstrip("- ").strip()
        categories[category] = after

    return categories


def normalize_text(text: str) -> str:
    """Normalize text for comparison by collapsing whitespace."""
    return " ".join(text.split())
