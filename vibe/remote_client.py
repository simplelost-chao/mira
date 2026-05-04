"""远程主机客户端 — 通过 HTTP API 拉取远程 Mira 实例的项目和终端数据。"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

log = logging.getLogger(__name__)

_TIMEOUT = 5.0  # 秒


@dataclass
class RemoteHost:
    alias: str
    url: str  # 如 http://100.64.0.2:8888
    token: str  # sha256(admin_password)
    online: bool = True
    last_projects: list[dict] = field(default_factory=list)
    last_panes: list[dict] = field(default_factory=list)

    # ── 构造 ──────────────────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, entry: dict) -> Optional["RemoteHost"]:
        """从 vibe.yaml remote_hosts 条目构造。alias 不允许包含冒号。"""
        alias = (entry.get("alias") or "").strip()
        url = (entry.get("url") or "").strip().rstrip("/")
        # 优先使用已哈希的 token（安全存储），否则从明文密码计算（向后兼容）
        token = (entry.get("admin_password_hash") or "").strip()
        if not token:
            password = (entry.get("admin_password") or "").strip()
            token = hashlib.sha256(password.encode()).hexdigest() if password else ""
        if not alias or not url:
            log.warning("remote_hosts 条目缺少 alias 或 url，跳过: %s", entry)
            return None
        if ":" in alias:
            log.warning("remote_hosts alias 不允许包含冒号: %s", alias)
            return None
        return cls(alias=alias, url=url, token=token)

    # ── 内部 ──────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.token:
            h["X-Admin-Token"] = self.token
        return h

    async def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict | list]:
        try:
            async with httpx.AsyncClient(trust_env=False, proxy=None) as client:
                resp = await client.get(
                    f"{self.url}{path}",
                    headers=self._headers(),
                    params=params,
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                self.online = True
                return resp.json()
        except Exception as e:
            log.debug("远程主机 %s 请求失败 %s: %s", self.alias, path, e)
            self.online = False
            return None

    async def _post(self, path: str, json_body: Optional[dict] = None,
                    content: Optional[bytes] = None,
                    headers: Optional[dict] = None) -> Optional[dict]:
        try:
            h = {**self._headers(), **(headers or {})}
            async with httpx.AsyncClient(trust_env=False, proxy=None) as client:
                resp = await client.post(
                    f"{self.url}{path}",
                    headers=h,
                    json=json_body if content is None else None,
                    content=content,
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                self.online = True
                return resp.json()
        except Exception as e:
            log.debug("远程主机 %s POST 失败 %s: %s", self.alias, path, e)
            self.online = False
            return None

    # ── 公开 API ──────────────────────────────────────────────────────────────

    async def fetch_projects(self) -> list[dict]:
        """GET /api/projects — 拉取远程项目列表。"""
        data = await self._get("/api/projects")
        if isinstance(data, list):
            self.last_projects = data
            return data
        # 离线时返回 stale 数据
        return self.last_projects

    async def fetch_panes(self) -> list[dict]:
        """GET /api/dev/panes — 拉取远程终端 pane 列表。"""
        data = await self._get("/api/dev/panes")
        if isinstance(data, list):
            self.last_panes = data
            return data
        return self.last_panes

    async def proxy_terminal_output(self, target: str, lines: int = 200) -> Optional[dict]:
        """GET /api/terminals/{target}/output"""
        return await self._get(f"/api/terminals/{target}/output", params={"lines": lines})

    async def proxy_send_keys(self, target: str, keys: str) -> Optional[dict]:
        """POST /api/terminals/{target}/send"""
        return await self._post(f"/api/terminals/{target}/send", json_body={"keys": keys})

    async def proxy_kill_pane(self, target: str) -> Optional[dict]:
        """DELETE /api/dev/panes/{target} — 通过 POST 模拟（httpx 方便起见）。"""
        try:
            async with httpx.AsyncClient(trust_env=False, proxy=None) as client:
                resp = await client.delete(
                    f"{self.url}/api/dev/panes/{target}",
                    headers=self._headers(),
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.debug("远程主机 %s 删除 pane 失败: %s", self.alias, e)
            return None

    async def proxy_upload(self, file_bytes: bytes, filename: str, content_type: str) -> Optional[dict]:
        """POST /api/upload/image — 转发文件上传到远程主机。"""
        try:
            async with httpx.AsyncClient(trust_env=False, proxy=None) as client:
                resp = await client.post(
                    f"{self.url}/api/upload/image",
                    headers=self._headers(),
                    files={"file": (filename, file_bytes, content_type)},
                    timeout=30.0,  # 上传可能较慢
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.debug("远程主机 %s 上传失败: %s", self.alias, e)
            return None

    def status_dict(self) -> dict:
        """返回主机连接状态（用于 /api/hosts）。"""
        return {
            "alias": self.alias,
            "url": self.url,
            "online": self.online,
            "project_count": len(self.last_projects),
            "pane_count": len(self.last_panes),
        }
