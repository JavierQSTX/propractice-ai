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


class AudioAnalysis(BaseModel):
    transcript: str = Field(
        description="Complete and accurate transcript of the audio, including mispronounciations and filler words"
    )
    speaking_style_analysis: str = Field(
        description="Comprehensive analysis of the vocal style of the speaker"
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
    """

    scripts: list[ScriptWithExtractedKeywords]
