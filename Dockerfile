FROM python:3.11-slim

# system libs required by OpenCV + InsightFace (onnxruntime needs libGL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF Spaces uses port 7860
ENV PORT=7860
ENV HOST=0.0.0.0

# App artifacts go in /data (HF Spaces persistent storage)
ENV ROOT_DIR=/data

# Photos come from OneDrive — set SOURCE_TYPE + credentials in Space Secrets
# No default PHOTOS_DIR; must be supplied via env var SECRET

EXPOSE 7860

CMD ["sh", "-c", "python startup.py && uvicorn main:app --host $HOST --port $PORT"]
