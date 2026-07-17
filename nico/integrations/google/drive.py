from __future__ import annotations

import base64
from typing import Any

import httpx

from nico.integrations.google.credentials import api_get, get_credentials

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class DriveIntegration:
    """Google Drive Integration via REST API."""

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file

    async def list_files(self, max_results: int = 5, query: str | None = None) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Drive is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "files": []}

        try:
            params: dict[str, Any] = {
                "pageSize": max_results,
                "fields": "nextPageToken, files(id, name, mimeType, size)",
            }
            if query:
                params["q"] = query

            data = await api_get(
                "https://www.googleapis.com/drive/v3/files",
                creds,
                params=params,
            )

            files = []
            for item in data.get("files", []):
                files.append({
                    "id": item.get("id"),
                    "name": item.get("name", "Untitled File"),
                    "mime_type": item.get("mimeType", ""),
                    "size_bytes": int(item.get("size", 0)) if item.get("size") else None,
                })
            return {"status": "ok", "files": files, "source": "Google Drive"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "files": []}

    async def read_file(self, file_id: str) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Drive is not configured.", "content": None}

        try:
            meta = await api_get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                creds,
                params={"fields": "id,name,mimeType,size"},
            )

            mime = meta.get("mimeType", "")
            if mime.startswith("application/vnd.google-apps"):
                content = await api_get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                    creds,
                    params={"mimeType": "text/plain"},
                )
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="replace")
                return {"status": "ok", "metadata": meta, "content": content, "source": "Google Drive"}

            if creds.expired:
                from google.auth.transport.requests import Request
                creds.refresh(Request())

            download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    download_url,
                    headers={"Authorization": f"Bearer {creds.token}"},
                    timeout=15,
                )
                resp.raise_for_status()
                raw = resp.content

            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                text = base64.b64encode(raw).decode("utf-8")

            return {"status": "ok", "metadata": meta, "content": text, "source": "Google Drive"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "content": None}

    async def search_files(self, query: str, max_results: int = 10) -> dict[str, Any]:
        return await self.list_files(max_results=max_results, query=query)

    async def get_file_info(self, file_id: str) -> dict[str, Any]:
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Drive is not configured.", "file": None}

        try:
            data = await api_get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                creds,
                params={
                    "fields": "id,name,mimeType,size,createdTime,modifiedTime,owners,lastModifyingUser,webViewLink,description",
                },
            )

            return {
                "status": "ok",
                "file": {
                    "id": data.get("id"),
                    "name": data.get("name", "Untitled"),
                    "mime_type": data.get("mimeType", ""),
                    "size_bytes": int(data.get("size", 0)) if data.get("size") else None,
                    "created": data.get("createdTime", ""),
                    "modified": data.get("modifiedTime", ""),
                    "owners": [o.get("displayName", "") for o in data.get("owners", [])],
                    "web_link": data.get("webViewLink", ""),
                    "description": data.get("description", ""),
                },
                "source": "Google Drive",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc), "file": None}
