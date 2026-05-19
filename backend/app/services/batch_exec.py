"""
批量执行服务
通过 SSH 在多台主机上并发执行命令，实时返回输出。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import paramiko

logger = logging.getLogger(__name__)


def _ssh_exec(host: str, port: int, username: str, password: str,
              command: str, timeout: int = 30) -> dict[str, Any]:
    """在单台主机上执行命令，返回结果。"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=host, port=port, username=username,
                    password=password, timeout=10, allow_agent=False, look_for_keys=False)
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        # 读取输出
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        return {"stdout": out, "stderr": err, "exit_code": exit_code, "ok": True}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "ok": False}
    finally:
        ssh.close()


async def execute_on_hosts(
    hosts: list[dict[str, Any]],
    command: str,
    send_message,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    在多台主机上并发执行命令，通过 send_message 回调实时推送输出。

    hosts: [{"id": int, "name": str, "ip": str, "port": int, "user": str, "pwd": str}]
    send_message: async callable(data: dict) — WebSocket 消息回调
    """
    loop = asyncio.get_event_loop()
    results: dict[str, dict] = {}
    success_count = 0
    fail_count = 0

    async def run_one(host_info: dict):
        nonlocal success_count, fail_count
        name = host_info["name"]
        ip = host_info["ip"]
        host_id = host_info["id"]

        # 通知开始
        await send_message({
            "type": "exec_start",
            "host_id": host_id,
            "host_name": name,
            "host_ip": ip,
        })

        # 在线程池中执行 SSH 命令
        result = await loop.run_in_executor(
            None,
            _ssh_exec,
            ip,
            host_info.get("port", 22),
            host_info.get("user", "root"),
            host_info.get("pwd", ""),
            command,
            timeout,
        )

        results[f"{host_id}"] = result

        if result["ok"] and result["exit_code"] == 0:
            success_count += 1
        else:
            fail_count += 1

        # 推送结果
        await send_message({
            "type": "exec_result",
            "host_id": host_id,
            "host_name": name,
            "host_ip": ip,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
            "ok": result["ok"],
        })

    # 并发执行所有主机
    await asyncio.gather(*[run_one(h) for h in hosts])

    # 通知全部完成
    summary = {
        "type": "exec_done",
        "total": len(hosts),
        "success": success_count,
        "failed": fail_count,
    }
    await send_message(summary)

    return {
        "total": len(hosts),
        "success": success_count,
        "failed": fail_count,
        "results": results,
    }
