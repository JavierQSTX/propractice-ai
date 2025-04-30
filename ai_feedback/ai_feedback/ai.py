from langfuse.openai import AsyncOpenAI
from loguru import logger
import base64
import json
import instructor
from ai_feedback.prompts import AUDIO_ANALYSIS_PROMPT, TEXT_ANALYSIS_PROMPT
from ai_feedback.config import settings
from ai_feedback.utils import (
    read_audio,
    generate_session_id,
    langfuse_log,
)
from ai_feedback.models import ScriptDetails, AudioAnalysis, TextAnalysis

client = AsyncOpenAI(
    api_key=settings.ai_api_key,
    base_url=settings.ai_base_url,
)
instructor_client = instructor.from_openai(client)


async def get_audio_analysis(audio: bytes, session_id: str) -> AudioAnalysis:
    encoded_string = base64.b64encode(audio).decode("utf-8")

    audio_analysis = await instructor_client.chat.completions.create(
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {"role": "developer", "content": AUDIO_ANALYSIS_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": encoded_string, "format": "wav"},
                    },
                ],
            },
        ],
        response_model=AudioAnalysis,
        session_id=session_id,
    )

    if audio_analysis is None:
        raise RuntimeError("External API call failed: received None")

    logger.info(f"AUDIO ANALYSIS: {audio_analysis}")
    return audio_analysis


async def get_text_analysis(
    transcript: str, script_details: ScriptDetails, session_id: str
) -> str:
    response = await client.chat.completions.create(
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {"role": "developer", "content": TEXT_ANALYSIS_PROMPT},
            {
                "role": "user",
                "content": f"<transcript>{transcript}</transcript>\n\n<script_details>{script_details}</script_details>",
            },
        ],
        session_id=session_id,
    )

    text_analysis = response.choices[0].message.content
    if text_analysis is None:
        raise RuntimeError("External API call failed: received None")

    logger.info(f"TEXT ANALYSIS: {text_analysis}")
    return text_analysis


async def get_feedback(audio_filename: str, script_details: ScriptDetails) -> str:
    session_id = generate_session_id()
    logger.info(f"Lesson details: {script_details}")
    audio = read_audio(audio_filename)

    audio_analysis = await get_audio_analysis(audio, session_id)
    text_analysis = await get_text_analysis(
        audio_analysis.transcript, script_details, session_id
    )

    final_feedback = f"{text_analysis}\n\n## Style Assessment Coaching Recommendations\n\n{audio_analysis.speaking_style_analysis}"
    langfuse_log(session_id, "final-feedback", final_feedback)
    return final_feedback
