from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class SupportedLanguage(str, Enum):
    """Supported languages for feedback generation"""
    ENGLISH = "english"
    GERMAN = "german"
    DUTCH = "dutch"
    FRENCH = "french"
    MALAY = "malay"
    SPANISH = "spanish"
    POLISH = "polish"


class KeyElement(BaseModel):
    script: str
    keywords: list[str]


class ScriptDetails(BaseModel):
    question: str
    briefing: str
    keyElements: list[KeyElement]


class FeedbackInput(ScriptDetails):
    challenge: int | str
    tags: list[str] | None = None
    user_id: str | None = None


class StyleCategory(BaseModel):
    assessment: str = Field(description="Actionable coaching feedback for this category")
    score: int = Field(description="Score from 0 to 100")


class FeedbackResponse(BaseModel):
    feedback: str
    accuracy: int
    confidence: int
    session_id: str
    rhythm_and_timing: Optional[StyleCategory] = None
    volume_and_tone: Optional[StyleCategory] = None
    emotional_authenticity: Optional[StyleCategory] = None
    confidence_detail: Optional[StyleCategory] = None


class FeedbackResponseLegacy(BaseModel):
    feedback: str
    accuracy: int
    confidence: int
    rhythm_timing_score: int
    volume_tone_score: int
    emotional_authenticity_score: int
    confidence_detail_score: int
    session_id: str


class StructuredFeedbackResponse(BaseModel):
    feedback: str
    accuracy: int
    confidence: int
    session_id: str
    rhythm_and_timing: StyleCategory
    volume_and_tone: StyleCategory
    emotional_authenticity: StyleCategory
    confidence_detail: StyleCategory


class UserLikeRequest(BaseModel):
    session_id: str
    positive_feedback: bool


class LangfuseTracesRequest(BaseModel):
    session_id: str


class AudioAnalysis(BaseModel):
    transcript: str = Field(
        description="Complete and accurate transcript of the audio, including mispronounciations and filler words"
    )
    rhythm_and_timing: StyleCategory = Field(
        description="""Analysis and score (0-100) for rhythm and timing:
        90-100: Natural and conversational flow, excellent pacing
        70-89: Good flow with minor stiffness or pacing issues
        50-69: Noticeable stiffness, some robotic delivery
        30-49: Frequently stiff or rushed, poor timing
        0-29: Very robotic, off-beat, or extremely rushed
        """
    )
    volume_and_tone: StyleCategory = Field(
        description="""Score (0-100) assessing volume and tone:
        90-100: Professional, warm, empathetic, and helpful
        70-89: Generally good tone with minor flatness
        50-69: Somewhat monotone, lacks warmth
        30-49: Flat delivery, minimal emotional texture
        0-29: Very monotone, no variation
        """
    )
    emotional_authenticity: StyleCategory = Field(
        description="""Score (0-100) assessing emotional authenticity:
        90-100: Genuinely invested, authentic connection
        70-89: Mostly authentic with occasional detachment
        50-69: Some emotional connection but inconsistent
        30-49: Limited emotional investment
        0-29: Emotionally empty, just reading words
        """
    )
    confidence: StyleCategory = Field(
        description="""Score (0-100) assessing confidence and authority:
        90-100: Assured, authoritative, bold choices
        70-89: Confident with minor hesitations
        50-69: Some confidence but noticeable uncertainty
        30-49: Frequent hesitations, "umms," unsure
        0-29: Very hesitant, lacks authority
        """
    )
    visual_presence: Optional[StyleCategory] = Field(
        default=None,
        description="Analysis and score (0-100) for visual presence (only for video)"
    )


class AudioAnalysisLegacy(BaseModel):
    transcript: str = Field(
        description="Complete and accurate transcript of the audio, including mispronounciations and filler words"
    )
    speaking_style_analysis: str = Field(
        description="Comprehensive analysis of the vocal style of the speaker"
    )
    rhythm_timing_score: int = Field(description="Score (0-100) for rhythm and timing")
    volume_tone_score: int = Field(description="Score (0-100) for volume and tone")
    emotional_authenticity_score: int = Field(description="Score (0-100) for emotional authenticity")
    confidence_score: int = Field(description="Score (0-100) for confidence and authority")


class KeywordMapping(BaseModel):
    keyword: str = Field(description="The required keyword")
    transcript_equivalent: str = Field(
        default="None",
        description="Exact match or equivalent formulation, if found in the transcript. If not found the 'None' string should be used",
    )


class ScriptWithExtractedKeywords(BaseModel):
    script: str
    keywords_with_equivalents: list[KeywordMapping]


class LessonDetailsExtractedKeywords(BaseModel):
    """
    Extract the script and keywords from the original script details
    section, along with keywords equivalents found in the transcript,
    if they exist.
    Also determine if the transcript matches the lesson or not.

    The script and keywords from the original script details should ALWAYS
    be extracted, even if the transcript doesn't match the lesson.
    """

    scripts: list[ScriptWithExtractedKeywords]
    transcript_matches_lesson: bool
