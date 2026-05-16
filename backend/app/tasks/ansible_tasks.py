"""
Ansible playbook execution tasks via SSH.
"""

from pathlib import Path
from typing import Generator

import paramiko
from celery import shared_task

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SCRIPTS_DIRECTORY = Path(__file__).parent.parent.parent / "scripts" / "shells"


class SSHCommandExecutor:
    """Execute commands over SSH using paramiko."""

    def __init__(self, host: str, port: int, username: str, password: str | None = None, key_path: str | None = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        """Establish SSH connection."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if self.key_path:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                key_filename=self.key_path,
                timeout=30,
            )
        else:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=30,
            )

    def execute_command(self, command: str) -> Generator[tuple[str, str], None, None]:
        """Execute a command and yield output lines.

        Yields: (stdout_line, stderr_line)
        """
        if not self.client:
            raise RuntimeError("SSH client not connected. Call connect() first.")

        stdin, stdout, stderr = self.client.exec_command(command, get_pty=True)

        stdout_lines = stdout.readlines()
        stderr_lines = stderr.readlines()

        for line in stdout_lines:
            yield line.rstrip("\n"), ""

        for line in stderr_lines:
            yield "", line.rstrip("\n")

    def upload_script(self, script_content: str, remote_path: str) -> bool:
        """Upload a script file to the remote server.

        Args:
            script_content: The script content to upload.
            remote_path: The path where the script will be saved on remote server.

        Returns:
            True if upload was successful, False otherwise.
        """
        if not self.client:
            raise RuntimeError("SSH client not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            with sftp.file(remote_path, "w") as remote_file:
                remote_file.write(script_content)
            sftp.close()
            self.client.exec_command(f"chmod +x {remote_path}")
            logger.info(f"Script uploaded to {self.host}:{remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload script: {str(e)}")
            return False

    def close(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def execute_ansible_command() -> tuple[bool, str]:
    """Execute ansible playbook command via SSH.

    Returns: (success, message)
    """
    try:
        executor = SSHCommandExecutor(
            host=settings.ansible_ssh_host,
            port=settings.ansible_ssh_port,
            username=settings.ansible_ssh_username,
            password=settings.ansible_ssh_password,
            key_path=settings.ansible_ssh_key_path,
        )

        executor.connect()
        logger.info(
            f"SSH connected to {settings.ansible_ssh_host}:{settings.ansible_ssh_port} as {settings.ansible_ssh_username}"
        )

        if settings.ansible_local_script_path:
            script_path = Path(settings.ansible_local_script_path)
            if not script_path.is_absolute():
                script_path = SCRIPTS_DIRECTORY / script_path

            if not script_path.exists():
                executor.close()
                return False, f"Local script file not found: {script_path}"

            script_content = script_path.read_text(encoding="utf-8")
            logger.info(f"Reading script from local file: {script_path}")
            upload_success = executor.upload_script(script_content, "/tmp/execute_script.sh")
            if not upload_success:
                executor.close()
                return False, "Failed to upload script to remote server"

            command_to_execute = "bash /tmp/execute_script.sh"
        elif settings.ansible_script:
            logger.info("Script mode detected, uploading and executing script")
            upload_success = executor.upload_script(
                settings.ansible_script,
                "/tmp/execute_script.sh"
            )
            if not upload_success:
                executor.close()
                return False, "Failed to upload script to remote server"

            command_to_execute = "bash /tmp/execute_script.sh"
        else:
            command_to_execute = settings.ansible_command

        output_lines = []
        error_lines = []

        for stdout, stderr in executor.execute_command(command_to_execute):
            if stdout:
                output_lines.append(stdout)
                logger.info(f"[ansible] {stdout}")
            if stderr:
                error_lines.append(stderr)
                logger.warning(f"[ansible] {stderr}")

        executor.close()

        if error_lines:
            return False, "\n".join(error_lines)

        full_output = "\n".join(output_lines)
        return True, full_output

    except paramiko.AuthenticationException:
        error_msg = f"SSH authentication failed for {settings.ansible_ssh_username}@{settings.ansible_ssh_host}"
        logger.error(error_msg)
        return False, error_msg

    except paramiko.SSHException as e:
        error_msg = f"SSH connection error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error executing ansible command: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def execute_remote_script(script_content: str) -> tuple[bool, str]:
    """Execute a shell script on the remote server via SSH.

    Args:
        script_content: The shell script content to execute.

    Returns: (success, message)
    """
    try:
        executor = SSHCommandExecutor(
            host=settings.ansible_ssh_host,
            port=settings.ansible_ssh_port,
            username=settings.ansible_ssh_username,
            password=settings.ansible_ssh_password,
            key_path=settings.ansible_ssh_key_path,
        )

        executor.connect()
        logger.info(
            f"SSH connected to {settings.ansible_ssh_host}:{settings.ansible_ssh_port} as {settings.ansible_ssh_username}"
        )

        upload_success = executor.upload_script(script_content, "/tmp/execute_script.sh")
        if not upload_success:
            executor.close()
            return False, "Failed to upload script to remote server"

        command_to_execute = "bash /tmp/execute_script.sh"
        output_lines = []
        error_lines = []

        for stdout, stderr in executor.execute_command(command_to_execute):
            if stdout:
                output_lines.append(stdout)
                logger.info(f"[script] {stdout}")
            if stderr:
                error_lines.append(stderr)
                logger.warning(f"[script] {stderr}")

        executor.close()

        if error_lines:
            return False, "\n".join(error_lines)

        full_output = "\n".join(output_lines)
        return True, full_output

    except paramiko.AuthenticationException:
        error_msg = f"SSH authentication failed for {settings.ansible_ssh_username}@{settings.ansible_ssh_host}"
        logger.error(error_msg)
        return False, error_msg

    except paramiko.SSHException as e:
        error_msg = f"SSH connection error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error executing script: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


@shared_task(bind=True, max_retries=3)
def execute_ansible_playbook_task(self):
    """Execute ansible playbook on remote server via SSH.

    This task connects to the configured Ansible server and runs
    the ansible-playbook command. If ANSIBLE_SCRIPT is configured,
    it will upload and execute the script instead.
    """
    logger.info("Starting ansible playbook execution task")

    success, message = execute_ansible_command()

    if success:
        logger.info("Ansible playbook execution completed successfully")
    else:
        logger.error(f"Ansible playbook execution failed: {message}")
        raise self.retry(exc=Exception(message), countdown=300)

    return {"status": "success" if success else "failed", "message": message}


@shared_task(bind=True, max_retries=3)
def execute_remote_script_task(self, script_content: str):
    """Execute a shell script on the remote server via SSH.

    Args:
        script_content: The shell script content to execute.
    """
    logger.info("Starting remote script execution")

    success, message = execute_remote_script(script_content, "/tmp/execute_script.sh")

    if success:
        logger.info("Remote script execution completed successfully")
    else:
        logger.error(f"Remote script execution failed: {message}")
        raise self.retry(exc=Exception(message), countdown=300)

    return {"status": "success" if success else "failed", "message": message}


@shared_task(bind=True, max_retries=3)
def execute_named_script_task(self, script_name: str):
    """Execute a named script from the local shells directory on remote server.

    Args:
        script_name: Name of the script file in backend/scripts/shells/ directory.
    """
    script_path = SCRIPTS_DIRECTORY / script_name

    if not script_path.exists():
        logger.error(f"Script file not found: {script_path}")
        raise Exception(f"Script file not found: {script_path}")

    script_content = script_path.read_text(encoding="utf-8")
    logger.info(f"Executing named script: {script_name} from {script_path}")

    success, message = execute_remote_script(script_content, "/tmp/execute_script.sh")

    if success:
        logger.info("Named script execution completed successfully")
    else:
        logger.error(f"Named script execution failed: {message}")
        raise self.retry(exc=Exception(message), countdown=300)

    return {"status": "success" if success else "failed", "message": message}
