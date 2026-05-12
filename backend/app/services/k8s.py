"""Kubernetes client service — read-only cluster information."""

from pathlib import Path

from app.core.config import settings


class K8sClient:
    def __init__(self) -> None:
        self._connected = False
        self._error: str | None = None
        self._version: str = "unknown"

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def version(self) -> str:
        return self._version

    def connect(self) -> None:
        kubeconfig_path = Path(settings.KUBECONFIG_PATH)
        if not kubeconfig_path.exists():
            self._error = f"Kubeconfig not found: {settings.KUBECONFIG_PATH}"
            return

        try:
            from kubernetes import client, config

            config.load_kube_config(config_file=str(kubeconfig_path.resolve()))
            version_info = client.VersionApi().get_code()
            self._version = version_info.git_version
            self._connected = True
            self._error = None
        except Exception as e:
            self._error = str(e)
            self._connected = False

    def get_nodes(self) -> list[dict]:
        if not self._connected:
            return []
        try:
            from kubernetes import client

            v1 = client.CoreV1Api()
            nodes = v1.list_node().items
            result = []
            for node in nodes:
                conditions = {c.type: c.status for c in (node.status.conditions or [])}
                ready = conditions.get("Ready") == "True"
                result.append({
                    "name": node.metadata.name if node.metadata else "",
                    "status": "Ready" if ready else "NotReady",
                    "version": node.status.node_info.kubelet_version if node.status and node.status.node_info else "",
                    "cpu": node.status.capacity.get("cpu", "") if node.status and node.status.capacity else "",
                    "memory": node.status.capacity.get("memory", "") if node.status and node.status.capacity else "",
                })
            return result
        except Exception:
            return []

    def get_pods(self, namespace: str = "") -> list[dict]:
        if not self._connected:
            return []
        try:
            from kubernetes import client

            v1 = client.CoreV1Api()
            if namespace:
                pods = v1.list_namespaced_pod(namespace).items
            else:
                pods = v1.list_pod_for_all_namespaces().items
            return [
                {
                    "name": p.metadata.name if p.metadata else "",
                    "namespace": p.metadata.namespace if p.metadata else "",
                    "status": p.status.phase if p.status else "",
                    "node": p.spec.node_name or "",
                }
                for p in pods
            ]
        except Exception:
            return []

    def get_overview(self) -> dict:
        nodes = self.get_nodes()
        pods = self.get_pods()

        node_total = len(nodes)
        node_ready = sum(1 for n in nodes if n["status"] == "Ready")
        pod_total = len(pods)
        pod_running = sum(1 for p in pods if p["status"] == "Running")
        pod_pending = sum(1 for p in pods if p["status"] == "Pending")
        pod_failed = sum(1 for p in pods if p["status"] in ("Failed", "CrashLoopBackOff", "Error"))

        return {
            "clusters": [{
                "name": "default",
                "version": self._version,
                "status": "healthy" if self._connected else "disconnected",
                "error": self._error,
            }],
            "nodes": {
                "total": node_total,
                "ready": node_ready,
                "not_ready": node_total - node_ready,
            },
            "pods": {
                "total": pod_total,
                "running": pod_running,
                "pending": pod_pending,
                "failed": pod_failed,
            },
            "resource_usage": {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
            },
            "alert_summary": {
                "critical": 0,
                "high": 0,
                "active_total": 0,
            },
        }


_k8s_client: K8sClient | None = None


def get_k8s_client() -> K8sClient:
    global _k8s_client
    if _k8s_client is None:
        _k8s_client = K8sClient()
        _k8s_client.connect()
    return _k8s_client


def get_cluster_overview(db=None) -> dict:
    """Get cluster overview, enriched with alert counts if db provided."""
    client = get_k8s_client()
    overview = client.get_overview()

    if db:
        from app.models.alerts import Alert
        alerts = db.query(Alert).filter(Alert.status == "active").all()
        overview["alert_summary"] = {
            "critical": sum(1 for a in alerts if a.severity == "critical"),
            "high": sum(1 for a in alerts if a.severity == "high"),
            "active_total": len(alerts),
        }

    return overview
