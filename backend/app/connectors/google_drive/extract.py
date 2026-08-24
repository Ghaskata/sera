import io

from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

GOOGLE_DOC = "application/vnd.google-apps.document"
GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
PDF = "application/pdf"
TEXT_PLAIN = "text/plain"

SUPPORTED_MIME_TYPES = {GOOGLE_DOC, GOOGLE_SHEET, PDF, TEXT_PLAIN}


def extract_text(drive_service, file_id: str, mime_type: str) -> str | None:
    """Returns extracted text, or None if the file type isn't supported (skip + log by caller)."""
    if mime_type == GOOGLE_DOC:
        data = drive_service.files().export(fileId=file_id, mimeType="text/plain").execute()
        return data.decode("utf-8") if isinstance(data, bytes) else data

    if mime_type == GOOGLE_SHEET:
        data = drive_service.files().export(fileId=file_id, mimeType="text/csv").execute()
        return data.decode("utf-8") if isinstance(data, bytes) else data

    if mime_type in (PDF, TEXT_PLAIN):
        buffer = io.BytesIO()
        request = drive_service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)

        if mime_type == PDF:
            reader = PdfReader(buffer)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        return buffer.read().decode("utf-8", errors="ignore")

    return None
