"""部署配置的只读静态检测:端口冲突、依赖缺失、反向影响。

输入均为从 vibe.yaml 读出的原始 dict/list,不做任何副作用,
仅返回供页面展示的结构。不会启停任何服务。
"""
from collections import defaultdict


def find_port_conflicts(deployments, base_services):
    """返回被多于一个使用者声明的端口。

    使用者 = 各 deployment(以 project 名标识)+ 各 base_service(以 name 标识)。
    """
    owners = defaultdict(list)
    for d in deployments or []:
        for port in d.get("ports") or []:
            owners[port].append(d.get("project", "?"))
    for s in base_services or []:
        port = s.get("port")
        if port is not None:
            owners[port].append(s.get("name", "?"))
    conflicts = []
    for port, who in owners.items():
        if len(who) > 1:
            conflicts.append({"port": port, "owners": who})
    return sorted(conflicts, key=lambda c: c["port"])


def find_missing_dependencies(deployments, base_services):
    """返回 depends_on 引用了不存在 base_service 的项目。"""
    known = {s.get("name") for s in base_services or []}
    result = []
    for d in deployments or []:
        missing = [name for name in (d.get("depends_on") or []) if name not in known]
        if missing:
            result.append({"project": d.get("project", "?"), "missing": missing})
    return result


def reverse_impact(deployments, base_services):
    """每个 base_service → 依赖它的项目列表(动它会影响谁)。"""
    impact = {s.get("name"): [] for s in base_services or []}
    for d in deployments or []:
        proj = d.get("project", "?")
        for name in d.get("depends_on") or []:
            if name in impact:
                impact[name].append(proj)
    return impact
