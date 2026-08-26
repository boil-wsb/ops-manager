"""Prometheus 监控主机配置管理服务。

面向 git-repos/prometheus/conf/prometheus/ 下的服务器监控配置文件
（linux_server.json / windows_server.json）做结构化读写，并复用 GitRepoService
完成一键提交（git commit + push）到 GitLab。

设计要点（对抗式评审后重构）：
- 采用操作日志（op-log）模型：增删改只追加 op，不直接改持久文件；
  commit 时先生成最新 base（clone → pull），再在 base 之上回放 op，统一写盘。
  避免"先写盘后 pull 导致远端内容被覆盖"(C-1)。
- 所有操作持互斥锁，避免跨请求并发对共享单例的读改写竞态(C-2)。
- 用稳定主键 address(ip:port) 定位增删改目标，避免索引漂移误删误改(I-1)。
- 写盘统一 newline='\\n'，避免换行/缩进差异造成 git diff 噪音。
"""

import json
import threading
from pathlib import Path
from typing import Any

from app.core.exceptions import AppException, ConflictError
from app.core.logging import get_logger
from app.services.git_repo.git_repo_service import GitRepoService, get_git_repo_service

logger = get_logger("monitor_config")

FILES = {
    "linux": "linux_server.json",
    "windows": "windows_server.json",
}

# Linux / Windows 默认标签
DEFAULT_JOB = {"linux": "linux服务器监控", "windows": "windows服务器监控"}


def _entry_addr(entry: dict[str, Any]) -> str:
    """从 entry 提取 ip:port 作为稳定主键。"""
    ip = (entry.get("ip") or "").strip()
    port = (entry.get("port") or "").strip()
    if not ip or not port:
        raise ConflictError(detail="ip 与 port 不能为空")
    return f"{ip}:{port}"


class MonitorConfigService:
    """服务器监控主机配置的结构化管理。"""

    def __init__(self, git_service: GitRepoService | None = None) -> None:
        self.git: GitRepoService = git_service or get_git_repo_service()
        # 互斥锁：串行化所有增删改与 commit，保护共享单例状态
        self._lock = threading.RLock()
        # 操作日志：每条为 {type, file, addr, entry}
        self._ops: list[dict[str, Any]] = []

    # ---------- 路径 ----------
    @property
    def conf_dir(self) -> Path:
        return self.git.repo_dir / "conf" / "prometheus"

    def _file_path(self, file: str) -> Path:
        if file not in FILES:
            raise ConflictError(detail=f"未知配置文件类型: {file}，仅支持 {list(FILES)}")
        return self.conf_dir / FILES[file]

    def _get_file(self, entry: dict[str, Any]) -> str:
        file = (entry.get("file") or "").strip().lower()
        if file not in FILES:
            raise ConflictError(detail=f"file 必须为 {list(FILES)} 之一")
        return file

    def _load_file(self, file: str) -> list[dict[str, Any]]:
        """读取文件原始数组；文件不存在返回空。"""
        path = self._file_path(file)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"读取配置文件失败: {file}: {e}", extra={"action": "monitor_config"})
            raise AppException(500, detail=f"读取配置文件失败: {FILES[file]}") from e

    # ---------- 视图 ----------
    def _apply_ops(self, base: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
        """在 base 之上回放操作日志，得到目标数组（内存中，不写盘）。"""
        for op in self._ops:
            file = op["file"]
            arr = base.setdefault(file, [])
            if op["type"] == "add":
                arr.append(self._build_item(op["entry"]))
            elif op["type"] == "delete":
                target = self._find_by_addr(arr, op["addr"])
                if target is not None:
                    arr.pop(target)
            elif op["type"] == "update":
                target = self._find_by_addr(arr, op["addr"])
                if target is not None:
                    arr[target] = self._build_item(op["entry"])
                else:
                    arr.append(self._build_item(op["entry"]))
        return base

    @staticmethod
    def _find_by_addr(arr: list[dict[str, Any]], addr: str) -> int | None:
        for idx, item in enumerate(arr):
            targets = item.get("targets") or []
            target_addr = targets[0] if targets else ""
            if target_addr == addr:
                return idx
        return None

    @staticmethod
    def _to_host_item(file: str, filename: str, idx: int, item: dict[str, Any]) -> dict[str, Any]:
        labels = item.get("labels", {}) or {}
        targets = item.get("targets", [])
        addr = targets[0] if targets else ""
        ip, _, port = addr.partition(":")
        return {
            "file": file,
            "filename": filename,
            "index": idx,
            "ip": ip,
            "port": port,
            "env": labels.get("env", ""),
            "job": labels.get("job", ""),
            "instance": labels.get("instance", ""),
            "raw": item,
        }

    def read_hosts(self) -> list[dict[str, Any]]:
        """合并返回 linux+windows 主机列表（含未提交的暂存操作视图）。"""
        with self._lock:
            base: dict[str, list[dict[str, Any]]] = {f: self._load_file(f) for f in FILES}
            view = self._apply_ops(base)
            hosts: list[dict[str, Any]] = []
            for file, arr in view.items():
                filename = FILES.get(file, file)
                for idx, item in enumerate(arr):
                    hosts.append(self._to_host_item(file, filename, idx, item))
            return hosts

    def pending_summary(self) -> list[dict[str, Any]]:
        """返回当前暂存（未提交）的操作摘要，供前端刷新/多标签页恢复提交状态。"""
        label = {"add": "新增", "update": "更新", "delete": "删除"}
        with self._lock:
            return [
                {
                    "type": label.get(op["type"], op["type"]),
                    "file": op["file"],
                    "addr": op["addr"],
                }
                for op in self._ops
            ]

    # ---------- 增删改（只追加 op）----------
    def add_host(self, entry: dict[str, Any]) -> dict[str, Any]:
        file = self._get_file(entry)
        self._validate_entry(entry)
        addr = _entry_addr(entry)
        with self._lock:
            # 防重复：同 file 同 address 已存在（含已暂存）则拒绝
            self._ensure_not_exists(file, addr)
            self._ops.append({"type": "add", "file": file, "addr": addr, "entry": dict(entry)})
        return {
            "file": file,
            "addr": addr,
            "ip": (entry.get("ip") or "").strip(),
            "port": (entry.get("port") or "").strip(),
            "message": f"已暂存新增 {addr}",
        }

    def update_host(self, entry: dict[str, Any]) -> dict[str, Any]:
        file = self._get_file(entry)
        self._validate_entry(entry)
        addr = self._resolve_addr(file, entry)  # 用 index 定位旧条目，取其稳定 addr
        with self._lock:
            self._ops.append({"type": "update", "file": file, "addr": addr, "entry": dict(entry)})
        return {"file": file, "addr": addr, "message": f"已暂存更新 {addr}"}

    def _resolve_addr(self, file: str, entry: dict[str, Any]) -> str:
        """用 index 在当前视图定位目标主机的稳定地址。

        更新必须基于「index 对应的现有条目」，而不能用 entry 里可能变化后的
        新 ip:port 去定位（否则改 IP 时会错误找不到旧条目而误 append）。"""
        with self._lock:
            base: dict[str, list[dict[str, Any]]] = {f: self._load_file(f) for f in FILES}
            view = self._apply_ops(base)
            idx = self._get_index(entry)
            arr = view.get(file, [])
            if idx < 0 or idx >= len(arr):
                raise ConflictError(detail=f"主机序号 {idx} 不存在（{file}）")
            targets = arr[idx].get("targets") or []
            if not targets:
                raise ConflictError(detail=f"目标主机无地址（{file} 序号 {idx}）")
            return targets[0]

    def _ensure_not_exists(self, file: str, addr: str) -> None:
        base: dict[str, list[dict[str, Any]]] = {f: self._load_file(f) for f in FILES}
        view = self._apply_ops(base)
        if self._find_by_addr(view.get(file, []), addr) is not None:
            raise ConflictError(detail=f"主机 {addr} 已存在（{file}），请勿重复新增")

    # ---------- 提交 ----------
    def commit(self, message: str) -> dict[str, Any]:
        """一键提交：先生成最新 base（clone→pull），再回放 op 写盘，然后 git commit+push。"""
        with self._lock:
            if not self._ops:
                return {"message": "无可提交变更", "committed": False}

            # 1. 确保已 clone（未 clone 自动 clone+sparse）
            self.git.ensure_clone()

            # 2. pull 合并远端最新（在写盘之前，避免覆盖远端内容）
            self.git.pull()

            # 3. 以 pull 后的最新磁盘内容为 base
            files = sorted({op["file"] for op in self._ops})
            base: dict[str, list[dict[str, Any]]] = {f: self._load_file(f) for f in files}
            view = self._apply_ops(base)

            # 4. 统一写盘（newline='\n'）
            for f, arr in view.items():
                if f in files:
                    self._write_file(f, arr)

            # 5. commit + push
            msg = (message or "").strip() or "sync: 监控配置同步"
            try:
                self.git.commit(message=msg, paths=["conf/prometheus"])
                self.git.push()
            except Exception:
                # 提交失败：保留 op，允许用户修复后重试
                raise
            # 提交成功后清空操作日志
            self._ops.clear()
            return {"message": f"已提交并推送: {msg}", "committed": True, "commit_message": msg}

    def push_pending_commits(self) -> dict[str, Any]:
        """仅推送本地已存在的提交到远端（不涉及 untracked/new changes）。

        用于「本地较新（ahead>0）但无 pending 暂存操作」时重推失败遗留的提交。
        """
        with self._lock:
            self.git.ensure_clone()
            return self.git.push()

    def _write_file(self, file: str, arr: list[dict[str, Any]]) -> None:
        self.conf_dir.mkdir(parents=True, exist_ok=True)
        path = self._file_path(file)
        path.write_text(
            json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        logger.info(
            f"配置落盘: {FILES[file]} ({len(arr)} 条)",
            extra={"action": "monitor_config.write", "file": FILES[file], "count": len(arr)},
        )

    # ---------- 校验与构建 ----------
    def _validate_entry(self, entry: dict[str, Any]) -> None:
        ip = (entry.get("ip") or "").strip()
        port = (entry.get("port") or "").strip()
        if not ip or not port:
            raise ConflictError(detail="ip 与 port 不能为空")
        _validate_ip(ip)
        _validate_port(port)
        # env / instance 必填
        if not (entry.get("env") or "").strip():
            raise ConflictError(detail="env 不能为空")
        if not (entry.get("instance") or "").strip():
            raise ConflictError(detail="instance 不能为空")

    @staticmethod
    def _get_index(entry: dict[str, Any]) -> int:
        try:
            return int(entry.get("index"))
        except (TypeError, ValueError):
            raise ConflictError(detail="index 必须为整数") from None

    @staticmethod
    def _extract(entry: dict[str, Any], key: str) -> str:
        return (entry.get(key) or "").strip() if entry.get(key) is not None else ""

    def _build_item(self, entry: dict[str, Any]) -> dict[str, Any]:
        file = self._get_file(entry)
        ip = self._extract(entry, "ip")
        port = self._extract(entry, "port")
        if not ip or not port:
            raise ConflictError(detail="ip 与 port 不能为空")

        # 字段级合并：raw 作为 base（保留额外 labels 等），显式字段逐键覆盖。
        raw = entry.get("raw")
        raw_item = dict(raw) if isinstance(raw, dict) else {}
        labels = dict(raw_item.get("labels") or {})

        if env := self._extract(entry, "env"):
            labels["env"] = env
        if job := self._extract(entry, "job"):
            labels["job"] = job
        if instance := self._extract(entry, "instance"):
            labels["instance"] = instance

        # 关键标签默认值
        labels.setdefault("job", DEFAULT_JOB[file])
        if file == "linux":
            labels.setdefault("instance", ip)

        # 自定义附加标签（键值对 dict，允许自定义 key）
        extra_labels = entry.get("labels") or {}
        if isinstance(extra_labels, dict):
            for k, v in extra_labels.items():
                if v is None or str(v).strip() == "":
                    continue
                k = str(k).strip()
                # 避免空 key；env/job/instance 显式字段优先，不被自定义标签覆盖
                if k and k not in ("env", "job", "instance"):
                    labels[k] = str(v).strip()

        # 固定字段顺序：targets 在前、labels 在后，与运维落盘的历史格式保持一致，
        # 减少因键序差异造成的不必要 git diff。额外自定义字段追加在末尾。
        item: dict[str, Any] = {"targets": [f"{ip}:{port}"], "labels": labels}
        for k, v in raw_item.items():
            if k not in ("targets", "labels") and k not in item:
                item[k] = v
        return item


def _validate_ip(ip: str) -> None:
    import ipaddress

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise ConflictError(detail=f"IP 格式非法: {ip}") from None


def _validate_port(port: str) -> None:
    if not port.isdigit() or not (0 < int(port) <= 65535):
        raise ConflictError(detail=f"端口非法: {port}")


monitor_config_service = MonitorConfigService()


def get_monitor_config_service() -> MonitorConfigService:
    """获取 MonitorConfigService 单例。"""
    return monitor_config_service
