from langfuse.openai import AsyncOpenAI

import base64
from ai_feedback.prompts import AUDIO_FEEDBACK_PROMPT
from ai_feedback.config import settings
from ai_feedback.utils import extract_text_from_pdf, read_audio
from loguru import logger


client = AsyncOpenAI(
    api_key=settings.ai_api_key,
    base_url=settings.ai_base_url,
)


async def call_ai_api(prompt: str, script: str, audio: bytes) -> str:
    encoded_string = base64.b64encode(audio).decode("utf-8")

    response = await client.chat.completions.create(
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "text", "text": f"Here is the script: {script}"},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": encoded_string, "format": "wav"},
                    },
                ],
            },
        ],
    )
    feedback = response.choices[0].message.content

    if feedback is None:
        raise RuntimeError("External API call failed: received None")

    logger.info(f"Generated feedback: {feedback}")
    return feedback


async def get_feedback(audio_filename: str, pdf_filename: str) -> str:
    prompt_input = AUDIO_FEEDBACK_PROMPT
    script_text = extract_text_from_pdf(pdf_filename)
    logger.info(f"Script text: {script_text}")
    audio = read_audio(audio_filename)

    return await call_ai_api(prompt_input, script_text, audio)
