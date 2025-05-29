import uuid
import subprocess
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Form,
    Request,
    Depends,
)
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import traceback

from ai_feedback.ai import get_feedback, judge_feedback
from ai_feedback.models import (
    FeedbackInput,
    FeedbackResponse,
    ScriptDetails,
    UserLikeRequest,
    LangfuseTracesRequest,
)
from ai_feedback.utils import (
    convert_video_to_audio,
    langfuse_user_like,
    fetch_feedback_input_output,
)
from ai_feedback.config import settings
from ai_feedback.authentication import verify_token, create_access_token
import asyncio


app = FastAPI()


origins = ["http://localhost", "http://localhost:3000", "https://cbway.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    "/feedback", response_model=FeedbackResponse, dependencies=[Depends(verify_token)]
)
async def generate_feedback(
    video: UploadFile = File(...), feedback_input_str: str = Form(...)
):
    try:
        logger.info(f"Feedback request input {feedback_input_str}")
        feedback_input = FeedbackInput.model_validate_json(feedback_input_str)
        script_details = ScriptDetails(
            question=feedback_input.question,
            keyElements=feedback_input.keyElements,
            briefing=feedback_input.briefing,
        )

        # Save video file
        video_filename = f"/tmp/{uuid.uuid4()}_{video.filename}"
        with open(video_filename, "wb") as f:
            f.write(await video.read())

        audio_filename = convert_video_to_audio(video_filename)

        feedback, average_score, confidence_score, session_id = await get_feedback(
            audio_filename=audio_filename,
            script_details=script_details,
            user_id=feedback_input.user_id,
            tags=feedback_input.tags,
        )
        return FeedbackResponse(
            feedback=feedback,
            accuracy=average_score,
            confidence=confidence_score,
            session_id=session_id,
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e}")
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
