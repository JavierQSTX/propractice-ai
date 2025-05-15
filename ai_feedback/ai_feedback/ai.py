from langfuse.openai import AsyncOpenAI
from loguru import logger
import base64
import instructor
from ai_feedback.constants.prompts import (
    AUDIO_ANALYSIS_PROMPT,
    TEXT_ANALYSIS_PROMPT,
    EXTRACT_KEYWORDS_PROMPT,
)
from ai_feedback.constants.fallback_prompts import (
    FALLBACK_INCLUDE_COACHING_RECOMMENDATIONS,
    FALLBACK_MAX_WORDS_PER_SPEECH_DIMENSION,
)
from ai_feedback.constants.conditional_prompts import COACHING_RECOMMENDATIONS_PROMPTS
from ai_feedback.config import settings
from ai_feedback.utils import (
    lf,
    read_audio,
    generate_session_id,
    langfuse_log,
)
from ai_feedback.models import (
    ScriptDetails,
    AudioAnalysis,
    LessonDetailsExtractedKeywords,
)

client = AsyncOpenAI(
    api_key=settings.ai_api_key,
    base_url=settings.ai_base_url,
)
instructor_client = instructor.from_openai(client)


def compute_scores(lesson_details: LessonDetailsExtractedKeywords):
    scores = {}

    for key_element in lesson_details.scripts:
        total = len(key_element.keywords_with_equivalents)
        if total == 0:
            scores[key_element.script] = 0
            continue

        score = 0
        for mapping in key_element.keywords_with_equivalents:
            if mapping.transcript_equivalent is not None:
                score += 1

        scores[key_element.script] = int(100 * score / total)

    return scores


async def get_audio_analysis(audio: bytes, session_id: str) -> AudioAnalysis:
    encoded_string = base64.b64encode(audio).decode("utf-8")

    max_words_per_speech_dimension = lf.get_prompt(
        "max-words-per-speech-dimension",
        label="production",
        fallback=FALLBACK_MAX_WORDS_PER_SPEECH_DIMENSION,
    ).prompt

    audio_analysis = await instructor_client.chat.completions.create(
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {
                "role": "developer",
                "content": AUDIO_ANALYSIS_PROMPT.format(
                    max_words_per_speech_dimension=max_words_per_speech_dimension
                ),
            },
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

    return audio_analysis


async def get_text_analysis(
    transcript: str,
    script_details: ScriptDetails,
    key_elements_scores: dict[str, int],
    session_id: str,
) -> str:
    include_coaching_recommendations = (
        lf.get_prompt(
            "include-coaching-recommendations",
            label="production",
            fallback=FALLBACK_INCLUDE_COACHING_RECOMMENDATIONS,
        )
        .prompt.strip()
        .lower()
        == "true"
    )
    prompt_values = COACHING_RECOMMENDATIONS_PROMPTS[include_coaching_recommendations]
    logger.info(
        f"Include coaching recommendations: <{include_coaching_recommendations}>"
    )

    response = await client.chat.completions.create(
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {
                "role": "developer",
                "content": TEXT_ANALYSIS_PROMPT.format(
                    coaching_column_mention=prompt_values["coaching_column_mention"],
                    table_example=prompt_values["table_example"],
                    coaching_column_instructions=prompt_values[
                        "coaching_column_instructions"
                    ],
                ),
            },
            {
                "role": "user",
                "content": (
                    f"<transcript>{transcript}</transcript>\n\n"
                    f"<script_details>{script_details}</script_details>\n\n"
                    f"<key_elements_scores>{key_elements_scores}</key_elements_scores>\n\n"
                ),
            },
        ],
        session_id=session_id,
    )

    text_analysis = response.choices[0].message.content
    if text_analysis is None:
        raise RuntimeError("External API call failed: received None")

    return text_analysis


async def get_keyword_equivalents(
    transcript: str, script_details: ScriptDetails, session_id: str
) -> LessonDetailsExtractedKeywords:
    keyword_equivalents = await instructor_client.chat.completions.create(
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {"role": "developer", "content": EXTRACT_KEYWORDS_PROMPT},
            {
                "role": "user",
                "content": (
                    f"<transcript>{transcript}</transcript>\n\n"
                    f"<lesson_details>{script_details}</lesson_details>"
                ),
            },
        ],
        session_id=session_id,
        response_model=LessonDetailsExtractedKeywords,
    )

    if keyword_equivalents is None:
        raise RuntimeError("External API call failed: received None")

    return keyword_equivalents


async def get_feedback(
    audio_filename: str, script_details: ScriptDetails
) -> tuple[str, int, int]:
    session_id = generate_session_id()
    logger.info(f"Lesson details: {script_details}")
    audio = read_audio(audio_filename)

    audio_analysis = await get_audio_analysis(audio, session_id)
    keyword_equivalents = await get_keyword_equivalents(
        audio_analysis.transcript, script_details, session_id
    )
    key_elements_scores = compute_scores(keyword_equivalents)
    average_score = int(
        sum(key_elements_scores.values()) / len(key_elements_scores.values())
    )

    text_analysis = await get_text_analysis(
        audio_analysis.transcript, script_details, key_elements_scores, session_id
    )

    final_feedback = f"{text_analysis}\n\n## Style Assessment Coaching Recommendations\n\n{audio_analysis.speaking_style_analysis}"
    langfuse_log(session_id, "final-feedback", final_feedback)

    return final_feedback, average_score, audio_analysis.speaking_score
