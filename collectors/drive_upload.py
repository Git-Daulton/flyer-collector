import os
import sys
import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]  # safest for service accounts


def get_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing env var: {name}")
    return val


def ensure_parent_folder_id(folder_id: str) -> str:
    # Basic sanity check: Drive folder IDs are long-ish, usually letters/numbers/_-
    if len(folder_id) < 10:
        raise RuntimeError("GDRIVE_FOLDER_ID looks too short—double-check you copied the folder ID.")
    return folder_id


def upsert_file(service, folder_id: str, local_path: Path) -> str:
    filename = local_path.name
    mime = "application/zip" if filename.lower().endswith(".zip") else "application/json"

    # Look for existing file with same name in target folder
    q = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    resp = service.files().list(q=q, fields="files(id,name)").execute()
    files = resp.get("files", [])

    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=True)

    if files:
        file_id = files[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id
    else:
        file_metadata = {"name": filename, "parents": [folder_id]}
        created = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return created["id"]


def main():
    sa_json = json.loads(get_env("GDRIVE_SERVICE_ACCOUNT_JSON"))
    folder_id = ensure_parent_folder_id(get_env("GDRIVE_FOLDER_ID"))

    creds = service_account.Credentials.from_service_account_info(sa_json, scopes=SCOPES)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    if len(sys.argv) < 2:
        raise RuntimeError("Usage: python collectors/drive_upload.py <file1> <file2> ...")

    paths = [Path(p) for p in sys.argv[1:]]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing files: {missing}")

    for p in paths:
        file_id = upsert_file(service, folder_id, p)
        print(f"Uploaded {p.name} -> fileId={file_id}")


if __name__ == "__main__":
    main()
