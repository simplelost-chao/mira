from typing import Optional
from pydantic import BaseModel


class GitInfo(BaseModel):
    branch: str
    commit_hash: str
    dirty_files: list[str]
    monthly_commits: int
    recent_commits: list[str]  # list of "hash msg" strings
    github_url: Optional[str] = None  # e.g. "https://github.com/user/repo"
    commit_heatmap: list[int] = []    # 84 daily commit counts (day 0 = 83 days ago)


class ClaudeActivity(BaseModel):
    last_session: Optional[str] = None   # ISO datetime
    session_count_7d: int = 0
    session_count_30d: int = 0
    todos: list[dict] = []
    todo_summary: dict = {}              # {completed, in_progress, pending}
    # token usage (summed across all matching sessions)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    estimated_cost_usd: float = 0.0     # rough estimate based on Sonnet 4.x pricing
    active_hours: float = 0.0           # sum of inter-message gaps < 30min
    session_spark_15d: list[float] = []  # per-day active hours, last 15 days (12h = full)


class CodexActivity(BaseModel):
    last_session: Optional[str] = None
    session_count_7d: int = 0
    session_count_30d: int = 0
    active_hours: float = 0.0
    session_spark_15d: list[float] = []
    total_tasks: int = 0
    avg_task_duration_sec: float = 0.0


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
    public_domain: Optional[str] = None  # e.g. "vibe.zhuchao.life"
    public_ip: Optional[str] = None      # resolved IP of public_domain
    domain_ok: Optional[bool] = None     # None = no domain configured


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
    llm_apis: list[str] = []
    claude_activity: Optional[ClaudeActivity] = None
    codex_activity: Optional[CodexActivity] = None
    error: Optional[str] = None
