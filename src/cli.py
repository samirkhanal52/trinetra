import logging
import os
import subprocess
import sys

import click
import psutil

import src.config as config
import src.utils as utils
from src.indexing_service import IndexingService
from src.rag_query import query_trinetra
from src.recorder import RecorderService
from src.uploader import UploaderService


# --- Helper Functions for Service Management ---
def _start_service(service_name: str, pid_file: str):
    """Launches a service in the foreground."""
    pid = utils.get_pid_from_file(pid_file)
    if pid and psutil.pid_exists(pid):
        logging.warning(
            f"{service_name.capitalize()} service (PID: {pid}) is already running."
        )
        return

    click.echo(f"Starting {service_name} service in foreground...")
    
    # Run the service directly instead of spawning a detached process
    if service_name == "recorder":
        service = RecorderService()
        service.run_forever()
    elif service_name == "uploader":
        service = UploaderService()
        service._upload_loop()
    elif service_name == "indexing":
        service = IndexingService()
        service.run_forever()
    else:
        click.echo(f"Unknown service: {service_name}")
        sys.exit(1)


def _stop_service(pid_file: str):
    # ... (this function remains the same, it correctly kills by PID) ...
    pid = utils.get_pid_from_file(pid_file)
    if not pid or not psutil.pid_exists(pid):
        logging.warning("Service process not found or PID file is stale.")
        if os.path.exists(pid_file):
            os.remove(pid_file)
        return

    try:
        p = psutil.Process(pid)
        p.terminate()  # Sends SIGTERM
        p.wait(timeout=5)
        logging.info(f"Successfully stopped process (PID: {pid}).")
    except psutil.NoSuchProcess:
        logging.error(f"No process with PID {pid} found.")
    except psutil.TimeoutExpired:
        logging.warning(f"Process {pid} did not terminate gracefully. Killing.")
        p.kill()  # Sends SIGKILL
    except Exception as e:
        logging.error(f"Failed to stop process {pid}: {e}")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)


# --- Main CLI Group ---
@click.group()
def cli():
    """Trinetra: A CLI tool for screen recording, uploading, and analysis."""
    # Note: utils.setup_logging() is called by the actual running process,
    # not just the launcher.
    pass


# --- Public Commands (Launchers) ---
@cli.group()
def recorder():
    """Commands to control the screen recorder service."""
    pass


@recorder.command("start")
def recorder_start():
    """Starts the screen recorder as a background process."""
    utils.setup_logging()
    if not config.validate_config():
        raise click.Abort()

    # I've updated the prompt to be more clear.
    consent = click.prompt(
        "This will record your screen and save images locally. The uploader service will move them to the cloud. Type [Y] to continue."
    )
    if consent != "Y":
        click.echo("Consent not given. Aborting.")
        return
    _start_service("recorder", config.RECORDER_PID_FILE)


@recorder.command("stop")
def recorder_stop():
    """Stops the screen recorder service."""
    utils.setup_logging()
    _stop_service(config.RECORDER_PID_FILE)


@cli.group()
def uploader():
    """Commands to control the S3/MinIO uploader service."""
    pass


@uploader.command("start")
def uploader_start():
    """Starts the uploader service as a background process."""
    utils.setup_logging()
    if not config.validate_config():
        raise click.Abort()
    _start_service("uploader", config.UPLOADER_PID_FILE)


@uploader.command("stop")
def uploader_stop():
    """Stops the uploader service."""
    utils.setup_logging()
    _stop_service(config.UPLOADER_PID_FILE)


# --- Agent Service Group ---
@cli.group()
def indexing():
    """Commands to control the GenAI indexing service."""
    pass


@indexing.command("start")
def indexing_start():
    """Starts the indexing service as a background process."""
    utils.setup_logging()
    config.validate_config()
    click.echo("This service should be run inside the Docker container.")
    _start_service("indexing", config.INDEXING_PID_FILE)


@indexing.command("stop")
def indexing_stop():
    """Stops the indexing service."""
    utils.setup_logging()
    _stop_service(config.INDEXING_PID_FILE)


@cli.command()
@click.argument("question", type=str)
def query(question: str):
    """Ask a question about your past activity using the RAG pipeline."""
    utils.setup_logging()
    config.validate_config()
    click.echo("Querying your indexed history... (this may take a moment)")

    response = query_trinetra(question)

    click.echo("\n--- Answer ---")
    click.echo(response)


@cli.command("_run-indexing", hidden=True)
def _run_indexing():
    utils.setup_logging()
    config.validate_config()
    service = IndexingService()
    service.run_forever()


# --- Hidden Commands (Actual Service Runners) ---
@cli.command("_run-recorder", hidden=True)
def _run_recorder():
    """(Internal) Runs the recorder service's main loop."""
    utils.setup_logging()
    if not config.validate_config():
        sys.exit(1)
    service = RecorderService()
    service.run_forever()


@cli.command("_run-uploader", hidden=True)
def _run_uploader():
    """(Internal) Runs the uploader service's main loop."""
    utils.setup_logging()
    if not config.validate_config():
        sys.exit(1)
    service = UploaderService()


if __name__ == "__main__":
    # This makes 'python -m trinetra.cli ...' work
    cli()
