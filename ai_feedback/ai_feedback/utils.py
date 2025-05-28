import subprocess
from uuid import uuid4
from langfuse import Langfuse

lf = Langfuse()


def read_audio(audio_filename: str) -> bytes:
    with open(audio_filename, "rb") as f:
        return f.read()


def convert_video_to_audio(video_filename: str) -> str:
    audio_filename = video_filename.rsplit(".", 1)[0] + ".mp3"
    subprocess.run(
        ["ffmpeg", "-i", video_filename, "-q:a", "0", "-map", "a", audio_filename],
        check=True,
    )
    return audio_filename


def generate_session_id() -> str:
    return str(uuid4())


def langfuse_log(
    *,
    session_id: str,
    trace_name: str,
    message: str,
    user_id: str | None,
    tags: list[str] | None,
) -> str:
    trace = lf.trace(
        session_id=session_id,
        name=trace_name,
        output=message,
        user_id=user_id,
        tags=tags,
    )
    return trace.trace_id


def langfuse_user_like(trace_id: str, positive_feedback: bool):
    lf.score(
        trace_id=trace_id,
        name="User Opinion",
        data_type="CATEGORICAL",
        value="Like" if positive_feedback else "Dislike",
    )
