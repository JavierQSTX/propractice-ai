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

from ai_feedback.ai import get_feedback
from ai_feedback.models import FeedbackInput, FeedbackResponse, ScriptDetails
from ai_feedback.utils import convert_video_to_audio
from ai_feedback.config import settings
from ai_feedback.authentication import verify_token, create_access_token


app = FastAPI()


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

        feedback = await get_feedback(audio_filename, script_details)
        return FeedbackResponse(feedback=feedback)

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
