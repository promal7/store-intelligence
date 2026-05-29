FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies needed for OpenCV, SQLite, and video processing
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libgl1-mesa-glx     libglib2.0-0     curl     && rm -rf /var/lib/apt/lists/*

# Copy package management blueprints
COPY requirements.txt .

# Install dependencies globally inside the container
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir -r requirements.txt

# Create application data and pipeline layout mounts
RUN mkdir -p data/clips app pipeline

# Copy operational repository tree elements
COPY app/ app/
COPY pipeline/ pipeline/

EXPOSE 8000

# Fire up production web service layer
CMD ["uvicorn", "app.main:main", "--host", "0.0.0.0", "--port", "8000"]
