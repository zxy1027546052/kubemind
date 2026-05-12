from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cases import Case

SEED_DATA = [
    {"title": "MySQL 连接池耗尽导致服务不可用",
     "symptom": "业务服务大量报错 connect timeout，数据库连接数飙升至上限 2000。",
     "root_cause": "新上线的微服务未配置连接池上限，突发流量下创建了大量空闲连接未及时回收。",
     "steps": "1. 紧急熔断问题服务\n2. 调整连接池 max_connections=50, idle_timeout=30s\n3. 重启服务并逐台放开流量",
     "impact": "影响用户登录和订单查询，持续 35 分钟。3 个服务受影响。",
     "conclusion": "制定连接池配置规范，所有新服务上线前必须通过配置审查。添加连接数告警阈值。",
     "category": "connection_pool", "severity": "critical", "status": "resolved"},
    {"title": "磁盘 IO 争抢导致数据库响应延迟",
     "symptom": "数据库 P99 查询延迟从 50ms 飙升至 2s，业务侧出现大量超时。",
     "root_cause": "同一物理机上另一个实例的日志清理 cron 任务产生大量顺序写，占满磁盘带宽。",
     "steps": "1. iostat 确认磁盘 util 100%\n2. 定位高 IO 进程，确认是批处理任务\n3. 暂停批处理，延迟恢复\n4. 将数据库数据目录迁移至独立 SSD",
     "impact": "数据库响应变慢约 1.5 小时，影响所有读写操作。",
     "conclusion": "数据库实例应采用独占存储。批处理类任务需设置 IO 限速。",
     "category": "io_saturation", "severity": "high", "status": "resolved"},
    {"title": "K8s 节点 NotReady — CNI 插件异常",
     "symptom": "3 个 Worker 节点状态变为 NotReady，调度到这些节点的 Pod 全部 Pending。",
     "root_cause": "Calico node 的 etcd 连接超时，calico-node Pod CrashLoopBackOff，导致节点网络不可用。",
     "steps": "1. kubectl describe node 确认 Condition Unknown\n2. 检查 calico-node Pod 日志发现 etcd 连接拒绝\n3. 重启 etcd 集群，等待 Leader 选举完成\n4. 重建 calico-node Pod",
     "impact": "约 30% 的在线服务受影响，持续 20 分钟。",
     "conclusion": "etcd 集群需配置自动故障转移。Calico 应使用 Kubernetes datastore 减少对 etcd 的直接依赖。",
     "category": "network_issue", "severity": "critical", "status": "resolved"},
]


def seed_cases(db: Session) -> None:
    if db.query(Case).first():
        return
    now = datetime.now()
    for data in SEED_DATA:
        db.add(Case(**data, created_at=now, updated_at=now))
    db.commit()
