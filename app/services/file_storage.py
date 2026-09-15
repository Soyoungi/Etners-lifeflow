import os
import uuid

import requests
from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import ApplicationAttachment

SUPABASE_SCHEME = "supabase:"


def _use_supabase():
    return bool(current_app.config.get("SUPABASE_URL") and current_app.config.get("SUPABASE_SERVICE_KEY"))


def _save_to_supabase(application_id, file_storage, safe_name):
    base_url = current_app.config["SUPABASE_URL"].rstrip("/")
    service_key = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = current_app.config["SUPABASE_BUCKET"]
    object_key = f"{application_id}/{uuid.uuid4().hex}_{safe_name}"

    file_storage.stream.seek(0)
    resp = requests.post(
        f"{base_url}/storage/v1/object/{bucket}/{object_key}",
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": file_storage.content_type or "application/octet-stream",
        },
        data=file_storage.stream.read(),
        timeout=30,
    )
    resp.raise_for_status()
    size = int(resp.headers.get("content-length", 0)) or None
    return f"{SUPABASE_SCHEME}{bucket}/{object_key}", size


def _save_to_local_disk(application_id, file_storage, safe_name):
    upload_dir = current_app.config["UPLOAD_DIR"]
    app_dir = os.path.join(upload_dir, str(application_id))
    os.makedirs(app_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    stored_path = os.path.join(app_dir, stored_name)
    file_storage.save(stored_path)
    return stored_path, os.path.getsize(stored_path)


def save_upload(application_id, label, file_storage):
    """업로드된 파일을 저장하고 첨부 레코드를 만든다.

    SUPABASE_URL/SUPABASE_SERVICE_KEY가 설정되어 있으면 Supabase Storage에,
    아니면 로컬 uploads/<application_id>/ 아래에 저장한다.
    """
    if file_storage is None or not file_storage.filename:
        return None

    original_filename = file_storage.filename
    safe_name = secure_filename(original_filename) or "file"

    if _use_supabase():
        stored_path, size = _save_to_supabase(application_id, file_storage, safe_name)
    else:
        stored_path, size = _save_to_local_disk(application_id, file_storage, safe_name)

    attachment = ApplicationAttachment(
        application_id=application_id,
        document_label=label,
        original_filename=original_filename,
        stored_path=stored_path,
        content_type=file_storage.content_type,
        size=size or 0,
    )
    db.session.add(attachment)
    return attachment


def resolve_download(attachment):
    """첨부파일을 내려받을 방법을 반환한다.

    Supabase 저장분은 서명된 URL(문자열), 로컬 저장분은 로컬 경로를 ("url"|"path", 값) 형태로 반환.
    """
    if attachment.stored_path.startswith(SUPABASE_SCHEME):
        bucket_and_key = attachment.stored_path[len(SUPABASE_SCHEME):]
        bucket, _, object_key = bucket_and_key.partition("/")
        base_url = current_app.config["SUPABASE_URL"].rstrip("/")
        service_key = current_app.config["SUPABASE_SERVICE_KEY"]
        resp = requests.post(
            f"{base_url}/storage/v1/object/sign/{bucket}/{object_key}",
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
            json={"expiresIn": 60},
            timeout=15,
        )
        resp.raise_for_status()
        signed_path = resp.json()["signedURL"]
        return "url", f"{base_url}/storage/v1{signed_path}"

    return "path", attachment.stored_path
