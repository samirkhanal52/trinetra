## Project Structure

```
trinetra/
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore file
├── docker-compose.yml         # For running MinIO locally
├── docs/
│   └── Security_Privacy_Checklist.md
├── pyproject.toml             # Python project metadata
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── src/
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── config.py              # Configuration management
│   ├── recorder.py            # Screen recording functionality
│   ├── uploader.py            # S3/MinIO upload functionality
│   └── utils.py               # Shared utilities
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── ...                    # Other test files
```

# Trinetra CLI

A powerful, two-service command-line tool for Windows to record screen activity and upload it securely to Amazon S3 or a local MinIO instance.

## Architecture

This tool is composed of two independent services:
1.  **Recorder Service**: Captures a screenshot of the primary monitor every second and saves it along with a metadata JSON file to a local `data/outbox` directory.
2.  **Uploader Service**: Watches the `data/outbox` directory, uploads new image/metadata pairs to the cloud (S3 or MinIO), and deletes the local files upon success.

This decoupled design ensures that screen recording can continue even if the network is unavailable. The uploader will automatically catch up once connectivity is restored.

... (Features, Prerequisites sections remain similar) ...

## Prerequisites

1.  **Python 3.8+**: Make sure Python is installed and in your PATH.
2.  **Tesseract OCR**: This tool depends on Google's Tesseract OCR engine.
    - [Download and install for Windows](https://github.com/UB-Mannheim/tesseract/wiki).
    - During installation, make sure to add Tesseract to your system's PATH.
3.  **AWS Account**: An AWS account with an S3 bucket and IAM user credentials.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/samirkhanal52/trinetra-cli.git
    cd trinetra-cli
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # On Windows
    # source venv/bin/activate  # On Linux/macOS
    ```

3.  **Install the package in editable mode:**
    ```bash
    pip install -e .
    ```
    This command also installs all required dependencies from `pyproject.toml`. The first run may take a while as it downloads the PyTorch and HuggingFace models.

## Configuration

The tool is configured using a `.env` file.

1.  Copy `.env.example` to `.env`.
2.  Edit the `.env` file. You can choose between using AWS S3 for production or a local MinIO instance for development.

-   **To use local MinIO**: Set `TRINETRA_ENV="local"` and fill in the `MINIO_*` variables.
-   **To use AWS S3**: Set `TRINETRA_ENV="prod"` and fill in the `AWS_*` variables.

## Local Development with MinIO

For easy local testing without needing an AWS account, you can run a local S3-compatible server using MinIO and Docker.

1.  **Install Docker and Docker Compose.**
2.  **Start the MinIO service:**
    ```bash
    docker-compose up -d
    ```
3.  **Access the MinIO Console:** Open your browser and go to `http://localhost:9001`. Log in with the credentials from your `.env` file (default: `minioadmin`/`minioadmin`).
4.  The uploader service will automatically create the required bucket on its first run.

## Usage

The CLI is now organized into groups for each service.

### Controlling the Services

**Start the recorder:**
```bash
screenrec recorder start
