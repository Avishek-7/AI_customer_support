import os
import uuid
from fastapi import UploadFile, HTTPException

# Directory where we store temporary uploaded files
UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_unique_filename(filename: str) -> str:
    extension = filename.split('.')[-1]
    return f"{uuid.uuid4()}.{extension}"

def validate_file_extension(file: UploadFile, allowed_extensions={"pdf"}) -> None:
    ext = file.filename.split('.')[-1].lower()
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
    validate_file_extension(upload_file.filename)
    validate_file_size(upload_file)

    unique_filename = generate_unique_filename(upload_file.filename)
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())

    upload_file.file.seek(0)  # Reset file pointer after saving
    return file_path

def delete_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        pass  # Log error in real application
