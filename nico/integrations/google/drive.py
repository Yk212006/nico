from __future__ import annotations

from typing import Any

from nico.integrations.google.credentials import get_credentials

# Scopes required for Google Drive access
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


try:
    from googleapiclient.discovery import build as _build
    _GOOGLE_API = True
except ModuleNotFoundError:
    _GOOGLE_API = False


class DriveIntegration:
    """Google Drive Integration service.

    Supports listing files and retrieving file details. Uses official Google API
    libraries if configured, otherwise indicates the service is unavailable.
    """

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file

    async def list_files(self, max_results: int = 5, query: str | None = None) -> dict[str, Any]:
        """Fetch list of files from Google Drive."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Drive is not configured. Set GOOGLE_CREDENTIALS_FILE to enable.", "files": []}

        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "files": []}

        try:
            import asyncio
            service = _build("drive", "v3", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                results = service.files().list(
                    pageSize=max_results,
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    q=query
                ).execute()
                return results.get("files", [])

            items = await loop.run_in_executor(None, _fetch)
            files = []
            for item in items:
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
        """Download and read the content of a file by its ID."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Drive is not configured.", "content": None}
        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "content": None}
        try:
            import asyncio
            from io import BytesIO
            service = _build("drive", "v3", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                file_meta = service.files().get(fileId=file_id, fields="id,name,mimeType,size").execute()
                mime = file_meta.get("mimeType", "")
                if mime.startswith("application/vnd.google-apps"):
                    content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
                    if isinstance(content, bytes):
                        content = content.decode("utf-8", errors="replace")
                    return {"metadata": file_meta, "content": content}
                request = service.files().get_media(fileId=file_id)
                fh = BytesIO()
                downloader = _MediaDownloader(request, fh)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                content = fh.getvalue()
                try:
                    content = content.decode("utf-8", errors="replace")
                except Exception:
                    content = base64.b64encode(content).decode("utf-8")
                return {"metadata": file_meta, "content": content}

            import base64
            from googleapiclient.http import MediaIoBaseDownload as _MediaDownloader
            result = await loop.run_in_executor(None, _fetch)
            return {"status": "ok", **result, "source": "Google Drive"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "content": None}

    async def search_files(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """Search for files by name or content query."""
        return await self.list_files(max_results=max_results, query=query)

    async def get_file_info(self, file_id: str) -> dict[str, Any]:
        """Get detailed metadata for a file by ID."""
        creds = get_credentials(SCOPES, self._credentials_file, self._token_file)
        if not creds:
            return {"status": "unavailable", "message": "Google Drive is not configured.", "file": None}
        if not _GOOGLE_API:
            return {"status": "unavailable", "message": "Google API client libraries not installed.", "file": None}
        try:
            import asyncio
            service = _build("drive", "v3", credentials=creds)
            loop = asyncio.get_running_loop()

            def _fetch():
                return service.files().get(
                    fileId=file_id,
                    fields="id,name,mimeType,size,createdTime,modifiedTime,owners,lastModifyingUser,webViewLink,description"
                ).execute()

            info = await loop.run_in_executor(None, _fetch)
            return {
                "status": "ok",
                "file": {
                    "id": info.get("id"),
                    "name": info.get("name", "Untitled"),
                    "mime_type": info.get("mimeType", ""),
                    "size_bytes": int(info.get("size", 0)) if info.get("size") else None,
                    "created": info.get("createdTime", ""),
                    "modified": info.get("modifiedTime", ""),
                    "owners": [o.get("displayName", "") for o in info.get("owners", [])],
                    "web_link": info.get("webViewLink", ""),
                    "description": info.get("description", ""),
                },
                "source": "Google Drive",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc), "file": None}
