import PyPDF2
import subprocess


def extract_text_from_pdf(pdf_filename: str) -> str:
    reader = PyPDF2.PdfReader(pdf_filename)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


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
