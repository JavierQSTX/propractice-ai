from pydantic import BaseModel, Field


class KeyElement(BaseModel):
    script: str
    keywords: list[str]


class ScriptDetails(BaseModel):
    question: str
    briefing: str
    keyElements: list[KeyElement]


class FeedbackInput(ScriptDetails):
    challenge: str


class FeedbackResponse(BaseModel):
    feedback: str


class AudioAnalysis(BaseModel):
    transcript: str = Field(
        description="Complete and accurate transcript of the audio, including mispronounciations and filler words"
    )
    speaking_style_analysis: str = Field(
        description="Comprehensive analysis of the vocal style of the speaker"
    )


class TextAnalysis(BaseModel):
    result: str
