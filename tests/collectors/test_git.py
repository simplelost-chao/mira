# tests/collectors/test_git.py
import subprocess
import pytest
from pathlib import Path
from vibe.collectors.git import collect_git

@pytest.fixture
def git_repo(tmp_path):
    """Create a minimal git repo with one commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path

def test_collect_git_branch(git_repo):
    info = collect_git(git_repo)
    assert info.branch in ("main", "master")

def test_collect_git_commit_hash(git_repo):
    info = collect_git(git_repo)
    assert len(info.commit_hash) == 7

def test_collect_git_dirty_files(git_repo):
    (git_repo / "new_file.py").write_text("print('hi')")
    info = collect_git(git_repo)
    assert any("new_file.py" in f for f in info.dirty_files)

def test_collect_git_not_a_repo(tmp_path):
    info = collect_git(tmp_path)
    assert info.branch == "unknown"
    assert info.commit_hash == ""
