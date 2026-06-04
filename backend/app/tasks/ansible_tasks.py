"""
Ansible playbook execution tasks via SSH.
"""

from collections.abc import Generator
from pathlib import Path

import paramiko
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SCRIPTS_DIRECTORY = Path(__file__).parent.parent.parent / "scripts" / "shells"


class SSHCommandExecutor:
    """Execute commands over SSH using paramiko."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str | None = None,
        key_path: str | None = None,
    ):
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
            logger.info(
                "脚本已上传",
                extra={"action": "ansible.run", "host": self.host, "remote_path": remote_path},
            )
            return True
        except Exception as e:
            logger.error(f"脚本上传失败: {str(e)}", extra={"action": "ansible.run"})
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
            "SSH连接成功",
            extra={
                "action": "ansible.run",
                "host": settings.ansible_ssh_host,
                "port": settings.ansible_ssh_port,
            },
        )

        if settings.ansible_local_script_path:
            script_path = Path(settings.ansible_local_script_path)
            if not script_path.is_absolute():
                script_path = SCRIPTS_DIRECTORY / script_path

            if not script_path.exists():
                executor.close()
                return False, f"Local script file not found: {script_path}"

            script_content = script_path.read_text(encoding="utf-8")
            logger.debug(
                "读取本地脚本文件", extra={"action": "ansible.run", "script_path": str(script_path)}
            )
            upload_success = executor.upload_script(script_content, "/tmp/execute_script.sh")
            if not upload_success:
                executor.close()
                return False, "Failed to upload script to remote server"

            command_to_execute = "bash /tmp/execute_script.sh"
        elif settings.ansible_script:
            logger.info("检测到脚本模式，上传并执行脚本", extra={"action": "ansible.run"})
            upload_success = executor.upload_script(
                settings.ansible_script, "/tmp/execute_script.sh"
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
                logger.info(f"[ansible] {stdout}", extra={"action": "ansible.run"})
            if stderr:
                error_lines.append(stderr)
                logger.warning(f"[ansible] {stderr}", extra={"action": "ansible.run"})

        executor.close()

        if error_lines:
            return False, "\n".join(error_lines)

        full_output = "\n".join(output_lines)
        return True, full_output

    except paramiko.AuthenticationException:
        error_msg = f"SSH authentication failed for {settings.ansible_ssh_username}@{settings.ansible_ssh_host}"
        logger.error(error_msg, extra={"action": "ansible.run"})
        return False, error_msg

    except paramiko.SSHException as e:
        error_msg = f"SSH connection error: {str(e)}"
        logger.error(error_msg, extra={"action": "ansible.run"})
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error executing ansible command: {str(e)}"
        logger.error(error_msg, extra={"action": "ansible.run"})
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
            "SSH连接成功",
            extra={
                "action": "ansible.run",
                "host": settings.ansible_ssh_host,
                "port": settings.ansible_ssh_port,
            },
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
                logger.info(f"[script] {stdout}", extra={"action": "ansible.run"})
            if stderr:
                error_lines.append(stderr)
                logger.warning(f"[script] {stderr}", extra={"action": "ansible.run"})

        executor.close()

        if error_lines:
            return False, "\n".join(error_lines)

        full_output = "\n".join(output_lines)
        return True, full_output

    except paramiko.AuthenticationException:
        error_msg = f"SSH authentication failed for {settings.ansible_ssh_username}@{settings.ansible_ssh_host}"
        logger.error(error_msg, extra={"action": "ansible.run"})
        return False, error_msg

    except paramiko.SSHException as e:
        error_msg = f"SSH connection error: {str(e)}"
        logger.error(error_msg, extra={"action": "ansible.run"})
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error executing script: {str(e)}"
        logger.error(error_msg, extra={"action": "ansible.run"})
        return False, error_msg


@retry(stop=stop_after_attempt(3), wait=wait_fixed(300))
def execute_ansible_playbook_task():
    """Execute ansible playbook on remote server via SSH.

    This task connects to the configured Ansible server and runs
    the ansible-playbook command. If ANSIBLE_SCRIPT is configured,
    it will upload and execute the script instead.
    """
    logger.info("开始Ansible Playbook执行任务", extra={"action": "ansible.run"})

    success, message = execute_ansible_command()

    if success:
        logger.info("Ansible Playbook执行完成", extra={"action": "ansible.run"})
    else:
        logger.error(f"Ansible Playbook执行失败: {message}", extra={"action": "ansible.run"})
        raise Exception(message)

    return {"status": "success" if success else "failed", "message": message}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(300))
def execute_remote_script_task(script_content: str):
    """Execute a shell script on the remote server via SSH.

    Args:
        script_content: The shell script content to execute.
    """
    logger.info("开始远程脚本执行", extra={"action": "ansible.run"})

    success, message = execute_remote_script(script_content, "/tmp/execute_script.sh")

    if success:
        logger.info("远程脚本执行完成", extra={"action": "ansible.run"})
    else:
        logger.error(f"远程脚本执行失败: {message}", extra={"action": "ansible.run"})
        raise Exception(message)

    return {"status": "success" if success else "failed", "message": message}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(300))
def execute_named_script_task(script_name: str):
    """Execute a named script from the local shells directory on remote server.

    Args:
        script_name: Name of the script file in backend/scripts/shells/ directory.
    """
    script_path = SCRIPTS_DIRECTORY / script_name

    if not script_path.exists():
        logger.error(f"脚本文件未找到: {script_path}", extra={"action": "ansible.run"})
        raise Exception(f"Script file not found: {script_path}")

    script_content = script_path.read_text(encoding="utf-8")
    logger.info("执行命名脚本", extra={"action": "ansible.run", "script_name": script_name})

    success, message = execute_remote_script(script_content, "/tmp/execute_script.sh")

    if success:
        logger.info("命名脚本执行完成", extra={"action": "ansible.run"})
    else:
        logger.error(f"命名脚本执行失败: {message}", extra={"action": "ansible.run"})
        raise Exception(message)

    return {"status": "success" if success else "failed", "message": message}
