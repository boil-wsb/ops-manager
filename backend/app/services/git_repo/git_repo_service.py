"""Git 仓库读写双向管理服务。

在容器内通过 subprocess 调用 git，对 GitLab 上的 prometheus 项目进行
克隆、拉取、提交、推送、分支/标签切换、日志与状态查看，并支持
sparse-checkout 只检出指定路径。认证 token 存于设置，仅按命令动态注入，
绝不写入 `git remote` 或日志。
"""

import base64
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.exceptions import AppException, ConflictError
from app.core.logging import get_logger

logger = get_logger("git_repo")


class GitRepoService:
    """prometheus 仓库的 git 操作封装。"""

    def __init__(self) -> None:
        self.repo_url: str = settings.git_repo_url.rstrip("/")
        self.token: str = settings.git_private_token
        self.repo_dir = Path(settings.git_repo_base_dir_abs) / self._repo_name()
        self.sparse_paths: list[str] = list(settings.git_repo_sparse_path_list)
        self.timeout: int = settings.git_command_timeout
        # 串行化 pull/push/status 等目录变更操作，避免定时任务与前端并发写坏仓库
        self._lock = threading.RLock()

    # ---------- 内部工具 ----------
    def _repo_name(self) -> str:
        """从仓库 URL 提取目录名，如 prometheus.git -> prometheus。"""
        name = self.repo_url.rsplit("/", 1)[-1]
        return name.removesuffix(".git")

    def _hide(self, text: str) -> str:
        """掩码 token，防止其进入日志。"""
        if self.token and self.token in text:
            text = text.replace(self.token, "***")
        return text

    def _auth_args(self) -> list[str]:
        """返回 git -c http.extraHeader 凭据注入参数（token 不落 remote/log）。"""
        if not self.token:
            return []
        basic = base64.b64encode(f"oauth2:{self.token}".encode()).decode()
        extra = [
            ("http.extraHeader", f"Authorization: Basic {basic}"),
            ("http.extraHeader", f"Private-Token: {self.token}"),
        ]
        return [item for pair in extra for item in ("-c", f"{pair[0]}={pair[1]}")]

    def run_git(
        self,
        git_args: list[str],
        cwd: str | None = None,
        auth: bool = False,
        check: bool = True,
    ) -> dict[str, str]:
        """执行 git 命令并返回 {code, stdout, stderr}。

        git_args 不含开头的 "git"。auth=True 时为网络操作注入凭据。
        """
        cmd: list[str] = ["git", *([*self._auth_args()] if auth else []), *git_args]
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                f"git 命令执行超时: {git_args[0] if git_args else ''}",
                extra={"action": "git_repo.run", "command": git_args[0] if git_args else ""},
            )
            raise AppException(500, detail="git 命令执行超时") from None
        except FileNotFoundError:
            logger.error("git 未安装", extra={"action": "git_repo.run"})
            raise AppException(500, detail="git 未安装，请检查后端镜像") from None

        stdout = self._hide(proc.stdout or "")
        stderr = self._hide(proc.stderr or "")
        logger.info(
            "git 命令执行完成",
            extra={
                "action": "git_repo.run",
                "command": git_args[0] if git_args else "",
                "returncode": proc.returncode,
                "stdout": self._truncate(stdout),
                "stderr": self._truncate(stderr),
            },
        )
        if check and proc.returncode != 0:
            detail = f"git 命令执行失败: {self._strip(stderr) or self._strip(stdout)}"
            raise AppException(500, detail=detail)
        return {"code": proc.returncode, "stdout": stdout, "stderr": stderr}

    @staticmethod
    def _truncate(text: str, limit: int = 500) -> str:
        """按用户偏好截断长日志。"""
        return text if len(text) <= limit else text[:limit] + "..."

    @staticmethod
    def _strip(text: str) -> str:
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())[-500:]

    def is_cloned(self) -> bool:
        """仓库目录是否已初始化。"""
        return (self.repo_dir / ".git").exists()

    def _require_cloned(self) -> None:
        if not self.is_cloned():
            raise ConflictError(detail="仓库尚未克隆，请先调用 clone 接口")

    def _current_branch(self) -> str:
        run = self.run_git(["branch", "--show-current"], cwd=str(self.repo_dir))
        return run["stdout"].strip()

    # ---------- 核心操作 ----------
    def ensure_clone(self) -> dict[str, Any]:
        """克隆仓库并初始化 sparse-checkout（未克隆时）。"""
        if self.is_cloned():
            return {"already_cloned": True}
        if not self.token:
            raise AppException(500, detail="未配置 GIT_PRIVATE_TOKEN，无法克隆私有仓库")
        with self._lock:
            base_dir = Path(settings.git_repo_base_dir_abs)
            base_dir.mkdir(parents=True, exist_ok=True)
            # 稀疏 + 部分克隆：仅拉取 conf 子目录，避免下载整个项目
            self.run_git(
                ["clone", "--sparse", "--filter=blob:none", self.repo_url, str(self.repo_dir)],
                cwd=str(base_dir),
                auth=True,
            )
            # 用无凭据 URL 重写 remote，避免 token 泄漏进 git remote -v
            self.run_git(["remote", "set-url", "origin", self.repo_url], cwd=str(self.repo_dir))
            self.init_sparse()
        return {"already_cloned": False}

    def init_sparse(self) -> dict[str, Any]:
        """按配置初始化稀疏检出（cone 模式）。"""
        self._require_cloned()
        self.run_git(["sparse-checkout", "init", "--cone"], cwd=str(self.repo_dir))
        self.set_sparse(self.sparse_paths)
        return {"paths": self.sparse_paths}

    def get_sparse(self) -> list[str]:
        """读取当前稀疏检出路径（含 core.sparseCheckoutCone 及匹配到的路径）。"""
        self._require_cloned()
        run = self.run_git(
            ["sparse-checkout", "list"], cwd=str(self.repo_dir), check=False
        )
        return [line for line in run["stdout"].splitlines() if line.strip()]

    def set_sparse(self, paths: list[str]) -> dict[str, Any]:
        """更新稀疏检出路径。"""
        self._require_cloned()
        clean = [p.strip() for p in paths if p and p.strip()]
        if not clean:
            raise AppException(422, detail="paths 不能为空")
        self.run_git(["sparse-checkout", "set", *clean], cwd=str(self.repo_dir))
        self.sparse_paths = clean
        return {"paths": clean}

    def fetch(self) -> dict[str, Any]:
        """从远端更新引用（不改动工作区）。"""
        self._require_cloned()
        with self._lock:
            run = self.run_git(["fetch", "origin"], cwd=str(self.repo_dir), auth=True, check=False)
            if run["code"] != 0:
                raise AppException(500, detail=f"git fetch 失败: {self._strip(run['stderr']) or self._strip(run['stdout'])}")
            return {"output": run["stdout"].strip() or run["stderr"].strip()}

    def pull(self) -> dict[str, Any]:
        """拉取远端最新。"""
        self._require_cloned()
        with self._lock:
            run = self.run_git(["pull", "origin"], cwd=str(self.repo_dir), auth=True)
        return {"output": run["stdout"].strip() or run["stderr"].strip()}

    def commit(self, message: str, paths: list[str] | None = None) -> dict[str, Any]:
        """提交本地改动（指定 paths 或全部）。"""
        self._require_cloned()
        if not message or not message.strip():
            raise AppException(422, detail="message 不能为空")
        if paths:
            clean = [p for p in paths if p and p.strip() != ""]
            if not clean:
                raise AppException(422, detail="paths 不能为空或空字符串")
            self.run_git(["add", "--", *clean], cwd=str(self.repo_dir))
        else:
            self.run_git(["add", "-A"], cwd=str(self.repo_dir))
        run = self.run_git(["commit", "-m", message.strip()], cwd=str(self.repo_dir))
        return {"output": (run["stdout"].strip() or run["stderr"].strip()) or "commit 完成"}

    def push(self) -> dict[str, Any]:
        """推送到远端当前分支。"""
        self._require_cloned()
        with self._lock:
            branch = self._current_branch()
            if not branch:
                raise AppException(422, detail="未处于任何分支（如 detach HEAD），无法 push")
            run = self.run_git(["push", "origin", branch], cwd=str(self.repo_dir), auth=True)
        return {"branch": branch, "output": run["stdout"].strip() or run["stderr"].strip()}

    def list_branches(self) -> list[dict[str, str]]:
        """列出分支与标签，标记当前分支。"""
        self._require_cloned()
        current = self._current_branch()
        run = self.run_git(
            [
                "for-each-ref",
                "--format=%(refname)|%(objectname:short)|%(subject)",
                "refs/heads",
                "refs/tags",
            ],
            cwd=str(self.repo_dir),
        )
        items: list[dict[str, str]] = []
        for line in run["stdout"].splitlines():
            parts = line.split("|", 2)
            if len(parts) < 2:
                continue
            refname, short = parts[0], parts[1]
            subject = parts[2] if len(parts) > 2 else ""
            if refname.startswith("refs/tags/"):
                kind, name = "tag", refname[len("refs/tags/") :]
            elif refname.startswith("refs/heads/"):
                kind, name = "branch", refname[len("refs/heads/") :]
            else:
                continue
            items.append(
                {
                    "name": name,
                    "kind": kind,
                    "hash": short,
                    "subject": subject,
                    "is_current": "1" if name == current else "0",
                }
            )
        return items

    def checkout(self, ref: str) -> dict[str, Any]:
        """切换分支/标签/commit。"""
        self._require_cloned()
        if not ref or not ref.strip():
            raise AppException(422, detail="ref 不能为空")
        run = self.run_git(["checkout", ref.strip()], cwd=str(self.repo_dir))
        return {"ref": ref.strip(), "output": run["stdout"].strip() or run["stderr"].strip()}

    def get_log(self, limit: int = 20) -> list[dict[str, str]]:
        """查看提交历史。"""
        self._require_cloned()
        run = self.run_git(
            [
                "log",
                "-n",
                str(limit),
                "--pretty=format:%H|%an|%ae|%aI|%s",
            ],
            cwd=str(self.repo_dir),
        )
        items: list[dict[str, str]] = []
        for line in run["stdout"].splitlines():
            parts = line.split("|", 4)
            if len(parts) >= 5:
                items.append(
                    {
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    }
                )
        return items

    def get_status(self) -> dict[str, Any]:
        """仓库状态：是否已克隆、当前分支、HEAD、未提交改动。"""
        if not self.is_cloned():
            return {"cloned": False}
        branch = self._current_branch()
        head = self.run_git(["rev-parse", "--short", "HEAD"], cwd=str(self.repo_dir))[
            "stdout"
        ].strip()
        porcelain = self.run_git(["status", "--porcelain"], cwd=str(self.repo_dir))["stdout"]
        dirty = bool(porcelain.strip())
        return {
            "cloned": True,
            "branch": branch,
            "head": head,
            "dirty": dirty,
            "changed_files": porcelain.splitlines(),
        }

    def get_sync_status(self) -> dict[str, Any]:
        """本地与远端的同步状态：fetch 后比较 ahead/behind。

        `local_newer` 以 ahead>0（本地存在远端没有的提交）为权威判断；
        `dirty` 仅作补充展示与拉取安全门槛。
        """
        if not self.is_cloned():
            return {"cloned": False}
        with self._lock:
            self.fetch()
            branch = self._current_branch()
            if not branch:
                return {"cloned": True, "branch": None}
            count = self.run_git(
                ["rev-list", "--left-right", "--count", f"HEAD...origin/{branch}"],
                cwd=str(self.repo_dir),
            )["stdout"]
            # 形如 "3\t2" 或 "3 2"
            tokens = count.replace("\t", " ").split()
            ahead = int(tokens[0]) if tokens else 0
            behind = int(tokens[1]) if len(tokens) > 1 else 0
            porcelain = self.run_git(["status", "--porcelain"], cwd=str(self.repo_dir))["stdout"]
            dirty = bool(porcelain.strip())
        return {
            "cloned": True,
            "branch": branch,
            "ahead": ahead,
            "behind": behind,
            "local_newer": ahead > 0,
            "remote_newer": behind > 0,
            "is_synced": ahead == 0 and behind == 0 and not dirty,
            "dirty": dirty,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    def get_remote(self) -> dict[str, str]:
        """返回脱敏后的远端地址（host/path，不含 token）。"""
        return {"url": self.repo_url}


git_repo_service = GitRepoService()


def get_git_repo_service() -> GitRepoService:
    """获取 GitRepoService 单例。"""
    return git_repo_service
