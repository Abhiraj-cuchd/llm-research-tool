import zipfile
import io
import logging

logger = logging.getLogger(__name__)


class UploadError(Exception):
    pass


def extract_zip(file_bytes: bytes) -> list[tuple[str, bytes]]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise UploadError("The uploaded file is not a valid ZIP archive.")

    names = zf.namelist()
    if not names:
        raise UploadError("The ZIP archive is empty.")

    docx_files = [n for n in names if n.lower().endswith(".docx") and not n.startswith("__MACOSX")]
    if not docx_files:
        raise UploadError("No .docx files found in the ZIP archive.")

    results = []
    for name in docx_files:
        results.append((name, zf.read(name)))

    non_docx = set(names) - set(docx_files)
    for skipped in non_docx:
        if not skipped.endswith("/"):
            logger.warning(f"Skipping non-DOCX file: {skipped}")

    return results
