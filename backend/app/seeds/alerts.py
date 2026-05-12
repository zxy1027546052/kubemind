from datetime import datetime

from sqlalchemy.orm import Session

from app.models.alerts import Alert

SEED_DATA = [
    {
        "title": "[Critical] MySQL 连接池耗尽 — API 服务大量超时",
        "description": "生产环境 MySQL 连接数达到上限 50，约 35% API 请求返回 connect timeout。影响订单、用户、支付三个核心模块。",
        "severity": "critical",
        "source": "prometheus",
        "status": "active",
        "assigned_to": "张运维",
        "category": "database",
    },
    {
        "title": "[High] 磁盘 IO 使用率持续 >90%",
        "description": "应用服务器 /dev/sda 磁盘 util 持续在 90% 以上，await 指标异常升高，API P99 延迟从 50ms 升至 2s。",
        "severity": "high",
        "source": "node_exporter",
        "status": "acknowledged",
        "assigned_to": "李SRE",
        "category": "infrastructure",
    },
    {
        "title": "[Medium] 节点内存使用率超过 85%",
        "description": "k8s-worker-3 节点内存使用率达到 87%，接近 OOM 阈值。该节点运行 15 个 Pod，其中 3 个未设置 memory limit。",
        "severity": "medium",
        "source": "node_exporter",
        "status": "active",
        "assigned_to": "",
        "category": "infrastructure",
    },
    {
        "title": "[Low] SSL 证书将在 14 天后过期",
        "description": "api.example.com 的 SSL 证书将于 2026-05-26 过期，需要尽快续签。当前证书由 Let's Encrypt 签发。",
        "severity": "low",
        "source": "cert_exporter",
        "status": "active",
        "assigned_to": "",
        "category": "security",
    },
    {
        "title": "[High] K8s 3 个 Worker 节点 NotReady",
        "description": "calico-node Pod CrashLoopBackOff 导致 3 个 Worker 节点 NotReady，约 30% Pod 处于 Pending 状态。",
        "severity": "high",
        "source": "kubernetes",
        "status": "resolved",
        "assigned_to": "王K8s",
        "category": "kubernetes",
    },
]


def seed_alerts(db: Session) -> None:
    if db.query(Alert).first():
        return
    now = datetime.now()
    for data in SEED_DATA:
        db.add(Alert(**data, created_at=now, updated_at=now))
    db.commit()
