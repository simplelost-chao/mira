from vibe.models import (
    GitInfo, PlanTask, PlanFile, PlanInfo,
    ServiceInfo, LocInfo, FsNode, FsInfo,
    Feature, DesignDoc, DeployInfo, ProjectInfo
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
