import uuid
import subprocess
from fastapi import FastAPI, File, UploadFile, HTTPException

from ai_feedback.ai import get_feedback
from ai_feedback.models import FeedbackResponse
from ai_feedback.utils import convert_video_to_audio

app = FastAPI()


@app.post("/feedback")
async def generate_feedback(video: UploadFile = File(...), pdf: UploadFile = File(...)):
    try:
        # Save video file
        video_filename = f"/tmp/{uuid.uuid4()}_{video.filename}"
        with open(video_filename, "wb") as f:
            f.write(await video.read())

        # Save PDF file
        pdf_filename = f"/tmp/{uuid.uuid4()}_{pdf.filename}"
        with open(pdf_filename, "wb") as f:
            f.write(await pdf.read())

        audio_filename = convert_video_to_audio(video_filename)

        feedback = get_feedback(audio_filename, pdf_filename)
        return FeedbackResponse(feedback=feedback)

    except subprocess.CalledProcessError as e:
        return HTTPException(status_code=500, detail=f"FFmpeg error: {e}")
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
