from openai import OpenAI
import base64
from ai_feedback.prompts import AUDIO_FEEDBACK_PROMPT
from ai_feedback.config import settings
from ai_feedback.utils import extract_text_from_pdf, read_audio


client = OpenAI(
    api_key=settings.ai_api_key,
    base_url=settings.ai_base_url,
)


def call_ai_api(prompt: str, script: str, audio: bytes) -> str:
    encoded_string = base64.b64encode(audio).decode("utf-8")

    feedback = (
        client.chat.completions.create(
            model=settings.ai_model_name,
            modalities=["text"],
            temperature=1e-7,
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
        .choices[0]
        .message.content
    )

    if feedback is None:
        raise RuntimeError("External API call failed: received None")
    return feedback


def get_feedback(audio_filename: str, pdf_filename: str) -> str:
    prompt_input = AUDIO_FEEDBACK_PROMPT
    script_text = extract_text_from_pdf(pdf_filename)
    audio = read_audio(audio_filename)

    return call_ai_api(prompt_input, script_text, audio)
