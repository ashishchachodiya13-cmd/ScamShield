FROM python:3.11-slim

# Install system dependencies: Tesseract OCR, English & Hindi language data
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Environment settings
ENV PYTHONUNBUFFERED=1

# Expose default port
EXPOSE 8000

# Start server using Render's dynamic $PORT (defaults to 8000 if not set)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
