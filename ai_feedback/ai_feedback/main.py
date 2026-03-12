import asyncio
import base64
import subprocess
import time
import traceback
import uuid
import os

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Form,
    Request,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from ai_feedback.ai import (
    get_feedback,
    judge_feedback,
    get_feedback_from_video,
    get_feedback_legacy,
)
from ai_feedback.authentication import verify_token, create_access_token
from ai_feedback.config import settings
from ai_feedback.models import (
    FeedbackInput,
    FeedbackResponse,
    ScriptDetails,
    SupportedLanguage,
    UserLikeRequest,
    LangfuseTracesRequest,
    StructuredFeedbackResponse,
    FeedbackResponseLegacy,
)
from ai_feedback.utils import (
    convert_video_to_audio,
    langfuse_user_like,
    fetch_feedback_input_output,
)

app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def delete_local_file(filepath: str):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted local temporary file: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to delete local temporary file: {e}")


@app.post("/login")
async def login(request: Request):
    body = await request.json()
    if (
        body.get("username") == settings.login_username
        and body.get("password") == settings.login_password
    ):
        token = create_access_token(data={"username": body.get("username")})
        return {"access_token": token, "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post(
    "/feedback",
    response_model=FeedbackResponseLegacy,
    dependencies=[Depends(verify_token)],
)
async def generate_feedback(
    video: UploadFile = File(...),
    feedback_input_str: str = Form(...),
    language: SupportedLanguage = Form(SupportedLanguage.ENGLISH),
):
    endpoint_start_time = time.time()
    timing_logs = []
    try:
        logger.info(f"Feedback request input {feedback_input_str}")
        feedback_input = FeedbackInput.model_validate_json(feedback_input_str)
        script_details = ScriptDetails(
            question=feedback_input.question,
            keyElements=feedback_input.keyElements,
            briefing=feedback_input.briefing,
        )

        t0 = time.time()
        video_content = await video.read()
        timing_logs.append(f"video_read: {time.time() - t0:.2f}s")

        base64_content_bytes = base64.b64encode(video_content)
        base64_content_str = base64_content_bytes.decode("utf-8")
        logger.info(f"base64Video {base64_content_str}")

        # Save video file
        t0 = time.time()
        video_filename = f"/tmp/{uuid.uuid4()}_{video.filename}"
        with open(video_filename, "wb") as f:
            f.write(video_content)
        timing_logs.append(f"video_write: {time.time() - t0:.2f}s")

        t0 = time.time()
        audio_filename = convert_video_to_audio(video_filename)
        timing_logs.append(f"convert_video_to_audio: {time.time() - t0:.2f}s")

        t0 = time.time()
        result = await get_feedback_legacy(
            audio_filename=audio_filename,
            script_details=script_details,
            user_id=feedback_input.user_id,
            tags=feedback_input.tags,
            language=language.value,
        )
        timing_logs.append(f"get_feedback_legacy: {time.time() - t0:.2f}s")

        asyncio.create_task(delete_local_file(video_filename))
        asyncio.create_task(delete_local_file(audio_filename))

        timing_logs.append(f"Total time: {time.time() - endpoint_start_time:.2f}s")
        logger.info(f"Performance [Endpoint /feedback]: {' | '.join(timing_logs)}")
        return FeedbackResponseLegacy(**result)

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e}")
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"{str(e)}\n\n{traceback.format_exc()}"
        )


@app.post(
    "/feedback_video",
    response_model=FeedbackResponse,
    dependencies=[Depends(verify_token)],
)
async def generate_feedback_video(
    video: UploadFile = File(...),
    feedback_input_str: str = Form(...),
    language: SupportedLanguage = Form(SupportedLanguage.ENGLISH),
):
    """
    Generate feedback from video using Gemini's multimodal capabilities.
    Processes video directly without converting to audio first.
    """
    endpoint_start_time = time.time()
    timing_logs = []
    try:
        logger.info(f"Video feedback request input {feedback_input_str}")
        feedback_input = FeedbackInput.model_validate_json(feedback_input_str)
        script_details = ScriptDetails(
            question=feedback_input.question,
            keyElements=feedback_input.keyElements,
            briefing=feedback_input.briefing,
        )

        t0 = time.time()
        video_content = await video.read()
        timing_logs.append(f"video_read: {time.time() - t0:.2f}s")

        # Save video file
        t0 = time.time()
        video_filename = f"/tmp/{uuid.uuid4()}_{video.filename}"
        with open(video_filename, "wb") as f:
            f.write(video_content)
        timing_logs.append(f"video_write: {time.time() - t0:.2f}s")

        # Process video directly using multimodal analysis
        t0 = time.time()
        result = await get_feedback_from_video(
            video_filename=video_filename,
            script_details=script_details,
            user_id=feedback_input.user_id,
            tags=feedback_input.tags,
            language=language.value,
        )
        timing_logs.append(f"get_feedback_from_video: {time.time() - t0:.2f}s")

        asyncio.create_task(delete_local_file(video_filename))

        timing_logs.append(f"Total time: {time.time() - endpoint_start_time:.2f}s")
        logger.info(
            f"Performance [Endpoint /feedback_video]: {' | '.join(timing_logs)}"
        )
        return FeedbackResponse(**result)

    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"{str(e)}\n\n{traceback.format_exc()}"
        )


@app.post(
    "/feedback_audio",
    response_model=StructuredFeedbackResponse,
    dependencies=[Depends(verify_token)],
)
async def generate_feedback_audio(
    video: UploadFile = File(...),
    feedback_input_str: str = Form(...),
    language: SupportedLanguage = Form(SupportedLanguage.ENGLISH),
):
    """
    Generate fully structured feedback.
    By default uses multimodal video analysis, falls back to audio-only if use_video_analysis is False.
    """
    endpoint_start_time = time.time()
    timing_logs = []
    try:
        feedback_input = FeedbackInput.model_validate_json(feedback_input_str)
        script_details = ScriptDetails(
            question=feedback_input.question,
            keyElements=feedback_input.keyElements,
            briefing=feedback_input.briefing,
        )

        t0 = time.time()
        video_content = await video.read()
        timing_logs.append(f"video_read: {time.time() - t0:.2f}s")

        t0 = time.time()
        video_filename = f"/tmp/{uuid.uuid4()}_{video.filename}"
        with open(video_filename, "wb") as f:
            f.write(video_content)
        timing_logs.append(f"video_write: {time.time() - t0:.2f}s")

        t0 = time.time()
        audio_filename = convert_video_to_audio(video_filename)
        timing_logs.append(f"convert_video_to_audio: {time.time() - t0:.2f}s")

        t0 = time.time()
        result = await get_feedback(
            audio_filename=audio_filename,
            script_details=script_details,
            user_id=feedback_input.user_id,
            tags=feedback_input.tags,
            language=language.value,
        )
        timing_logs.append(f"get_feedback: {time.time() - t0:.2f}s")
        asyncio.create_task(delete_local_file(video_filename))
        asyncio.create_task(delete_local_file(audio_filename))

        timing_logs.append(f"Total time: {time.time() - endpoint_start_time:.2f}s")
        logger.info(
            f"Performance [Endpoint /feedback_structured]: {' | '.join(timing_logs)}"
        )
        return StructuredFeedbackResponse(**result)

    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"{str(e)}\n\n{traceback.format_exc()}"
        )


@app.post("/like", dependencies=[Depends(verify_token)])
async def user_like(req: UserLikeRequest):
    try:
        langfuse_user_like(req.session_id, req.positive_feedback)
        if not req.positive_feedback:
            asyncio.create_task(
                judge_session(LangfuseTracesRequest(session_id=req.session_id))
            )
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"{str(e)}\n\n{traceback.format_exc()}"
        )


@app.post("/judge", dependencies=[Depends(verify_token)])
async def judge_session(req: LangfuseTracesRequest):
    try:
        ai_input, ai_feedback = fetch_feedback_input_output(req.session_id)
        await judge_feedback(
            ai_input=ai_input, ai_feedback=ai_feedback, session_id=req.session_id
        )
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"{str(e)}\n\n{traceback.format_exc()}"
        )
