# Stage 1: Base image with Python and Tesseract
FROM python:3.10-slim-bullseye

LABEL maintainer="Miricle"
LABEL description="Container for Trinetra with Tesseract OCR."

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PATH="/root/.local/bin:${PATH}"

# Install Tesseract OCR and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    build-essential \
    wget \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Build and install SQLite 3.35+ from source
RUN wget https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz && \
    tar xzf sqlite-autoconf-3420000.tar.gz && \
    cd sqlite-autoconf-3420000 && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    cd .. && \
    rm -rf sqlite-autoconf-3420000 sqlite-autoconf-3420000.tar.gz && \
    ldconfig

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Set up a working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY requirements.txt .

# Install external dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
COPY src/ ./src/

# Pip will find pyproject.toml and the src/trinetra package and create the
# 'trinetra' executable in /root/.local/bin/.
RUN pip install --no-cache-dir .

ENTRYPOINT ["trinetra"]
