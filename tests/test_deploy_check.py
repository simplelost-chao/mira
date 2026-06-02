from vibe.deploy_check import (
    find_port_conflicts, find_missing_dependencies, reverse_impact
)

BASE = [
    {"name": "Ollama", "port": 11434},
    {"name": "PostgreSQL", "port": 5432},
]
DEPLOYMENTS = [
    {"project": "a", "ports": [8080], "depends_on": ["Ollama"]},
    {"project": "b", "ports": [8080, 5432], "depends_on": ["Ollama", "Ghost"]},
    {"project": "c", "ports": [9000], "depends_on": []},
]


def test_port_conflicts_detects_duplicate_across_projects():
    conflicts = find_port_conflicts(DEPLOYMENTS, BASE)
    by_port = {c["port"]: sorted(c["owners"]) for c in conflicts}
    assert by_port[8080] == ["a", "b"]
    assert by_port[5432] == ["PostgreSQL", "b"]
    assert 9000 not in by_port


def test_missing_dependencies():
    missing = find_missing_dependencies(DEPLOYMENTS, BASE)
    by_proj = {m["project"]: m["missing"] for m in missing}
    assert by_proj == {"b": ["Ghost"]}


def test_reverse_impact():
    impact = reverse_impact(DEPLOYMENTS, BASE)
    assert sorted(impact["Ollama"]) == ["a", "b"]
    assert impact["PostgreSQL"] == []


def test_empty_inputs_safe():
    assert find_port_conflicts([], []) == []
    assert find_missing_dependencies([], []) == []
    assert reverse_impact([], []) == {}


def test_port_no_self_conflict_on_intra_project_duplicate():
    deployments = [{"project": "a", "ports": [8080, 8080], "depends_on": []}]
    assert find_port_conflicts(deployments, []) == []
