import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.workflows import Workflow

SEED_DATA = [
    {
        "title": "数据库故障应急响应流程",
        "description": "当数据库出现连接超时、慢查询堆积或主从延迟时的标准化处理流程。",
        "category": "database",
        "steps": json.dumps([
            {"order": 1, "action": "确认故障范围", "detail": "检查受影响的服务和接口，确认数据库连接状态"},
            {"order": 2, "action": "紧急止血", "detail": "Kill 长时间阻塞查询，扩容连接池上限"},
            {"order": 3, "action": "根因分析", "detail": "分析慢查询日志，定位问题 SQL 和调用来源"},
            {"order": 4, "action": "修复验证", "detail": "优化问题 SQL，灰度验证修复效果"},
            {"order": 5, "action": "复盘总结", "detail": "输出故障复盘报告，更新 Runbook 和监控规则"},
        ], ensure_ascii=False),
        "status": "active",
    },
    {
        "title": "Kubernetes 节点故障处理流程",
        "description": "节点 NotReady、资源耗尽或 Pod 驱逐时的标准操作流程。",
        "category": "kubernetes",
        "steps": json.dumps([
            {"order": 1, "action": "确认节点状态", "detail": "kubectl describe node 查看 Conditions 和 Events"},
            {"order": 2, "action": "Cordon 节点", "detail": "kubectl cordon <node> 停止调度新 Pod"},
            {"order": 3, "action": "Drain 节点", "detail": "kubectl drain <node> --ignore-daemonsets 迁移工作负载"},
            {"order": 4, "action": "诊断修复", "detail": "SSH 登录节点，检查 kubelet/containerd/CNI 状态"},
            {"order": 5, "action": "恢复上线", "detail": "修复后 Uncordon 节点，验证 Pod 调度正常"},
        ], ensure_ascii=False),
        "status": "active",
    },
    {
        "title": "服务发布回滚流程",
        "description": "当新版本部署后出现异常时的快速回滚操作流程。",
        "category": "deployment",
        "steps": json.dumps([
            {"order": 1, "action": "确认异常", "detail": "检查监控面板、错误日志、告警信息确认发布导致的问题"},
            {"order": 2, "action": "决策回滚", "detail": "值班负责人判断是否需要回滚，通知相关团队"},
            {"order": 3, "action": "执行回滚", "detail": "kubectl rollout undo deployment/<name> 或触发 CI 回滚流水线"},
            {"order": 4, "action": "验证恢复", "detail": "观察监控指标和业务指标 5-10 分钟，确认恢复正常"},
            {"order": 5, "action": "问题跟踪", "detail": "创建 Bug Ticket，保留现场日志和监控快照供后续分析"},
        ], ensure_ascii=False),
        "status": "draft",
    },
]


def seed_workflows(db: Session) -> None:
    if db.query(Workflow).first():
        return
    now = datetime.now()
    for data in SEED_DATA:
        db.add(Workflow(**data, created_at=now, updated_at=now))
    db.commit()
