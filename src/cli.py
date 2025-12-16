import click
import os
import sys
import logging
import psutil
import subprocess

import utils, config
from recorder import RecorderService
from uploader import UploaderService
from indexing_service import AgentService

# --- Helper Functions for Service Management ---
def _start_service(service_name: str, pid_file: str):
    """Launches a service as a detached background process."""
    pid = utils.get_pid_from_file(pid_file)
    if pid and psutil.pid_exists(pid):
        logging.warning(f"{service_name.capitalize()} service (PID: {pid}) is already running.")
        return

    command = [sys.executable, "-m", "cli", f"_run-{service_name}"]

    # Platform-specific flags to run the process in the background detached from the console.
    creationflags = 0
    preexec_fn = None
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS
    else: # POSIX
        preexec_fn = os.setsid

    click.echo(f"Starting {service_name} service... It will run as a detached background process.")
    
    # We don't store the Popen object, it's fire-and-forget.
    # The new process is responsible for its own lifecycle.
    subprocess.Popen(command, creationflags=creationflags, preexec_fn=preexec_fn, close_fds=True)

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
        p.terminate() # Sends SIGTERM
        p.wait(timeout=5)
        logging.info(f"Successfully stopped process (PID: {pid}).")
    except psutil.NoSuchProcess:
        logging.error(f"No process with PID {pid} found.")
    except psutil.TimeoutExpired:
        logging.warning(f"Process {pid} did not terminate gracefully. Killing.")
        p.kill() # Sends SIGKILL
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
    consent = click.prompt("This will record your screen and save images locally. The uploader service will move them to the cloud. Type [Y] to continue.")
    if consent != "Y":
        click.echo("Consent not given. Aborting.")
        return
    _start_service("recorder", config.RECORDER_PID_FILE)

@recorder.command("stop")
def recorder_stop():
    """Stops the screen recorder service."""
    utils.setup_logging()
    _stop_service(config.RECORDER_PID_FILE)


# @cli.group()
# def uploader():
#     """Commands to control the S3/MinIO uploader service."""
#     pass

# @uploader.command("start")
# def uploader_start():
#     """Starts the uploader service as a background process."""
#     utils.setup_logging()
#     if not config.validate_config():
#         raise click.Abort()
#     _start_service("uploader", config.UPLOADER_PID_FILE)

# @uploader.command("stop")
# def uploader_stop():
#     """Stops the uploader service."""
#     utils.setup_logging()
#     _stop_service(config.UPLOADER_PID_FILE)

# --- Agent Service Group ---
@cli.group()
def agent():
    """Commands to control the analysis agent service."""
    pass

@agent.command("start")
def agent_start():
    """Starts the agent service as a background process."""
    utils.setup_logging()
    if not config.validate_config():
        raise click.Abort()
    click.echo("This service should be run inside the Docker container.")
    _start_service("agent", config.AGENT_PID_FILE)

@agent.command("stop")
def agent_stop():
    """Stops the agent service."""
    utils.setup_logging()
    _stop_service(config.AGENT_PID_FILE)


# --- Hidden Commands (Actual Service Runners) ---
@cli.command("_run-recorder", hidden=True)
def _run_recorder():
    """(Internal) Runs the recorder service's main loop."""
    utils.setup_logging()
    if not config.validate_config():
        sys.exit(1)
    service = RecorderService()
    service.run_forever()

# @cli.command("_run-uploader", hidden=True)
# def _run_uploader():
#     """(Internal) Runs the uploader service's main loop."""
#     utils.setup_logging()
#     if not config.validate_config():
#         sys.exit(1)
#     service = UploaderService()
#     service.run_forever()

@cli.command("_run-agent", hidden=True)
def _run_agent():
    """(Internal) Runs the agent service's main loop."""
    utils.setup_logging()
    if not config.validate_config():
        sys.exit(1)
    service = AgentService()
    service.run_forever()

if __name__ == '__main__':
    # This makes 'python -m trinetra.cli ...' work
    cli()
