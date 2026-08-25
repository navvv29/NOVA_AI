import os
from pathlib import Path

from langchain_core.tools import tool

# Base directory for file operations (restricts to workspace)
WORKSPACE = os.getenv("NOVA_WORKSPACE", ".")


def _safe_path(path: str) -> Path:
    """Resolve path relative to workspace and ensure it stays within it."""
    base = Path(WORKSPACE).resolve()
    target = (base / path).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path '{path}' is outside the workspace.")
    return target


@tool
def read_file(path: str) -> str:
    """Read the contents of a file.

    Use this to read code files, notes, documents, or any text file.
    Provide the path relative to the workspace directory.
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"File not found: {path}"
        if target.stat().st_size > 100_000:
            return f"File too large ({target.stat().st_size} bytes). Read a specific section instead."
        content = target.read_text(encoding="utf-8", errors="replace")
        return content
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating it if it doesn't exist.

    Use this to create new files, save notes, write code, or update existing files.
    Provide the path relative to the workspace directory.
    """
    try:
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_files(directory: str = ".") -> str:
    """List files and directories at the given path.

    Use this to explore the workspace structure, find files, or see what's available.
    Provide the path relative to the workspace directory, or '.' for the root.
    """
    try:
        target = _safe_path(directory)
        if not target.exists():
            return f"Directory not found: {directory}"
        if not target.is_dir():
            return f"Not a directory: {directory}"

        entries = []
        for entry in sorted(target.iterdir()):
            if entry.name.startswith("."):
                continue  # skip hidden files
            prefix = "📁 " if entry.is_dir() else "📄 "
            size = ""
            if entry.is_file():
                size_bytes = entry.stat().st_size
                if size_bytes < 1024:
                    size = f" ({size_bytes}B)"
                elif size_bytes < 1_048_576:
                    size = f" ({size_bytes / 1024:.1f}KB)"
                else:
                    size = f" ({size_bytes / 1_048_576:.1f}MB)"
            entries.append(f"{prefix}{entry.name}{size}")

        if not entries:
            return f"Directory '{directory}' is empty."
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing files: {e}"
