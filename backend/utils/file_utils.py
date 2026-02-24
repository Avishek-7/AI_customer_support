import os
import uuid
from fastapi import UploadFile, HTTPException
from utils.logger import get_logger

logger = get_logger("backend.utils.file_utils")

# Directory where we store temporary uploaded files
UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
CHUNK_SIZE = 64 * 1024

def generate_unique_filename(filename: str) -> str:
    _, extension = os.path.splitext(filename or "")
    if extension:
        return f"{uuid.uuid4()}{extension}"
    return f"{uuid.uuid4()}"

def validate_file_extension(file: UploadFile, allowed_extensions=frozenset({"pdf"})) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type: .{ext}. Allowed types: {allowed_extensions}")
    
def validate_file_size(file: UploadFile, max_mb: int = 10) -> None:
    file_size = 0
    for chunk in iter(lambda: file.file.read(1024 * 1024), b''):
        file_size += len(chunk)
        if file_size > max_mb * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large. Max size is {max_mb} MB.")
    file.file.seek(0)  # Reset file pointer after reading

def save_upload_file(upload_file: UploadFile) -> str:
    validate_file_extension(upload_file)
    validate_file_size(upload_file)

    unique_filename = generate_unique_filename(upload_file.filename)
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        while True:
            chunk = upload_file.file.read(CHUNK_SIZE)
            if not chunk:
                break
            buffer.write(chunk)

    upload_file.file.seek(0)  # Reset file pointer after saving
    return file_path

def delete_file(path: str) -> None:
    upload_root = os.path.abspath(UPLOAD_DIR)
    resolved_path = os.path.abspath(path)
    if os.path.commonpath([upload_root, resolved_path]) != upload_root:
        raise ValueError("Attempted to delete file outside upload directory")

    try:
        os.remove(resolved_path)
    except FileNotFoundError:
        logger.warning("File not found during delete", extra={"path": resolved_path})
        raise
    except PermissionError:
        logger.error("Permission denied deleting file", extra={"path": resolved_path})
        raise
