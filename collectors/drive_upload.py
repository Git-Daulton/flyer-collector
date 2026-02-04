import os
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def drive_service():
    client_id = os.environ["GDRIVE_CLIENT_ID"]
    client_secret = os.environ["GDRIVE_CLIENT_SECRET"]
    refresh_token = os.environ["GDRIVE_REFRESH_TOKEN"]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    # Exchange refresh_token -> access token
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def find_existing(service, folder_id: str, name: str):
    safe_name = name.replace("'", "\\'")
    q = f"name='{safe_name}' and '{folder_id}' in parents and trashed=false"
    resp = service.files().list(q=q, fields="files(id,name)", pageSize=10).execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None



def upsert_file(service, folder_id: str, path: Path):
    name = path.name
    media = MediaFileUpload(str(path), resumable=True)

    existing_id = find_existing(service, folder_id, name)
    if existing_id:
        service.files().update(fileId=existing_id, media_body=media).execute()
        print(f"[drive] updated: {name} ({existing_id})")
        return existing_id

    meta = {"name": name, "parents": [folder_id]}
    created = service.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = created["id"]
    print(f"[drive] created: {name} ({file_id})")
    return file_id


def main():
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    service = drive_service()

    if len(sys.argv) < 2:
        print("Usage: drive_upload.py <file1> <file2> ...")
        sys.exit(2)

    for p in sys.argv[1:]:
        path = Path(p)
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty file: {path}")
        upsert_file(service, folder_id, path)


if __name__ == "__main__":
    main()
