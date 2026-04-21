import typer
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path

cli = typer.Typer()
api = FastAPI(title="Vibe Manager")

STATIC_DIR = Path(__file__).parent.parent / "static"

def get_all_projects() -> list[dict]:
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.aggregator import collect_project
    from vibe.models import ProjectInfo

    cfg = load_global_config()
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    projects = []
    for item in discovered:
        path = Path(item["path"])
        try:
            info = collect_project(path, name=item["name"], vibe_cfg=item["vibe_config"])
            projects.append(info.model_dump())
        except Exception as e:
            fallback = ProjectInfo(
                id=path.name,
                name=item["name"],
                path=str(path),
                status="active",
                error=str(e),
            )
            projects.append(fallback.model_dump())
    return projects

@api.get("/api/projects")
def list_projects():
    return get_all_projects()

@api.get("/api/projects/{project_id}")
def get_project(project_id: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            return p
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id}/refresh")
def refresh_project(project_id: str):
    return get_project(project_id)

@api.post("/api/refresh")
def refresh_all():
    return get_all_projects()

@api.get("/api/projects/{project_id}/design-docs")
def list_design_docs(project_id: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            return p.get("design_docs", [])
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id}/design-docs/{filename}")
def get_design_doc(project_id: str, filename: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            for doc in p.get("design_docs", []):
                if doc["filename"] == filename:
                    return doc
            raise HTTPException(status_code=404, detail="Design doc not found")
    raise HTTPException(status_code=404, detail="Project not found")

@api.post("/api/projects/import")
def import_project(body: dict):
    """Add a project path to extra_projects in vibe.yaml."""
    from vibe.config import add_extra_project
    from vibe.aggregator import collect_project
    proj_path = (body.get("path") or "").strip()
    if not proj_path:
        raise HTTPException(status_code=400, detail="path is required")
    p = Path(proj_path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {p}")
    if not (p / ".git").exists():
        raise HTTPException(status_code=400, detail=f"Not a git repository: {p}")
    add_extra_project(str(p))
    info = collect_project(p, name=p.name, vibe_cfg=None)
    return {"status": "ok", "project": info.model_dump()}


@api.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Hide a project from discovery by adding it to excluded_paths."""
    from vibe.config import exclude_project
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            exclude_project(p["path"])
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Project not found")


@api.post("/api/projects/{project_id}/summarize")
def summarize_project_endpoint(project_id: str, force: bool = False):
    """Generate and write AI summary for a single project."""
    from vibe.summarizer import summarize_project
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            ok, msg = summarize_project(p, force=force)
            if ok:
                # Re-collect to include fresh summary
                from vibe.aggregator import collect_project
                from pathlib import Path as _Path
                refreshed = collect_project(_Path(p["path"]), p["name"], None)
                return {"status": "ok", "project": refreshed.model_dump()}
            raise HTTPException(status_code=500, detail=msg)
    raise HTTPException(status_code=404, detail="Project not found")


@cli.callback()
def main():
    """Vibe Manager — project dashboard CLI."""

@cli.command("summarize")
def summarize_cmd(
    force: bool = typer.Option(False, "--force", help="Re-generate even if summary exists"),
):
    """Generate AI summaries for all discovered projects and write docs/vibe-summary.md."""
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.aggregator import collect_project
    from vibe.summarizer import summarize_project

    cfg = load_global_config()
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    typer.echo(f"Found {len(discovered)} projects. Generating summaries...\n")

    for item in discovered:
        path = Path(item["path"])
        name = item["name"]
        try:
            info = collect_project(path, name=name, vibe_cfg=item["vibe_config"])
            ok, msg = summarize_project(info.model_dump(), force=force)
            icon = "✓" if ok else ("⟳" if "skipped" in msg else "✗")
            typer.echo(f"  {icon}  {name}: {msg}")
        except Exception as e:
            typer.echo(f"  ✗  {name}: error — {e}")

    typer.echo("\nDone.")


@cli.command("serve")
def serve(
    port: int = typer.Option(None, help="Port to listen on (default: from vibe.yaml or 8888)"),
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
):
    """Start the Vibe Manager web server."""
    from vibe.config import load_global_config
    cfg = load_global_config()
    actual_port = port if port is not None else cfg.get("port", 8888)
    if STATIC_DIR.exists():
        api.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    typer.echo(f"Vibe Manager running at http://{host}:{actual_port}")
    uvicorn.run(api, host=host, port=actual_port)

app = cli

if __name__ == "__main__":
    cli()
