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
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"])
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

@cli.callback()
def main():
    """Vibe Manager — project dashboard CLI."""

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
