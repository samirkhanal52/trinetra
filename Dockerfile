# Stage 1: Base image with Python and Tesseract
FROM python:3.10-slim-bullseye

LABEL maintainer="Miricle"
LABEL description="Container for Trinetra with Tesseract OCR."

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PATH="/root/.local/bin:${PATH}"

# Install Tesseract OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up a working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
COPY src/ ./src/

# Pip will find pyproject.toml and the src/trinetra package and create the
# 'trinetra' executable in /root/.local/bin/.
RUN pip install --no-cache-dir .

# Set the entrypoint to our new CLI tool name
ENTRYPOINT ["trinetra"]
