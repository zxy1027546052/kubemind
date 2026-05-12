import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisSession

SEED_RESULT_1 = {
    "root_causes": ["MySQL 连接池配置上限过低 (max_connections=50)", "应用侧连接未及时释放导致连接泄漏"],
    "steps": [
        "1. 登录 MySQL 执行 SHOW PROCESSLIST 查看当前连接数和状态",
        "2. 检查应用连接池配置 (max_connections, idle_timeout)",
        "3. 分析慢查询日志，定位是否有长时间运行的阻塞查询",
        "4. 根据业务量调整 max_connections 到合理值 (建议 200-500)",
        "5. 配置连接池空闲超时和最大生命周期，防止连接泄漏",
    ],
    "impact": "数据库连接池耗尽导致 35% 的 API 请求返回 connect timeout，影响 3 个核心业务模块",
    "runbook_refs": [
        {"id": 1, "title": "MySQL 连接池耗尽 / 慢查询排查处理手册", "score": 0.92},
        {"id": 4, "title": "TCP TIME_WAIT 堆积处理手册", "score": 0.35},
    ],
}

SEED_RESULT_2 = {
    "root_causes": ["磁盘 IO 争用 — 后台定时任务与业务高峰重叠", "日志轮转策略不当导致瞬时大量写入"],
    "steps": [
        "1. 执行 iostat -x 1 观察磁盘 util% 和 await 指标",
        "2. 使用 iotop / pidstat -d 定位高 IO 进程",
        "3. 检查 crontab 中的定时任务调度时间",
        "4. 将非紧急批处理任务调整到业务低峰期执行",
        "5. 考虑升级为 SSD 或增加 IOPS 配额",
    ],
    "impact": "API 响应 P99 从 50ms 飙升至 2s，影响约 1.5 小时",
    "runbook_refs": [
        {"id": 2, "title": "磁盘 IO 饱和排查处理手册", "score": 0.88},
    ],
}


def seed_diagnoses(db: Session) -> None:
    if db.query(DiagnosisSession).first():
        return
    now = datetime.now()
    sessions = [
        DiagnosisSession(
            query_text="生产环境 MySQL 突然大量连接超时，API 返回 connect timeout 错误",
            matched_items=json.dumps([
                {"id": 1, "source_type": "cases", "title": "MySQL 连接池耗尽导致 API 响应超时", "score": 0.92},
                {"id": 1, "source_type": "runbooks", "title": "MySQL 连接池耗尽 / 慢查询排查处理手册", "score": 0.88},
                {"id": 4, "source_type": "runbooks", "title": "TCP TIME_WAIT 堆积处理手册", "score": 0.35},
            ], ensure_ascii=False),
            llm_response=json.dumps(SEED_RESULT_1, ensure_ascii=False),
            status="completed",
            created_at=now,
            updated_at=now,
        ),
        DiagnosisSession(
            query_text="API 响应突然变得非常慢，P99 从 50ms 变成了 2 秒以上",
            matched_items=json.dumps([
                {"id": 2, "source_type": "cases", "title": "磁盘 IO 饱和导致 API 响应延迟飙升", "score": 0.85},
                {"id": 2, "source_type": "runbooks", "title": "磁盘 IO 饱和排查处理手册", "score": 0.82},
            ], ensure_ascii=False),
            llm_response=json.dumps(SEED_RESULT_2, ensure_ascii=False),
            status="completed",
            created_at=now,
            updated_at=now,
        ),
    ]
    for s in sessions:
        db.add(s)
    db.commit()
