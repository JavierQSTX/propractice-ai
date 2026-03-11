import asyncio
import base64
import time
import io
from typing import Any

from faster_whisper import WhisperModel
import instructor
from google import genai
from langfuse import get_client
from langfuse.openai import AsyncOpenAI
from loguru import logger
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

from ai_feedback.config import settings
from ai_feedback.constants.conditional_prompts import COACHING_RECOMMENDATIONS_PROMPTS
from ai_feedback.constants.fallback_prompts import (
    FALLBACK_INCLUDE_COACHING_RECOMMENDATIONS,
    FALLBACK_MAX_WORDS_PER_SPEECH_DIMENSION,
)
from ai_feedback.constants.prompts import (
    AUDIO_ANALYSIS_PROMPT,
    AUDIO_ANALYSIS_PROMPT_LEGACY,
    TEXT_ANALYSIS_PROMPT,
    EXTRACT_KEYWORDS_PROMPT,
    JUDGE_FEEDBACK_PROMPT,
    SPEECH_ANALYSIS_SKIPPED,
    VIDEO_ANALYSIS_PROMPT
)
from ai_feedback.constants.translations import STYLE_CATEGORY_TITLES
from ai_feedback.models import (
    ScriptDetails,
    AudioAnalysis,
    AudioAnalysisLegacy,
    LessonDetailsExtractedKeywords, SupportedLanguage, StyleCategory,
)
from ai_feedback.utils import (
    lf,
    read_audio,
    generate_session_id,
)

MAX_ITERATIONS = 30        # e.g. ~60 seconds total
SLEEP_SECONDS = 2

LANGUAGE_TO_WHISPER_CODE = {
    "english": "en",
    "german": "de",
    "dutch": "nl",
    "french": "fr",
    "malay": "ms",
    "spanish": "es",
    "polish": "pl",
}

# Initialize Whisper model globally
logger.info("Initializing Faster Whisper model...")
try:
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("Faster Whisper model loaded successfully.")
except Exception as e:
    logger.warning(f"Failed to load Whisper model: {e}")
    whisper_model = None

langfuse = get_client()
GoogleGenAIInstrumentor().instrument()

client = AsyncOpenAI(
    api_key=settings.ai_api_key,
    base_url=settings.ai_base_url,
)
instructor_client = instructor.from_openai(client)

genai_client = genai.Client(api_key=settings.ai_api_key)

def get_scores_and_matching_keywords(
    keyword_equivalents: LessonDetailsExtractedKeywords,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    if not keyword_equivalents.transcript_matches_lesson:
        return (
            {key_element.script: 0 for key_element in keyword_equivalents.scripts},
            {
                key_element.script: [
                    kw.keyword for kw in key_element.keywords_with_equivalents
                ]
                for key_element in keyword_equivalents.scripts
            },
        )

    scores = {}
    matching_keywords = {}
    for key_element in keyword_equivalents.scripts:
        total = len(key_element.keywords_with_equivalents)
        if total == 0:
            scores[key_element.script] = 0
            matching_keywords[key_element.script] = []
            continue

        score = 0
        key_words = []
        for mapping in key_element.keywords_with_equivalents:
            if mapping.transcript_equivalent == "None":
                key_words.append(mapping.keyword)
            else:
                score += 1
                key_words.append(f"**{mapping.keyword}**")

        try:
            scores[key_element.script] = int(100 * score / total)
        except ZeroDivisionError:
            scores[key_element.script] = 0

        matching_keywords[key_element.script] = key_words

    return scores, matching_keywords


async def get_audio_analysis(audio: bytes, session_id: str, language: str = SupportedLanguage.ENGLISH.value) -> AudioAnalysis:
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
                    max_words_per_speech_dimension=max_words_per_speech_dimension,
                    language=language
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
    )

    if audio_analysis is None:
        raise RuntimeError("External API call failed: received None")

    return audio_analysis


async def get_audio_analysis_legacy(
    audio: bytes,
    session_id: str,
    language: str = SupportedLanguage.ENGLISH.value,
) -> AudioAnalysisLegacy:
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
                "content": AUDIO_ANALYSIS_PROMPT_LEGACY.format(
                    max_words_per_speech_dimension=max_words_per_speech_dimension,
                    language=language
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
        response_model=AudioAnalysisLegacy,
    )

    if audio_analysis is None:
        raise RuntimeError("External API call failed: received None")

    return audio_analysis

def _transcribe_audio_sync(audio_source: bytes | str, language: str) -> str:
    if whisper_model is None:
        raise RuntimeError("Whisper model not initialized")
    
    # audio_source could be `bytes` (from get_feedback/legacy) or `str` (from get_feedback_from_video file path)
    if isinstance(audio_source, bytes):
        audio_input = io.BytesIO(audio_source)
    else:
        audio_input = audio_source
        
    whisper_lang = LANGUAGE_TO_WHISPER_CODE.get(language.lower(), "en")
    segments, _ = whisper_model.transcribe(audio_input, language=whisper_lang)
    return " ".join([segment.text for segment in segments])

async def get_fast_transcription(audio_source: bytes | str, language: str = SupportedLanguage.ENGLISH.value) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _transcribe_audio_sync, audio_source, language)

async def upload_and_wait_for_file(video_filename: str) -> Any:
    logger.info(f"Uploading video file: {video_filename}")
    
    myfile = await genai_client.aio.files.upload(file=video_filename)
    logger.info(f"Video uploaded with URI: {myfile.uri}")

    for i in range(MAX_ITERATIONS):
        if myfile.state.name != "PROCESSING":
            break

        logger.info(f"Waiting for video processing... ({i + 1}/{MAX_ITERATIONS})")
        await asyncio.sleep(SLEEP_SECONDS)
        myfile = await genai_client.aio.files.get(name=myfile.name)
    else:
        raise TimeoutError("File processing timed out")
    
    if myfile.state.name == "FAILED":
        raise RuntimeError(f"Video processing failed: {myfile.state}")
        
    logger.info("Video processing complete.")
    return myfile

async def get_video_analysis(myfile: Any, session_id: str, language: str = SupportedLanguage.ENGLISH.value) -> AudioAnalysis:
    """
    Analyze video using Gemini 3.0's multimodal capabilities.
    Processes both audio and visual streams from an already uploaded file.
    Returns AudioAnalysis structure for compatibility with existing pipeline.
    """
    logger.info("Generating video analysis...")
    
    max_words_per_speech_dimension = lf.get_prompt(
        "max-words-per-speech-dimension",
        label="production",
        fallback=FALLBACK_MAX_WORDS_PER_SPEECH_DIMENSION,
    ).prompt
    
    response = await genai_client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            VIDEO_ANALYSIS_PROMPT.format(
                max_words_per_speech_dimension=max_words_per_speech_dimension,
                language=language
            ),
            myfile,
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": AudioAnalysis,
        }
    )
    
    logger.info(f"Video analysis response: {response}")
    
    if response.parsed is None:
        raise RuntimeError("External API call failed: received None")
    
    return response.parsed



async def get_text_analysis(
    *,
    transcript: str,
    script_details: ScriptDetails,
    scores: dict[str, int],
    matching_keywords: dict[str, list[str]],
    session_id: str,
    language: str = SupportedLanguage.ENGLISH.value,
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

    titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
    response = await client.chat.completions.create(  # pyright: ignore
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
                    language=language,
                    assessment_heading=titles["assessment_heading"],
                ),
            },
            {
                "role": "user",
                "content": (
                    f"<transcript>{transcript}</transcript>\n\n"
                    f"<script_details>{script_details}</script_details>\n\n"
                    f"<key_elements_scores>{scores}</key_elements_scores>\n\n"
                ),
            },
        ],
    )

    text_analysis = response.choices[0].message.content
    if text_analysis is None:
        raise RuntimeError("External API call failed: received None")

    for script, keywords in matching_keywords.items():
        # replacing script with list of bold-formatted keywords
        # text_analysis = text_analysis.replace(script, f"- {', '.join(keywords)}")
        text_analysis = text_analysis.replace(script, "- " + " \| ".join(keywords))

    return text_analysis


async def get_keyword_equivalents(
    *, transcript: str, script_details: ScriptDetails, session_id: str, language: str = SupportedLanguage.ENGLISH.value
) -> LessonDetailsExtractedKeywords:

    logger.info(f"Before calling instructor_client")
    keyword_equivalents = await genai_client.aio.models.generate_content(
        model=settings.ai_model_name,
        contents=[
            EXTRACT_KEYWORDS_PROMPT.format(language=language),
            f"<transcript>{transcript}</transcript>\n\n <lesson_details>{script_details}</lesson_details>"
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": LessonDetailsExtractedKeywords,
        }
    )
    # log keyword_equivalents
    logger.info(f"Keyword equivalents: {keyword_equivalents}")

    if keyword_equivalents is None:
        raise RuntimeError("External API call failed: received None")

    return keyword_equivalents.parsed


async def judge_feedback(
    *, ai_input: str, ai_feedback: str, session_id: str
) -> LessonDetailsExtractedKeywords:
    response = await client.chat.completions.create(  # pyright: ignore
        model=settings.ai_model_name,
        modalities=["text"],
        messages=[
            {"role": "developer", "content": JUDGE_FEEDBACK_PROMPT},
            {
                "role": "user",
                "content": (
                    f"<ai_input>{ai_input}</ai_input>\n\n<ai_feedback>{ai_feedback}</ai_feedback>"
                ),
            },
        ],
    )

    judged_feedback = response.choices[0].message.content
    if judged_feedback is None:
        raise RuntimeError("External API call failed: received None")

    return judged_feedback


async def get_feedback(
    *,
    audio_filename: str,
    script_details: ScriptDetails,
    user_id: str | None,
    tags: list[str] | None,
    language: str = SupportedLanguage.ENGLISH.value,
) -> dict[str, Any]:
    start_time = time.time()
    timing_logs = []
    session_id = generate_session_id()
    logger.info(f"Lesson details: {script_details}")

    audio = read_audio(audio_filename)

    t0 = time.time()
    transcript = await get_fast_transcription(audio, language)
    timing_logs.append(f"get_fast_transcription: {time.time() - t0:.2f}s")
    
    async def process_text_feedback():
        t0_kw = time.time()
        kw_eq = await get_keyword_equivalents(
            transcript=transcript,
            script_details=script_details,
            session_id=session_id,
            language=language,
        )
        timing_logs.append(f"get_keyword_equivalents: {time.time() - t0_kw:.2f}s")
        
        logger.info(f"Keyword equivalents: {kw_eq}")
        scores, matching_keywords = get_scores_and_matching_keywords(kw_eq)
        logger.info(f"Scores: {scores}")
        logger.info(f"Matched keywords: {matching_keywords}")

        try:
            average_score = int(sum(scores.values()) / len(scores))
        except ZeroDivisionError:
            average_score = 0

        t0_text = time.time()
        txt_analysis = await get_text_analysis(
            transcript=transcript,
            script_details=script_details,
            scores=scores,
            matching_keywords=matching_keywords,
            session_id=session_id,
            language=language,
        )
        timing_logs.append(f"get_text_analysis: {time.time() - t0_text:.2f}s")
        return kw_eq, txt_analysis, average_score

    audio_analysis_coro = get_audio_analysis(audio, session_id, language)
    text_feedback_coro = process_text_feedback()

    t0_gather = time.time()
    audio_analysis, (keyword_equivalents, text_analysis, average_score) = await asyncio.gather(
        audio_analysis_coro,
        text_feedback_coro
    )
    timing_logs.append(f"audio_analysis_and_text_chain_gather: {time.time() - t0_gather:.2f}s")
    
    titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
    final_feedback = f"{text_analysis}{titles['bolded_keywords']}\n\n"

    # Concatenate style assessments into final_feedback
    if not keyword_equivalents.transcript_matches_lesson:
        titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
        final_feedback += f"## {titles['heading']}\n\n{SPEECH_ANALYSIS_SKIPPED}"
        skipped_category = StyleCategory(assessment=SPEECH_ANALYSIS_SKIPPED, score=0)
        
        timing_logs.append(f"Total time: {time.time() - start_time:.2f}s")
        logger.info(f"Performance [get_feedback]: {' | '.join(timing_logs)}")
        
        return {
            "feedback": final_feedback,
            "accuracy": average_score,
            "confidence": 0,
            "session_id": session_id,
            "rhythm_and_timing": skipped_category,
            "volume_and_tone": skipped_category,
            "emotional_authenticity": skipped_category,
            "confidence_detail": skipped_category,
        }

    titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
    final_feedback += (
        f"## {titles['heading']}\n\n"
        f"* {titles['rhythm_and_timing']}: {audio_analysis.rhythm_and_timing.assessment}\n"
        f"* {titles['volume_and_tone']}: {audio_analysis.volume_and_tone.assessment}\n"
        f"* {titles['emotional_authenticity']}: {audio_analysis.emotional_authenticity.assessment}\n"
        f"* {titles['confidence']}: {audio_analysis.confidence.assessment}"
    )

    # Normal case: return full structured data
    confidence_score = int(
        (
            audio_analysis.rhythm_and_timing.score
            + audio_analysis.volume_and_tone.score
            + audio_analysis.emotional_authenticity.score
            + audio_analysis.confidence.score
        )
        / 4
    )

    timing_logs.append(f"Total time: {time.time() - start_time:.2f}s")
    logger.info(f"Performance [get_feedback]: {' | '.join(timing_logs)}")

    return {
        "feedback": final_feedback,
        "accuracy": average_score,
        "confidence": confidence_score,
        "session_id": session_id,
        "rhythm_and_timing": audio_analysis.rhythm_and_timing,
        "volume_and_tone": audio_analysis.volume_and_tone,
        "emotional_authenticity": audio_analysis.emotional_authenticity,
        "confidence_detail": audio_analysis.confidence,
    }

async def get_feedback_legacy(
    *,
    audio_filename: str,
    script_details: ScriptDetails,
    user_id: str | None,
    tags: list[str] | None,
    language: str = SupportedLanguage.ENGLISH.value,
) -> dict[str, Any]:
    start_time = time.time()
    timing_logs = []
    session_id = generate_session_id()
    logger.info(f"Lesson details: {script_details}")

    audio = read_audio(audio_filename)
    
    t0 = time.time()
    transcript = await get_fast_transcription(audio, language)
    timing_logs.append(f"get_fast_transcription: {time.time() - t0:.2f}s")

    async def process_text_feedback():
        t0_kw = time.time()
        kw_eq = await get_keyword_equivalents(
            transcript=transcript,
            script_details=script_details,
            session_id=session_id,
            language=language,
        )
        timing_logs.append(f"get_keyword_equivalents: {time.time() - t0_kw:.2f}s")
        
        logger.info(f"Keyword equivalents: {kw_eq}")
        scores, matching_keywords = get_scores_and_matching_keywords(kw_eq)
        logger.info(f"Scores: {scores}")
        logger.info(f"Matched keywords: {matching_keywords}")

        try:
            average_score = int(sum(scores.values()) / len(scores))
        except ZeroDivisionError:
            average_score = 0

        t0_text = time.time()
        txt_analysis = await get_text_analysis(
            transcript=transcript,
            script_details=script_details,
            scores=scores,
            matching_keywords=matching_keywords,
            session_id=session_id,
            language=language,
        )
        timing_logs.append(f"get_text_analysis: {time.time() - t0_text:.2f}s")
        return kw_eq, txt_analysis, average_score

    audio_analysis_legacy_coro = get_audio_analysis_legacy(audio, session_id, language)
    text_feedback_coro = process_text_feedback()

    t0_gather = time.time()
    audio_analysis, (keyword_equivalents, text_analysis, average_score) = await asyncio.gather(
        audio_analysis_legacy_coro,
        text_feedback_coro
    )
    timing_logs.append(f"audio_analysis_legacy_and_text_chain_gather: {time.time() - t0_gather:.2f}s")
    
    speech_analysis = (
        SPEECH_ANALYSIS_SKIPPED
        if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.speaking_style_analysis
    )

    titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
    final_feedback = (
        f"{text_analysis}{titles['bolded_keywords']}\n\n"
        f"## {titles['heading']}\n\n{speech_analysis}"
    )

    confidence_score = (
        0
        if not keyword_equivalents.transcript_matches_lesson
        else int(
            (
                audio_analysis.rhythm_timing_score
                + audio_analysis.volume_tone_score
                + audio_analysis.emotional_authenticity_score
                + audio_analysis.confidence_score
            )
            / 4
        )
    )

    # Individual dimension scores (0 if transcript doesn't match lesson)
    rhythm_timing = (
        0 if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.rhythm_timing_score
    )
    volume_tone = (
        0 if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.volume_tone_score
    )
    emotional_authenticity = (
        0 if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.emotional_authenticity_score
    )
    confidence_detail = (
        0 if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.confidence_score
    )

    timing_logs.append(f"Total time: {time.time() - start_time:.2f}s")
    logger.info(f"Performance [get_feedback_legacy]: {' | '.join(timing_logs)}")

    return {
        "feedback": final_feedback,
        "accuracy": average_score,
        "confidence": confidence_score,
        "session_id": session_id,
        "rhythm_timing_score": rhythm_timing,
        "volume_tone_score": volume_tone,
        "emotional_authenticity_score": emotional_authenticity,
        "confidence_detail_score": confidence_detail,
    }


async def get_feedback_from_video(
    *,
    video_filename: str,
    script_details: ScriptDetails,
    user_id: str | None,
    tags: list[str] | None,
    language: str = SupportedLanguage.ENGLISH.value,
) -> dict[str, Any]:
    """
    Generate feedback from video using Gemini's multimodal capabilities.
    This function processes video directly without converting to audio first.
    """
    start_time = time.time()
    timing_logs = []
    session_id = generate_session_id()
    logger.info(f"Lesson details: {script_details}")
    logger.info(f"Processing video file: {video_filename}")

    t0_upload_transcribe = time.time()
    upload_task = asyncio.create_task(upload_and_wait_for_file(video_filename))
    transcription_task = asyncio.create_task(get_fast_transcription(video_filename, language))

    myfile, transcript = await asyncio.gather(upload_task, transcription_task)
    timing_logs.append(f"video_upload_and_transcription: {time.time() - t0_upload_transcribe:.2f}s")

    # Run analysis and keyword extraction concurrently using gather
    async def process_text_feedback():
        t0_kw = time.time()
        kw_eq = await get_keyword_equivalents(
            transcript=transcript,
            script_details=script_details,
            session_id=session_id,
            language=language,
        )
        timing_logs.append(f"get_keyword_equivalents: {time.time() - t0_kw:.2f}s")
        
        logger.info(f"Keyword equivalents: {kw_eq}")
        scores, matching_keywords = get_scores_and_matching_keywords(kw_eq)
        logger.info(f"Scores: {scores}")
        logger.info(f"Matched keywords: {matching_keywords}")

        try:
            average_score = int(sum(scores.values()) / len(scores))
        except ZeroDivisionError:
            average_score = 0

        # Text analysis can now run since scores are computed
        t0_text = time.time()
        txt_analysis = await get_text_analysis(
            transcript=transcript,
            script_details=script_details,
            scores=scores,
            matching_keywords=matching_keywords,
            session_id=session_id,
            language=language,
        )
        timing_logs.append(f"get_text_analysis: {time.time() - t0_text:.2f}s")
        return kw_eq, txt_analysis, average_score

    video_analysis_coro = get_video_analysis(myfile, session_id, language)
    text_feedback_coro = process_text_feedback()

    t0_gather = time.time()
    video_analysis, (keyword_equivalents, text_analysis, average_score) = await asyncio.gather(
        video_analysis_coro,
        text_feedback_coro
    )
    timing_logs.append(f"video_analysis_and_text_chain_gather: {time.time() - t0_gather:.2f}s")
    
    try:
        await genai_client.aio.files.delete(name=myfile.name)
        logger.info(f"Deleted uploaded file: {myfile.name}")
    except Exception as e:
        logger.warning(f"Failed to delete uploaded file: {e}")

    titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
    final_feedback = f"{text_analysis}{titles['bolded_keywords']}\n\n"

    # Concatenate style assessments into final_feedback
    if not keyword_equivalents.transcript_matches_lesson:
        titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
        final_feedback += f"## {titles['heading']}\n\n{SPEECH_ANALYSIS_SKIPPED}"
        skipped_category = StyleCategory(assessment=SPEECH_ANALYSIS_SKIPPED, score=0)
        
        timing_logs.append(f"Total time: {time.time() - start_time:.2f}s")
        logger.info(f"Performance [get_feedback_from_video]: {' | '.join(timing_logs)}")
        
        return {
            "feedback": final_feedback,
            "accuracy": average_score,
            "confidence": 0,
            "session_id": session_id,
            "rhythm_and_timing": skipped_category,
            "volume_and_tone": skipped_category,
            "emotional_authenticity": skipped_category,
            "confidence_detail": skipped_category,
            "visual_presence": skipped_category,
        }

    titles = STYLE_CATEGORY_TITLES.get(language, STYLE_CATEGORY_TITLES[SupportedLanguage.ENGLISH.value])
    final_feedback += (
        f"## {titles['heading']}\n\n"
        f"* {titles['rhythm_and_timing']}: {video_analysis.rhythm_and_timing.assessment}\n"
        f"* {titles['volume_and_tone']}: {video_analysis.volume_and_tone.assessment}\n"
        f"* {titles['emotional_authenticity']}: {video_analysis.emotional_authenticity.assessment}\n"
        f"* {titles['confidence']}: {video_analysis.confidence.assessment}"
    )

    # Normal case: return full structured data
    confidence_score = int(
        (
            video_analysis.rhythm_and_timing.score
            + video_analysis.volume_and_tone.score
            + video_analysis.emotional_authenticity.score
            + video_analysis.confidence.score
        )
        / 4
    )

    timing_logs.append(f"Total time: {time.time() - start_time:.2f}s")
    logger.info(f"Performance [get_feedback_from_video]: {' | '.join(timing_logs)}")

    return {
        "feedback": final_feedback,
        "accuracy": average_score,
        "confidence": confidence_score,
        "session_id": session_id,
        "rhythm_and_timing": video_analysis.rhythm_and_timing,
        "volume_and_tone": video_analysis.volume_and_tone,
        "emotional_authenticity": video_analysis.emotional_authenticity,
        "confidence_detail": video_analysis.confidence,
    }
