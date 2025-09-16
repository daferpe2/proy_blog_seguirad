from pathlib import Path
import uuid
import aiofiles
from fastapi import HTTPException, UploadFile
from fastapi import status

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
UPLOAD_DIR = Path("app/static/images")


def validate_image(file: UploadFile):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no permitido. Solo se aceptan imágenes JPEG o PNG."
        )
    return ext

async def save_image(file: UploadFile, ext: str) -> str:
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    async with aiofiles.open(filepath, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    return str(filepath)


async def save_image_name(file: UploadFile, ext: str) -> str:
    filename = f"{file.filename}"
    filepath = UPLOAD_DIR / filename
    async with aiofiles.open(filepath, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    return str(filepath)