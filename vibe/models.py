from typing import Optional
from pydantic import BaseModel


class GitInfo(BaseModel):
    branch: str
    commit_hash: str
    dirty_files: list[str]
    monthly_commits: int
    recent_commits: list[str]  # list of "hash msg" strings


class PlanTask(BaseModel):
    text: str
    done: bool


class PlanFile(BaseModel):
    filename: str
    tasks: list[PlanTask]


class PlanInfo(BaseModel):
    files: list[PlanFile]
    total: int
    done: int


class ServiceInfo(BaseModel):
    port: Optional[int] = None
    process_name: Optional[str] = None
    is_running: bool = False
    url: Optional[str] = None


class LocLanguage(BaseModel):
    name: str
    files: int
    code: int
    comment: int
    blank: int


class LocInfo(BaseModel):
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    file_count: int
    languages: list[LocLanguage]


class FsNode(BaseModel):
    name: str
    is_dir: bool
    size_bytes: Optional[int] = None
    line_count: Optional[int] = None  # for files
    children: Optional[list["FsNode"]] = None


FsNode.model_rebuild()


class FsInfo(BaseModel):
    tree: FsNode
    total_files: int
    large_files: list[str]  # paths with >2000 lines


class Feature(BaseModel):
    text: str
    source: str  # "readme" | "plan" | "code"
    implemented: bool = True


class DesignDoc(BaseModel):
    filename: str
    title: str
    content: str
    mtime: float  # unix timestamp
    possibly_stale: bool  # mtime > 30 days old


class DeployInfo(BaseModel):
    type: str = "none"  # ec2 | ngrok | local | none
    host: Optional[str] = None
    user: Optional[str] = None
    remote_dir: Optional[str] = None
    process: Optional[str] = None
    url: Optional[str] = None
    cmd: Optional[str] = None


class TechStack(BaseModel):
    name: str
    version: Optional[str] = None


class ExternalDep(BaseModel):
    name: str            # "CosyVoice", "PostgreSQL", "Redis" …
    url: Optional[str] = None
    port: Optional[int] = None
    source: str = ""     # which env var / file revealed this


class ProjectInfo(BaseModel):
    id: str
    name: str
    path: str
    status: str = "active"  # active | paused | done
    description: Optional[str] = None
    tech_stack: list[TechStack] = []
    git: Optional[GitInfo] = None
    plans: Optional[PlanInfo] = None
    service: Optional[ServiceInfo] = None
    loc: Optional[LocInfo] = None
    fs: Optional[FsInfo] = None
    features: list[Feature] = []
    design_docs: list[DesignDoc] = []
    deploy: Optional[DeployInfo] = None
    arch_summary: Optional[str] = None
    external_deps: list[ExternalDep] = []
    error: Optional[str] = None
