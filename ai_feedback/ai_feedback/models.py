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


class FeedbackResponse(BaseModel):
    feedback: str
    accuracy: int
    confidence: int


class AudioAnalysis(BaseModel):
    transcript: str = Field(
        description="Complete and accurate transcript of the audio, including mispronounciations and filler words"
    )
    speaking_style_analysis: str = Field(
        description="Comprehensive analysis of the vocal style of the speaker"
    )
    confidence_score: int = Field(
        description="""Score assessing the overall quality of the speech. Can have one of 3 values:
        - 0, which means the speaker didn't even talk or was extremely unsure of himself
        - 50, which means the speaker was moderately confident, had moments of doubt, unusual pauses, filler words etc.
        - 100, which means the speaker proved his knowledge of the material, was eloquent and easy to trust
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
