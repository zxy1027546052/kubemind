from datetime import datetime

from sqlalchemy.orm import Session

from app.models.runbooks import Runbook

SEED_DATA = [
    {"title": "MySQL 慢查询 / 连接异常处置手册",
     "scenario": "数据库响应延迟超过 500ms，或连接数超过阈值 80%，业务出现超时告警。",
     "steps": "1. SHOW FULL PROCESSLIST 定位慢查询和长时间运行的连接\n2. 检查 slow_query_log，分析慢查询模式\n3. 检查连接池配置（max_connections, wait_timeout, idle_timeout）\n4. 若存在锁等待：SHOW ENGINE INNODB STATUS 分析锁链\n5. Kill 长时间阻塞的查询\n6. 必要时紧急扩容读副本或调整连接池上限",
     "risk": "Kill 查询可能导致数据不一致。调整连接池参数可能引发更多连接竞争。",
     "rollback": "回滚连接池参数至变更前配置。恢复被 Kill 的写事务需通过应用层重试机制。",
     "category": "slow_sql", "tags": "mysql,slow_query,connection_pool,lock_wait"},
    {"title": "磁盘 IO 饱和处置手册",
     "scenario": "磁盘 util% 持续 > 90%，iostat 显示 await/svctm 显著升高，数据库或应用响应变慢。",
     "steps": "1. iostat -x 1 确认磁盘 util% 和 await 指标\n2. iotop / pidstat -d 定位高 IO 进程\n3. 判断 IO 来源：数据库读写 / 日志写入 / 备份任务 / 其他批处理\n4. 若为批处理任务：暂停任务或降低并发\n5. 若为数据库：检查是否有全表扫描，优化查询\n6. 紧急措施：迁移热点数据至更高性能的存储",
     "risk": "强制暂停批处理任务可能导致数据延迟。在线迁移数据目录有数据丢失风险。",
     "rollback": "恢复被暂停的批处理任务。若数据迁移中断，从备份恢复至原始存储。",
     "category": "io_saturation", "tags": "disk,io,iostat,performance"},
    {"title": "网络丢包 / 带宽饱和处置手册",
     "scenario": "节点间 ping 丢包率 > 1%，或网卡带宽使用率 > 90%，服务间 RPC 超时增多。",
     "steps": "1. iftop / nload 查看实时网络流量\n2. netstat -s 检查 TCP 重传、错误包计数\n3. 检查交换机/网卡是否工作在全双工模式\n4. 定位高流量进程：ss -tup 查看连接情况\n5. 若为单个 Pod 导致：对该 Pod 实施网络限速\n6. 若为集群整体：评估是否需要扩容网络或启用 QoS",
     "risk": "对 Pod 实施网络限速可能导致该服务响应进一步恶化。",
     "rollback": "移除网络限速策略。若 QoS 策略导致问题，恢复默认策略。",
     "category": "network_issue", "tags": "network,packet_loss,bandwidth,tcp"},
    {"title": "TCP TIME_WAIT 堆积处置手册",
     "scenario": "服务器上 TIME_WAIT 状态连接数超过 10000，新连接建立失败或端口耗尽。",
     "steps": "1. ss -s 或 netstat -an | grep TIME_WAIT | wc -l 统计数量\n2. 确认是作为客户端还是服务端产生 TIME_WAIT\n3. 客户端：调整 net.ipv4.tcp_tw_reuse=1\n4. 服务端：检查是否有短连接循环（应改用长连接/连接池）\n5. 调整 net.ipv4.ip_local_port_range 扩大可用端口范围",
     "risk": "开启 tcp_tw_reuse 在 NAT 环境下可能导致连接混乱。",
     "rollback": "回滚内核参数至原始值。确保回滚后重启相关服务使配置生效。",
     "category": "connection_pool", "tags": "tcp,time_wait,connection_pool,kernel"},
]


def seed_runbooks(db: Session) -> None:
    if db.query(Runbook).first():
        return
    now = datetime.now()
    for data in SEED_DATA:
        db.add(Runbook(**data, created_at=now, updated_at=now))
    db.commit()
