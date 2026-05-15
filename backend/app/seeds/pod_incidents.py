"""Pod 故障排查 Runbook 数据导入脚本."""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.runbooks import Runbook

POD_INCIDENTS_DATA = [
    {
        "id": 1,
        "title": "Pending 调度失败",
        "root_causes": ["无可用节点", "资源不足", "亲和性不匹配", "存储冲突", "污点无法容忍", "PVC绑定失败"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看 Events 信息",
            "2. 检查节点资源使用情况: kubectl describe node",
            "3. 检查亲和性/反亲和性配置",
            "4. 检查 PVC 绑定状态",
            "5. 检查节点污点和 Pod 容忍度配置"
        ],
        "impact": "Pod 无法调度到任何节点，服务无法启动",
        "runbook_refs": [{"id": 1, "title": "Pod 调度失败排查处理手册", "score": 0.92}]
    },
    {
        "id": 2,
        "title": "镜像拉取失败",
        "root_causes": ["认证失败", "地址解析错误", "磁盘不足", "证书异常", "网络超时", "DockerHub限流"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看 Events 信息",
            "2. 检查镜像地址是否正确",
            "3. 验证镜像仓库认证配置",
            "4. 检查节点网络连通性",
            "5. 检查节点磁盘空间",
            "6. 考虑使用私有镜像仓库或增加限流配额"
        ],
        "impact": "Pod 无法拉取镜像，容器无法启动",
        "runbook_refs": [{"id": 2, "title": "镜像拉取失败排查处理手册", "score": 0.89}]
    },
    {
        "id": 3,
        "title": "Init 容器异常",
        "root_causes": ["脚本执行失败", "依赖未就绪", "资源不足", "配置错误"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看 Init 容器状态",
            "2. 查看 Init 容器日志: kubectl logs <pod-name> -c <init-container-name>",
            "3. 检查 Init 脚本的执行权限",
            "4. 验证依赖服务是否就绪",
            "5. 检查资源配额是否足够"
        ],
        "impact": "Init 容器失败导致主容器无法启动",
        "runbook_refs": [{"id": 3, "title": "Init 容器异常排查处理手册", "score": 0.87}]
    },
    {
        "id": 4,
        "title": "CrashLoopBackOff 循环重启",
        "root_causes": ["无持续进程", "探针失败", "磁盘满", "端口冲突", "业务代码异常"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看状态",
            "2. 查看容器日志: kubectl logs <pod-name> --previous",
            "3. 检查探针配置是否合理",
            "4. 检查节点磁盘空间",
            "5. 检查端口占用情况",
            "6. 分析业务代码异常原因"
        ],
        "impact": "Pod 反复重启，服务不可用或不稳定",
        "runbook_refs": [{"id": 4, "title": "CrashLoopBackOff 循环重启排查处理手册", "score": 0.91}]
    },
    {
        "id": 5,
        "title": "OOMKilled 内存溢出",
        "root_causes": ["容器超 limit", "节点内存不足"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看 OOM 事件",
            "2. 查看节点内核日志",
            "3. 检查容器内存使用: kubectl top pod <pod-name>",
            "4. 检查节点内存状态: kubectl top node",
            "5. 调整容器内存 limit 配置或优化应用内存使用"
        ],
        "impact": "容器被内核强制杀死，服务中断",
        "runbook_refs": [{"id": 5, "title": "OOMKilled 内存溢出排查处理手册", "score": 0.93}]
    },
    {
        "id": 6,
        "title": "Terminating 销毁卡住",
        "root_causes": ["finalizers 未清理", "preStop 钩子卡住", "容器无响应"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看状态",
            "2. 检查 finalizers 配置",
            "3. 分析 preStop 钩子脚本",
            "4. 检查容器是否正常响应",
            "5. 必要时强制删除: kubectl delete pod <pod-name> --force --grace-period=0"
        ],
        "impact": "Pod 无法正常销毁，占用资源，影响新 Pod 调度",
        "runbook_refs": [{"id": 6, "title": "Pod 销毁卡住排查处理手册", "score": 0.85}]
    },
    {
        "id": 7,
        "title": "Evicted 节点驱逐",
        "root_causes": ["内存压力", "磁盘压力", "PID压力"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看驱逐原因",
            "2. 检查节点状态: kubectl describe node <node-name>",
            "3. 分析节点内存/磁盘/PID使用情况",
            "4. 释放节点资源或扩容节点",
            "5. 调整 Pod 优先级和 QoS 配置"
        ],
        "impact": "Pod 被节点驱逐，服务短暂中断",
        "runbook_refs": [{"id": 7, "title": "节点驱逐排查处理手册", "score": 0.88}]
    },
    {
        "id": 8,
        "title": "Error 程序异常",
        "root_causes": ["启动文件缺失", "权限不足", "配置丢失", "业务报错"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看状态",
            "2. 查看容器日志: kubectl logs <pod-name>",
            "3. 检查启动命令和参数",
            "4. 验证文件权限配置",
            "5. 检查配置文件是否正确挂载",
            "6. 分析业务代码错误"
        ],
        "impact": "容器启动失败或异常退出，服务不可用",
        "runbook_refs": [{"id": 8, "title": "容器启动异常排查处理手册", "score": 0.90}]
    },
    {
        "id": 9,
        "title": "Completed 任务结束",
        "root_causes": ["Job 正常结束", "Deployment 意外退出"],
        "steps": [
            "1. 执行 kubectl describe pod <pod-name> 查看状态",
            "2. 查看容器日志: kubectl logs <pod-name>",
            "3. 确认退出码是否为 0",
            "4. 判断是否为预期行为",
            "5. 对于 Deployment 需检查是否需要重启"
        ],
        "impact": "任务完成或意外退出，需确认是否正常",
        "runbook_refs": [{"id": 9, "title": "Pod 任务结束排查处理手册", "score": 0.82}]
    }
]


def convert_incident_to_runbook(incident: dict) -> dict:
    """将 incident 数据转换为 Runbook 格式."""
    title = incident["title"] + " 排查处理手册"
    
    root_causes = incident["root_causes"]
    scenario = f"Pod 状态异常: {incident['title']}\n\n可能原因:\n" + "\n".join(f"- {cause}" for cause in root_causes)
    
    steps = "\n".join(incident["steps"])
    
    risk = f"影响: {incident['impact']}"
    
    rollback = "根据具体排查结果，采取相应的恢复措施:\n" + \
               "- 若为配置问题，回滚配置至变更前状态\n" + \
               "- 若为资源问题，释放资源或扩容后重试\n" + \
               "- 若为代码问题，回滚至上一版本部署"
    
    category = "pod_troubleshoot"
    
    tags = "kubernetes,pod," + incident["title"].lower().replace(" ", "_")
    
    return {
        "title": title,
        "scenario": scenario,
        "steps": steps,
        "risk": risk,
        "rollback": rollback,
        "category": category,
        "tags": tags
    }


def seed_pod_incidents(db: Session) -> None:
    """导入 Pod 故障排查 Runbook 数据."""
    now = datetime.now()
    
    for incident in POD_INCIDENTS_DATA:
        runbook_data = convert_incident_to_runbook(incident)
        
        existing = db.query(Runbook).filter(Runbook.title == runbook_data["title"]).first()
        if existing:
            print(f"Runbook '{runbook_data['title']}' 已存在，跳过")
            continue
        
        db.add(Runbook(**runbook_data, created_at=now, updated_at=now))
        print(f"已添加 Runbook: {runbook_data['title']}")
    
    db.commit()
    print(f"\n完成! 共处理 {len(POD_INCIDENTS_DATA)} 条 Pod 故障排查 Runbook")


def main():
    db = SessionLocal()
    try:
        seed_pod_incidents(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
