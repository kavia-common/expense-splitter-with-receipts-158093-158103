import os
import uuid
from typing import Optional

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def _upload_dir() -> str:
    """Return the absolute uploads directory path from app config, ensuring it exists."""
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        # Fallback in case config is missing; shouldn't happen as __init__ sets it.
        upload_folder = os.path.join(os.getcwd(), "receipts")
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


# PUBLIC_INTERFACE
def save_receipt_file(file: FileStorage, filename: Optional[str] = None) -> str:
    """Save an uploaded receipt file to the configured upload folder.

    Parameters:
        file: The FileStorage object from Flask containing the uploaded file.
        filename: Optional explicit filename to use; if not provided, a UUID-based
                  filename will be generated while preserving the original extension.

    Returns:
        The saved filename (not the full path). Store this in the database to reference
        the receipt later using get_receipt_path.

    Raises:
        ValueError: If no file is provided or the file has an empty filename.
    """
    if file is None:
        raise ValueError("No file provided.")

    original_name = secure_filename(file.filename or "")
    if not original_name and not filename:
        raise ValueError("Invalid file name.")

    # Determine the final filename
    if filename:
        safe_name = secure_filename(filename)
    else:
        _, ext = os.path.splitext(original_name)
        safe_name = f"{uuid.uuid4().hex}{ext.lower()}"

    dest_dir = _upload_dir()
    dest_path = os.path.join(dest_dir, safe_name)
    file.save(dest_path)
    return safe_name


# PUBLIC_INTERFACE
def get_receipt_path(filename: str) -> str:
    """Get the absolute path on disk for a receipt filename.

    Parameters:
        filename: The stored filename of the receipt.

    Returns:
        Absolute file path where the receipt is stored.
    """
    if not filename:
        raise ValueError("Filename must be provided.")
    return os.path.join(_upload_dir(), secure_filename(filename))
