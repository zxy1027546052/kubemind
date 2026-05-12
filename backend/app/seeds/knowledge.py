from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge import Document

SEED_DATA = [
    {"title": "Runbook: MySQL 慢查询 / 连接异常", "type": "Runbook", "category": "slow_sql", "size": "-",
     "content": "排查慢查询日志，检查连接数、锁等待和连接池配置。"},
    {"title": "Runbook: 磁盘 IO 饱和", "type": "Runbook", "category": "io_saturation", "size": "-",
     "content": "使用 iostat 定位高 IO 进程，评估磁盘吞吐瓶颈。"},
    {"title": "Runbook: 网络丢包 / 带宽饱和", "type": "Runbook", "category": "network_issue", "size": "-",
     "content": "检查网卡流量、重传率、错误包计数和节点链路状态。"},
    {"title": "Runbook: TCP TIME_WAIT 堆积 / 短连接耗尽端口", "type": "Runbook", "category": "connection_pool", "size": "-",
     "content": "检查 TIME_WAIT 连接数，调整内核参数 net.ipv4.tcp_tw_reuse，优化连接池配置。"},
]


def seed_documents(db: Session) -> None:
    if db.query(Document).first():
        return
    now = datetime.now()
    for data in SEED_DATA:
        db.add(Document(**data, created_at=now, updated_at=now))
    db.commit()
