"""
Jenkins REST API 客户端。
使用 httpx 调用 Jenkins API，模式参考 services/k8s.py。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=15, write=5, pool=5)


def _auth(username: str, api_token: str) -> httpx.BasicAuth:
    return httpx.BasicAuth(username, api_token)


def _clean(url: str) -> str:
    return url.rstrip("/")


# ─── 触发构建 ────────────────────────────────────────────────


def trigger_build(
    base_url: str,
    job_name: str,
    username: str,
    api_token: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    触发 Jenkins 构建。
    - 无参数: POST /job/{name}/build
    - 有参数: POST /job/{name}/buildWithParameters
    返回 {"ok": True, "queue_url": "...", "queue_id": int} 或 {"ok": False, "error": "..."}
    """
    base = _clean(base_url)
    auth = _auth(username, api_token)

    if params:
        url = f"{base}/job/{job_name}/buildWithParameters"
    else:
        url = f"{base}/job/{job_name}/build"

    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False, auth=auth) as client:
            resp = client.post(url, params=params or {})
            if resp.status_code in (200, 201):
                queue_url = resp.headers.get("Location", "")
                queue_id = _extract_queue_id(queue_url)
                return {"ok": True, "queue_url": queue_url, "queue_id": queue_id}
            elif resp.status_code == 400:
                return {"ok": False, "error": "参数错误或 Job 不存在"}
            elif resp.status_code == 401:
                return {"ok": False, "error": "Jenkins 认证失败（用户名或 API Token 错误）"}
            elif resp.status_code == 403:
                return {"ok": False, "error": "Jenkins 权限不足"}
            elif resp.status_code == 404:
                return {"ok": False, "error": f"Job '{job_name}' 不存在"}
            else:
                return {"ok": False, "error": f"HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接 Jenkins 超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接 Jenkins: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _extract_queue_id(queue_url: str) -> int | None:
    """从 Location header 提取 queue item ID。"""
    if not queue_url:
        return None
    # URL 格式: /queue/item/123/
    parts = queue_url.strip("/").split("/")
    try:
        idx = parts.index("item")
        return int(parts[idx + 1])
    except (ValueError, IndexError):
        return None


# ─── 查询队列项 ──────────────────────────────────────────────


def get_queue_item(
    base_url: str,
    queue_id: int,
    username: str,
    api_token: str,
) -> dict[str, Any]:
    """
    查询队列项，获取实际分配的构建号。
    返回 {"ok": True, "build_number": int, "cancelled": bool} 或错误。
    """
    base = _clean(base_url)
    url = f"{base}/queue/item/{queue_id}/api/json"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False, auth=_auth(username, api_token)) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            cancelled = data.get("cancelled", False)
            build = data.get("executable", {})
            build_number = build.get("number") if build else None
            return {"ok": True, "build_number": build_number, "cancelled": cancelled}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接 Jenkins 超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接 Jenkins: {e}"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": "队列项不存在（可能已过期）"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 查询构建信息 ────────────────────────────────────────────


def get_build_info(
    base_url: str,
    job_name: str,
    build_number: int,
    username: str,
    api_token: str,
) -> dict[str, Any]:
    """
    GET /job/{name}/{number}/api/json
    返回 {"ok": True, "result": "SUCCESS/FAILURE/ABORTED", "building": bool,
           "duration": int, "url": str, "timestamp": int} 或错误。
    """
    base = _clean(base_url)
    url = f"{base}/job/{job_name}/{build_number}/api/json"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False, auth=_auth(username, api_token)) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "ok": True,
                "result": data.get("result"),
                "building": data.get("building", False),
                "duration": data.get("duration", 0),
                "url": data.get("url", ""),
                "timestamp": data.get("timestamp", 0),
            }
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接 Jenkins 超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接 Jenkins: {e}"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": f"构建 #{build_number} 不存在"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 获取构建日志 ────────────────────────────────────────────


def get_build_log(
    base_url: str,
    job_name: str,
    build_number: int,
    username: str,
    api_token: str,
    start: int = 0,
) -> dict[str, Any]:
    """
    GET /job/{name}/{number}/logText/progressiveText?start={start}
    增量拉取构建日志，用于实时查看。
    返回 {"ok": True, "text": str, "offset": int, "more": bool} 或错误。
    """
    base = _clean(base_url)
    url = f"{base}/job/{job_name}/{build_number}/logText/progressiveText"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False, auth=_auth(username, api_token)) as client:
            resp = client.get(url, params={"start": start})
            resp.raise_for_status()
            text = resp.text
            # Jenkins 返回 X-Text-Size header 表示下次请求的 offset
            new_offset = int(resp.headers.get("X-Text-Size", start + len(text)))
            more = resp.headers.get("X-More-Data", "false").lower() == "true"
            return {"ok": True, "text": text, "offset": new_offset, "more": more}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接 Jenkins 超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接 Jenkins: {e}"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": f"构建 #{build_number} 不存在"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 获取下一个构建号 ───────────────────────────────────────


def get_next_build_number(
    base_url: str,
    job_name: str,
    username: str,
    api_token: str,
) -> dict[str, Any]:
    """
    GET /job/{name}/api/json?tree=nextBuildNumber
    返回 {"ok": True, "next_build_number": int} 或错误。
    """
    base = _clean(base_url)
    url = f"{base}/job/{job_name}/api/json"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False, auth=_auth(username, api_token)) as client:
            resp = client.get(url, params={"tree": "nextBuildNumber"})
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "next_build_number": data.get("nextBuildNumber", 0)}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接 Jenkins 超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接 Jenkins: {e}"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": f"Job '{job_name}' 不存在"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 测试连接 ────────────────────────────────────────────────


def test_connection(base_url: str, username: str, api_token: str) -> dict[str, Any]:
    """测试 Jenkins 连通性。"""
    base = _clean(base_url)
    url = f"{base}/api/json"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False, auth=_auth(username, api_token)) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "ok": True,
                "version": data.get("version", ""),
                "node_name": data.get("nodeName", ""),
                "num_jobs": len(data.get("jobs", [])),
            }
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接 Jenkins 超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接 Jenkins: {e}"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {"ok": False, "error": "认证失败（用户名或 API Token 错误）"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
