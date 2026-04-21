import typer
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

cli = typer.Typer()
api = FastAPI(title="Vibe Manager")

STATIC_DIR = Path(__file__).parent.parent / "static"

@cli.callback()
def main():
    """Vibe Manager — project dashboard CLI."""

@cli.command("serve")
def serve(
    port: int = typer.Option(8888, help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
):
    """Start the Vibe Manager web server."""
    if STATIC_DIR.exists():
        api.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    typer.echo(f"Vibe Manager running at http://{host}:{port}")
    uvicorn.run(api, host=host, port=port)

app = cli

if __name__ == "__main__":
    cli()
