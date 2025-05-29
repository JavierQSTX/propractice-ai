from pydantic import BaseModel, Field


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


class FeedbackResponse(BaseModel):
    feedback: str
    accuracy: int
    confidence: int
    session_id: str


class UserLikeRequest(BaseModel):
    session_id: str
    positive_feedback: bool


class LangfuseTracesRequest(BaseModel):
    session_id: str


class AudioAnalysis(BaseModel):
    transcript: str = Field(
        description="Complete and accurate transcript of the audio, including mispronounciations and filler words"
    )
    speaking_style_analysis: str = Field(
        description="Comprehensive analysis of the vocal style of the speaker"
    )
    confidence_score: int = Field(
        description="""Score assessing the overall quality of the speech. Can have one of 2 values:
        - 50, which means the speaker was extremely unsure of himself, he didn't really know the material
        - 100, which means the speaker was moderately confident or confident, even if he had moments of doubt, unusual pauses, filler words etc.
        """
    )


class KeywordMapping(BaseModel):
    keyword: str = Field(description="The required keyword")
    transcript_equivalent: str | None = Field(
        None,
        description="Exact match or equivalent formulation, if found in the transcript",
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
