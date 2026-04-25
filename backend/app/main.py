"""FastAPI entrypoint re-exporting the MCP-powered application."""

from .main_fast import app

__all__ = ["app"]
