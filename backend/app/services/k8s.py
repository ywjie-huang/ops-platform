"""
Kubernetes API 客户端
对接 K8s REST API，自动发现集群资源。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=15, write=5, pool=5)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _clean(url: str) -> str:
    return url.rstrip("/")


# ─── 连接测试 ───────────────────────────────────────────────


def test_connection(endpoint: str, token: str) -> dict[str, Any]:
    """测试 K8s API 连通性，返回集群版本信息。"""
    url = f"{_clean(endpoint)}/version"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.get(url, headers=_headers(token))
            resp.raise_for_status()
            data = resp.json()
            return {
                "ok": True,
                "version": data.get("gitVersion", ""),
                "major": data.get("major", ""),
                "minor": data.get("minor", ""),
                "platform": data.get("platform", ""),
            }
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接超时"}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"无法连接: {e}"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {"ok": False, "error": "认证失败（Token 无效或已过期）"}
        if e.response.status_code == 403:
            return {"ok": False, "error": "权限不足（Token 缺少访问权限）"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 资源拉取 ───────────────────────────────────────────────


def _get_list(endpoint: str, token: str, path: str) -> list[dict]:
    """通用 K8s API list 请求。"""
    url = f"{_clean(endpoint)}{path}"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.get(url, headers=_headers(token))
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
    except Exception as e:
        logger.error("K8s API error [%s]: %s", path, e)
        return []


def get_pod_logs(endpoint: str, token: str, namespace: str, pod_name: str, tail_lines: int = 200) -> dict[str, Any]:
    """获取 Pod 日志。"""
    ns = quote(namespace, safe="")
    pod = quote(pod_name, safe="")
    url = f"{_clean(endpoint)}/api/v1/namespaces/{ns}/pods/{pod}/log"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.get(url, headers=_headers(token), params={"tailLines": max(1, min(tail_lines, 1000)), "allContainers": "true"})
            resp.raise_for_status()
            return {"ok": True, "logs": resp.text}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": "Pod 不存在或日志不可用"}
        if e.response.status_code == 403:
            return {"ok": False, "error": "权限不足，无法读取 Pod 日志"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error("K8s pod logs error [%s/%s]: %s", namespace, pod_name, e)
        return {"ok": False, "error": str(e)}


def get_pod_events(endpoint: str, token: str, namespace: str, pod_name: str) -> list[dict[str, Any]]:
    """获取 Pod 相关事件。"""
    url = f"{_clean(endpoint)}/api/v1/namespaces/{quote(namespace, safe='')}/events"
    selector = f"involvedObject.kind=Pod,involvedObject.name={pod_name},involvedObject.namespace={namespace}"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.get(url, headers=_headers(token), params={"fieldSelector": selector})
            resp.raise_for_status()
            items = resp.json().get("items", [])
    except Exception as e:
        logger.error("K8s pod events error [%s/%s]: %s", namespace, pod_name, e)
        return []

    events = []
    for item in items:
        events.append({
            "type": item.get("type", ""),
            "reason": item.get("reason", ""),
            "message": item.get("message", ""),
            "count": item.get("count", 1),
            "source": (item.get("source") or {}).get("component", ""),
            "first_timestamp": item.get("firstTimestamp", ""),
            "last_timestamp": item.get("lastTimestamp", ""),
        })
    return events


def get_nodes(endpoint: str, token: str) -> list[dict[str, Any]]:
    """获取节点列表。"""
    items = _get_list(endpoint, token, "/api/v1/nodes")
    nodes = []
    for item in items:
        meta = item.get("metadata", {})
        status = item.get("status", {})
        conditions = status.get("conditions", [])
        # 找 Ready 条件
        ready = "Unknown"
        for c in conditions:
            if c.get("type") == "Ready":
                ready = "Ready" if c.get("status") == "True" else "NotReady"
                break

        # 提取资源信息
        capacity = status.get("capacity", {})
        addresses = status.get("addresses", [])
        internal_ip = ""
        for addr in addresses:
            if addr.get("type") == "InternalIP":
                internal_ip = addr.get("address", "")
                break

        nodes.append({
            "name": meta.get("name", ""),
            "status": ready,
            "ip": internal_ip,
            "cpu": capacity.get("cpu", ""),
            "memory": capacity.get("memory", ""),
            "kubelet_version": status.get("nodeInfo", {}).get("kubeletVersion", ""),
            "os_image": status.get("nodeInfo", {}).get("osImage", ""),
            "container_runtime": status.get("nodeInfo", {}).get("containerRuntimeVersion", ""),
            "labels": meta.get("labels", {}),
        })
    return nodes


def get_pods(endpoint: str, token: str) -> list[dict[str, Any]]:
    """获取 Pod 列表。"""
    items = _get_list(endpoint, token, "/api/v1/pods")
    pods = []
    for item in items:
        meta = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})

        # 计算重启次数
        restarts = 0
        for cs in status.get("containerStatuses", []) or []:
            restarts += cs.get("restartCount", 0)

        # 提取镜像
        images = []
        for c in spec.get("containers", []) or []:
            img = c.get("image", "")
            if img:
                images.append(img)

        # 确定状态和异常原因
        phase = status.get("phase", "Unknown")
        container_statuses = status.get("containerStatuses", []) or []
        reason = status.get("reason", "")
        message = status.get("message", "")

        waiting_reasons = []
        terminated_reasons = []
        not_ready_containers = []
        for cs in container_statuses:
            name = cs.get("name", "")
            state = cs.get("state", {}) or {}
            waiting = state.get("waiting") or {}
            terminated = state.get("terminated") or {}
            if waiting:
                waiting_reasons.append(waiting.get("reason", "Waiting"))
                if waiting.get("message"):
                    message = waiting["message"]
            if terminated:
                terminated_reasons.append(terminated.get("reason", "Terminated"))
                if terminated.get("message"):
                    message = terminated["message"]
            if not cs.get("ready", False):
                not_ready_containers.append(name)

        if waiting_reasons:
            reason = waiting_reasons[0]
            phase = reason
        elif terminated_reasons and phase != "Succeeded":
            reason = terminated_reasons[0]
            phase = reason
        elif phase == "Running" and container_statuses and not_ready_containers:
            phase = "NotReady"
            reason = "ContainersNotReady"
            message = f"未就绪容器: {', '.join(not_ready_containers)}"
        elif phase in {"Failed", "Pending", "Unknown"} and not reason:
            reason = phase

        pods.append({
            "name": meta.get("name", ""),
            "namespace": meta.get("namespace", "default"),
            "status": phase,
            "reason": reason,
            "message": message,
            "node": spec.get("nodeName", ""),
            "pod_ip": status.get("podIP", ""),
            "images": images,
            "restarts": restarts,
            "created_at": meta.get("creationTimestamp", ""),
            "labels": meta.get("labels", {}),
        })
    return pods


def get_services(endpoint: str, token: str) -> list[dict[str, Any]]:
    """获取 Service 列表。"""
    items = _get_list(endpoint, token, "/api/v1/services")
    services = []
    for item in items:
        meta = item.get("metadata", {})
        spec = item.get("spec", {})

        # 端口格式化
        ports = []
        for p in spec.get("ports", []) or []:
            port_str = f"{p.get('port', '')}"
            if p.get("nodePort"):
                port_str += f":{p['nodePort']}"
            if p.get("protocol"):
                port_str += f"/{p['protocol']}"
            ports.append(port_str)

        # Selector 格式化
        selector = spec.get("selector", {}) or {}
        selector_str = ",".join(f"{k}={v}" for k, v in selector.items())

        services.append({
            "name": meta.get("name", ""),
            "namespace": meta.get("namespace", "default"),
            "service_type": spec.get("type", "ClusterIP"),
            "cluster_ip": spec.get("clusterIP", ""),
            "ports": ",".join(ports),
            "selector": selector_str,
            "created_at": meta.get("creationTimestamp", ""),
        })
    return services


def get_deployments(endpoint: str, token: str) -> list[dict[str, Any]]:
    """获取 Deployment 列表。"""
    items = _get_list(endpoint, token, "/apis/apps/v1/deployments")
    deployments = []
    for item in items:
        meta = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})

        # 镜像
        images = []
        for c in spec.get("template", {}).get("spec", {}).get("containers", []) or []:
            img = c.get("image", "")
            if img:
                images.append(img)

        replicas = spec.get("replicas", 0)
        ready = status.get("readyReplicas", 0)
        available = status.get("availableReplicas", 0)

        # 状态判断
        if ready == replicas:
            dep_status = "running"
        elif ready > 0:
            dep_status = "updating"
        else:
            dep_status = "stopped"

        deployments.append({
            "name": meta.get("name", ""),
            "namespace": meta.get("namespace", "default"),
            "replicas": replicas,
            "ready_replicas": ready,
            "available_replicas": available,
            "images": images,
            "status": dep_status,
            "created_at": meta.get("creationTimestamp", ""),
            "labels": meta.get("labels", {}),
        })
    return deployments


def delete_pod(endpoint: str, token: str, namespace: str, pod_name: str) -> dict[str, Any]:
    """删除 Pod，让控制器按需重建。"""
    ns = quote(namespace, safe="")
    pod = quote(pod_name, safe="")
    url = f"{_clean(endpoint)}/api/v1/namespaces/{ns}/pods/{pod}"
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.delete(url, headers=_headers(token))
            resp.raise_for_status()
            return {"ok": True}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": "Pod 不存在"}
        if e.response.status_code == 403:
            return {"ok": False, "error": "权限不足，无法删除 Pod"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error("K8s delete pod error [%s/%s]: %s", namespace, pod_name, e)
        return {"ok": False, "error": str(e)}


def restart_deployment(endpoint: str, token: str, namespace: str, deployment_name: str) -> dict[str, Any]:
    """通过 patch pod-template annotation 触发 Deployment 滚动重启。"""
    ns = quote(namespace, safe="")
    dep = quote(deployment_name, safe="")
    url = f"{_clean(endpoint)}/apis/apps/v1/namespaces/{ns}/deployments/{dep}"
    restarted_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": restarted_at,
                    }
                }
            }
        }
    }
    headers = {**_headers(token), "Content-Type": "application/strategic-merge-patch+json"}
    try:
        with httpx.Client(timeout=_TIMEOUT, verify=False) as client:
            resp = client.patch(url, headers=headers, json=payload)
            resp.raise_for_status()
            return {"ok": True, "restarted_at": restarted_at}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": "Deployment 不存在"}
        if e.response.status_code == 403:
            return {"ok": False, "error": "权限不足，无法重启 Deployment"}
        return {"ok": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error("K8s restart deployment error [%s/%s]: %s", namespace, deployment_name, e)
        return {"ok": False, "error": str(e)}


def get_namespaces(endpoint: str, token: str) -> list[str]:
    """获取命名空间列表。"""
    items = _get_list(endpoint, token, "/api/v1/namespaces")
    return [item.get("metadata", {}).get("name", "") for item in items if item.get("metadata", {}).get("name")]


def get_cluster_info(endpoint: str, token: str) -> dict[str, Any]:
    """获取集群概览信息。"""
    version_info = test_connection(endpoint, token)
    if not version_info.get("ok"):
        return {"connected": False, "error": version_info.get("error", "连接失败"), "node_count": 0}

    nodes = get_nodes(endpoint, token)
    pods = get_pods(endpoint, token)
    services = get_services(endpoint, token)
    deployments = get_deployments(endpoint, token)
    namespaces = get_namespaces(endpoint, token)

    # 节点统计
    ready_nodes = sum(1 for n in nodes if n["status"] == "Ready")

    # Pod 状态统计和 Namespace 概览
    pod_status_count: dict[str, int] = {}
    namespace_map = {
        ns: {"name": ns, "pods": 0, "abnormal_pods": 0, "deployments": 0, "services": 0}
        for ns in namespaces
    }
    for p in pods:
        s = p["status"]
        pod_status_count[s] = pod_status_count.get(s, 0) + 1
        ns = p.get("namespace", "default")
        item = namespace_map.setdefault(ns, {"name": ns, "pods": 0, "abnormal_pods": 0, "deployments": 0, "services": 0})
        item["pods"] += 1
        if s not in {"Running", "Succeeded"} or p.get("reason"):
            item["abnormal_pods"] += 1
    for d in deployments:
        ns = d.get("namespace", "default")
        namespace_map.setdefault(ns, {"name": ns, "pods": 0, "abnormal_pods": 0, "deployments": 0, "services": 0})["deployments"] += 1
    for s in services:
        ns = s.get("namespace", "default")
        namespace_map.setdefault(ns, {"name": ns, "pods": 0, "abnormal_pods": 0, "deployments": 0, "services": 0})["services"] += 1

    namespace_overview = sorted(namespace_map.values(), key=lambda x: x["name"])

    return {
        "connected": True,
        "version": version_info.get("version", ""),
        "node_count": len(nodes),
        "ready_nodes": ready_nodes,
        "pod_count": len(pods),
        "service_count": len(services),
        "deployment_count": len(deployments),
        "namespace_count": len(namespaces),
        "namespaces": namespaces,
        "namespace_overview": namespace_overview,
        "pod_status": pod_status_count,
        "nodes": nodes,
        "pods": pods,
        "services": services,
        "deployments": deployments,
    }
