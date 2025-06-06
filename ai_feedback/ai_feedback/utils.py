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


def langfuse_user_like(session_id: str, positive_feedback: bool):
    traces = lf.fetch_traces(session_id=session_id, order_by="timestamp.asc")
    output_trace_id = str(traces.data[3].id)

    lf.score(
        trace_id=output_trace_id,
        name="User Opinion",
        data_type="CATEGORICAL",
        value="Like" if positive_feedback else "Dislike",
    )


def fetch_feedback_input_output(session_id: str) -> tuple[str, str]:
    traces = lf.fetch_traces(session_id=session_id, order_by="timestamp.asc")
    ai_input = str(traces.data[1].input["messages"][1]["content"])  # pyright: ignore
    ai_feedback = str(traces.data[3].output)

    return ai_input, ai_feedback
