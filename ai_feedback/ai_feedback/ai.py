from langfuse.openai import AsyncOpenAI
from loguru import logger
import base64
import instructor
from typing import List
from ai_feedback.constants.prompts import (
    AUDIO_ANALYSIS_PROMPT,
    TEXT_ANALYSIS_PROMPT,
    EXTRACT_KEYWORDS_PROMPT,
    JUDGE_FEEDBACK_PROMPT,
    SPEECH_ANALYSIS_SKIPPED,
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


def get_scores_and_matching_keywords(
    keyword_equivalents: LessonDetailsExtractedKeywords,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    logger.info(f"transcript_matches_lesson: {keyword_equivalents.transcript_matches_lesson}")
    logger.info(f"Number of scripts: {len(keyword_equivalents.scripts)}")
    
    # Log details about each script and its keywords
    for i, script_element in enumerate(keyword_equivalents.scripts):
        logger.info(f"Script {i}: '{script_element.script[:50]}...'")
        logger.info(f"  Keywords count: {len(script_element.keywords_with_equivalents)}")
        for j, mapping in enumerate(script_element.keywords_with_equivalents):
            logger.info(f"    {j}: '{mapping.keyword}' -> '{mapping.transcript_equivalent}'")
    
    # Calculate scores regardless of transcript_matches_lesson
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
            if mapping.transcript_equivalent == "None" or mapping.transcript_equivalent is None:
                key_words.append(mapping.keyword)
            else:
                score += 1
                key_words.append(f"**{mapping.keyword}**")

        try:
            scores[key_element.script] = int(100 * score / total)
        except ZeroDivisionError:
            scores[key_element.script] = 0

        matching_keywords[key_element.script] = key_words
        
        logger.info(f"Script '{key_element.script[:30]}...': {score}/{total} matches = {scores[key_element.script]}%")

    # If transcript doesn't match lesson, override scores to 0 but keep the matching keywords for display
    if not keyword_equivalents.transcript_matches_lesson:
        logger.info("Transcript doesn't match lesson - setting all scores to 0")
        scores = {script: 0 for script in scores.keys()}

    return scores, matching_keywords


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
    *,
    transcript: str,
    script_details: ScriptDetails,
    scores: dict[str, int],
    matching_keywords: dict[str, list[str]],
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
        session_id=session_id,
    )

    text_analysis = response.choices[0].message.content
    if text_analysis is None:
        raise RuntimeError("External API call failed: received None")

    # Clean up markdown code blocks if the AI wrapped the response in them
    text_analysis = text_analysis.strip()
    if text_analysis.startswith("```markdown"):
        text_analysis = text_analysis[11:]  # Remove ```markdown
    elif text_analysis.startswith("```"):
        text_analysis = text_analysis[3:]   # Remove ```
    
    if text_analysis.endswith("```"):
        text_analysis = text_analysis[:-3]  # Remove trailing ```
    
    text_analysis = text_analysis.strip()

    for script, keywords in matching_keywords.items():
        # replacing script with list of bold-formatted keywords
        # text_analysis = text_analysis.replace(script, f"- {', '.join(keywords)}")
        text_analysis = text_analysis.replace(script, "- " + " \| ".join(keywords))

    return text_analysis


async def get_keyword_equivalents(
    *, transcript: str, script_details: ScriptDetails, session_id: str
) -> LessonDetailsExtractedKeywords:
    try:
        # Try with the single model first (revert from List approach)
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
            max_retries=1,
        )

        if keyword_equivalents is None:
            raise RuntimeError("Instructor client returned None")

        return keyword_equivalents

    except Exception as instructor_error:
        logger.warning(f"Instructor client failed: {instructor_error}")
        logger.info("Falling back to regular OpenAI client with JSON parsing")
        
        # Fallback to regular OpenAI client with JSON response
        response = await client.chat.completions.create(
            model=settings.ai_model_name,
            modalities=["text"],
            messages=[
                {
                    "role": "developer", 
                    "content": EXTRACT_KEYWORDS_PROMPT + "\n\nIMPORTANT: Return your response as valid JSON that matches this exact structure: {\"scripts\": [{\"script\": \"string\", \"keywords_with_equivalents\": [{\"keyword\": \"string\", \"transcript_equivalent\": \"string or None\"}]}], \"transcript_matches_lesson\": boolean}"
                },
                {
                    "role": "user",
                    "content": (
                        f"<transcript>{transcript}</transcript>\n\n"
                        f"<lesson_details>{script_details}</lesson_details>"
                    ),
                },
            ],
            session_id=session_id,
            response_format={"type": "json_object"},
            max_tokens=40000,  # Add max tokens to prevent truncation
        )

        if response.choices[0].message.content is None:
            raise RuntimeError("External API call failed: received None")

        raw_content = response.choices[0].message.content.strip()
        logger.info(f"Raw AI response length: {len(raw_content)}")
        logger.info(f"Raw AI response (first 200 chars): {raw_content[:200]}")
        
        try:
            import json
            
            # Clean up the JSON response
            cleaned_content = raw_content
            
            # Remove any markdown code blocks if present
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            
            cleaned_content = cleaned_content.strip()
            
            # Try to find the JSON object if there's extra text
            start_idx = cleaned_content.find('{')
            end_idx = cleaned_content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                cleaned_content = cleaned_content[start_idx:end_idx + 1]
            
            logger.info(f"Cleaned JSON content: {cleaned_content[:200]}...")
            
            json_response = json.loads(cleaned_content)
            keyword_equivalents = LessonDetailsExtractedKeywords(**json_response)
            logger.info("Successfully parsed JSON response from fallback")
            return keyword_equivalents
            
        except (json.JSONDecodeError, ValueError, TypeError) as parse_error:
            logger.error(f"Failed to parse JSON response: {parse_error}")
            logger.error(f"Raw response: {raw_content}")
            logger.error(f"Cleaned content: {cleaned_content if 'cleaned_content' in locals() else 'Not available'}")
            
            # Try to create a fallback response with minimal data
            try:
                # Extract key elements from script_details to create a fallback
                fallback_scripts = []
                for key_element in script_details.keyElements:
                    fallback_keywords = []
                    for keyword in key_element.keywords:
                        fallback_keywords.append({
                            "keyword": keyword,
                            "transcript_equivalent": "None"
                        })
                    
                    fallback_scripts.append({
                        "script": key_element.script,
                        "keywords_with_equivalents": fallback_keywords
                    })
                
                fallback_response = {
                    "scripts": fallback_scripts,
                    "transcript_matches_lesson": False
                }
                
                logger.info("Created fallback response due to JSON parsing failure")
                return LessonDetailsExtractedKeywords(**fallback_response)
                
            except Exception as fallback_error:
                logger.error(f"Fallback response creation failed: {fallback_error}")
                raise RuntimeError(f"Failed to parse AI response and create fallback: {parse_error}")


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
        session_id=session_id,
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
) -> tuple[str, int, int, str]:
    session_id = generate_session_id()
    logger.info(f"Lesson details: {script_details}")

    audio = read_audio(audio_filename)
    audio_analysis = await get_audio_analysis(audio, session_id)

    keyword_equivalents = await get_keyword_equivalents(
        transcript=audio_analysis.transcript,
        script_details=script_details,
        session_id=session_id,
    )
    logger.info(f"Keyword equivalents: {keyword_equivalents}")
    scores, matching_keywords = get_scores_and_matching_keywords(keyword_equivalents)
    logger.info(f"Scores: {scores}")
    logger.info(f"Matched keywords: {matching_keywords}")

    try:
        average_score = int(sum(scores.values()) / len(scores))
    except ZeroDivisionError:
        average_score = 0

    text_analysis = await get_text_analysis(
        transcript=audio_analysis.transcript,
        script_details=script_details,
        scores=scores,
        matching_keywords=matching_keywords,
        session_id=session_id,
    )
    speech_analysis = (
        SPEECH_ANALYSIS_SKIPPED
        if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.speaking_style_analysis
    )

    final_feedback = (
        f"{text_analysis}*only bolded keywords are mentioned during the recording\n\n"
        f"## Style Coaching Recommendations\n\n{speech_analysis}"
    )

    langfuse_log(
        session_id=session_id,
        trace_name="final-feedback",
        message=final_feedback,
        user_id=user_id,
        tags=tags,
    )

    confidence_score = (
        0
        if not keyword_equivalents.transcript_matches_lesson
        else audio_analysis.confidence_score
    )

    return (
        final_feedback,
        average_score,
        confidence_score,
        session_id,
    )
