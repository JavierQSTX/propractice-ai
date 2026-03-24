FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Set HF_HOME so that huggingface caches the model into the image itself
ENV HF_HOME=/app/models_cache

# Download the Whisper model during build to prevent read-only filesystem errors and speed up cold starts
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

COPY . .

EXPOSE 8080

CMD ["uvicorn", "ai_feedback.main:app", "--host", "0.0.0.0", "--port", "8080","--timeout-keep-alive", "120"]
