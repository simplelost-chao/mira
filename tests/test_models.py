from vibe.models import (
    GitInfo, PlanTask, PlanFile, PlanInfo,
    ServiceInfo, LocInfo, FsNode, FsInfo,
    Feature, DesignDoc, DeployInfo, ProjectInfo, Deployment
)

def test_git_info_defaults():
    g = GitInfo(branch="main", commit_hash="abc123", dirty_files=[], monthly_commits=0, recent_commits=[])
    assert g.branch == "main"
    assert g.dirty_files == []

def test_plan_info_completion():
    tasks = [PlanTask(text="do A", done=True), PlanTask(text="do B", done=False)]
    pf = PlanFile(filename="plan.md", tasks=tasks)
    pi = PlanInfo(files=[pf], total=2, done=1)
    assert pi.total == 2
    assert pi.done == 1

def test_project_info_minimal():
    p = ProjectInfo(id="my-proj", name="My Proj", path="/tmp/my-proj")
    assert p.id == "my-proj"
    assert p.git is None


def test_deployment_minimal():
    d = Deployment(project="simulacra")
    assert d.project == "simulacra"
    assert d.ports == []
    assert d.depends_on == []
    assert d.domain is None
    assert d.deploy is None
    assert d.notes == ""


def test_deployment_full():
    d = Deployment(
        project="awalon-chao",
        ports=[8080, 8081],
        depends_on=["Ollama", "CosyVoice"],
        domain="avalon.zhuchao.life",
        deploy={"type": "ec2", "host": "h", "user": "ec2-user"},
        notes="部署前先确认模型已加载",
    )
    assert d.ports == [8080, 8081]
    assert d.depends_on == ["Ollama", "CosyVoice"]
    assert d.deploy["type"] == "ec2"
    assert d.notes.startswith("部署前")
