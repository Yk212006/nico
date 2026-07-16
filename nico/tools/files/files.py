from __future__ import annotations

import os
import pathlib
import shutil
from typing import Any


class FilesTool:
    """Sandboxed file system operations for reading, writing, and listing files.

    All operations are confined to the directory specified by
    ``NICO_FILES_ROOT`` (default: ``~/nico_files``).  Attempts to escape
    via path traversal (``../``) raise a ``PermissionError``.
    """

    name = "files"
    description = "Read, write, list, and manage files within the NICO sandbox directory"
    category = "system"
    timeout_seconds = 10.0
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "list", "delete", "exists"],
                "description": "File operation to perform",
            },
            "path": {
                "type": "string",
                "description": "Relative path inside the sandbox (e.g. 'notes/todo.txt')",
            },
            "content": {
                "type": "string",
                "description": "Content to write (required for 'write' action)",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Must be true to execute delete operations",
            },
        },
        "required": ["action"],
    }

    def __init__(self, files_root: str | None = None) -> None:
        root_env = os.getenv("NICO_FILES_ROOT", "~/nico_files")
        self._root = pathlib.Path(
            files_root or root_env
        ).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative: str) -> pathlib.Path:
        """Resolve *relative* inside the sandbox, rejecting traversal attempts."""
        target = (self._root / relative).resolve()
        if not str(target).startswith(str(self._root)):
            raise PermissionError(
                f"Path '{relative}' escapes the sandbox at '{self._root}'"
            )
        return target

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = str(kwargs.get("action", "list"))
        relative: str = str(kwargs.get("path", ""))

        if action == "list":
            return self._list(relative)
        if action == "exists":
            return self._exists(relative)
        if action == "read":
            return self._read(relative)
        if action == "write":
            content = str(kwargs.get("content", ""))
            return self._write(relative, content)
        if action == "delete":
            confirmed = bool(kwargs.get("confirmed", False))
            if not confirmed:
                return {
                    "status": "requires_confirmation",
                    "path": relative,
                    "message": f"Deleting '{relative}' requires confirmation.",
                }
            return self._delete(relative)
        return {"error": f"Unknown action: {action}"}

    def _list(self, relative: str) -> dict[str, Any]:
        try:
            base = self._safe_path(relative) if relative else self._root
            if not base.is_dir():
                return {"error": f"Not a directory: {relative or '(root)'}"}
            entries = []
            for item in sorted(base.iterdir()):
                entries.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size_bytes": item.stat().st_size if item.is_file() else None,
                    }
                )
            return {"path": relative or "(root)", "entries": entries}
        except PermissionError as exc:
            return {"error": str(exc)}

    def _exists(self, relative: str) -> dict[str, Any]:
        try:
            path = self._safe_path(relative)
            return {"path": relative, "exists": path.exists()}
        except PermissionError as exc:
            return {"error": str(exc)}

    def _read(self, relative: str) -> dict[str, Any]:
        if not relative:
            return {"error": "A file path is required for 'read'"}
        try:
            path = self._safe_path(relative)
            if not path.is_file():
                return {"error": f"File not found: {relative}"}
            content = path.read_text(encoding="utf-8", errors="replace")
            return {"path": relative, "content": content, "size_bytes": len(content)}
        except PermissionError as exc:
            return {"error": str(exc)}

    def _write(self, relative: str, content: str) -> dict[str, Any]:
        if not relative:
            return {"error": "A file path is required for 'write'"}
        try:
            path = self._safe_path(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {
                "path": relative,
                "status": "written",
                "size_bytes": len(content),
            }
        except PermissionError as exc:
            return {"error": str(exc)}

    def _delete(self, relative: str) -> dict[str, Any]:
        if not relative:
            return {"error": "A file path is required for 'delete'"}
        try:
            path = self._safe_path(relative)
            if not path.exists():
                return {"error": f"Not found: {relative}"}
            if path.is_dir():
                shutil.rmtree(path)
                return {"path": relative, "status": "directory_deleted"}
            path.unlink()
            return {"path": relative, "status": "deleted"}
        except PermissionError as exc:
            return {"error": str(exc)}
