"""
File Management and Audit Logging Module for SecureStego.
Handles safe lossless file saving, extraction export, and persistent operation logging.
"""

import json
import mimetypes
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from PIL import Image

from securestego.core.exceptions import UnsupportedFormatError


@dataclass
class AuditLogEntry:
    id: str
    timestamp: str
    action: str  # "ENCODE", "DECODE", "ANALYZE", "EXPORT"
    status: str  # "SUCCESS", "FAILED"
    target_image: str
    payload_type: Optional[str] = None
    payload_size_bytes: Optional[int] = None
    details: Optional[str] = None
    integrity_verified: Optional[bool] = None


class AuditLogger:
    """
    Persistent JSON audit logger recording all steganographic actions and forensics.
    """

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            log_dir = os.path.join(os.path.expanduser("~"), ".securestego")
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "audit_history.json")

    def _read_logs(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_file):
            return []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_logs(self, logs: List[Dict[str, Any]]) -> None:
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            pass

    def log_action(
        self,
        action: str,
        status: str,
        target_image: str,
        payload_type: Optional[str] = None,
        payload_size_bytes: Optional[int] = None,
        details: Optional[str] = None,
        integrity_verified: Optional[bool] = None,
    ) -> AuditLogEntry:
        """Logs an event to the persistent audit trail."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_id = f"LOG-{int(time.time() * 1000)}"
        entry = AuditLogEntry(
            id=log_id,
            timestamp=timestamp,
            action=action.upper(),
            status=status.upper(),
            target_image=os.path.basename(target_image),
            payload_type=payload_type,
            payload_size_bytes=payload_size_bytes,
            details=details,
            integrity_verified=integrity_verified,
        )

        logs = self._read_logs()
        logs.insert(0, asdict(entry))  # Prepend newest
        # Cap at 500 entries
        if len(logs) > 500:
            logs = logs[:500]
        self._write_logs(logs)
        return entry

    def get_history(self, search_query: str = "", action_filter: str = "ALL") -> List[Dict[str, Any]]:
        """Retrieves and filters audit logs."""
        logs = self._read_logs()
        filtered = []
        q = search_query.lower().strip()
        act = action_filter.upper().strip()

        for item in logs:
            if act != "ALL" and item.get("action") != act:
                continue
            if q:
                match = (
                    q in str(item.get("target_image", "")).lower()
                    or q in str(item.get("details", "")).lower()
                    or q in str(item.get("action", "")).lower()
                    or q in str(item.get("id", "")).lower()
                )
                if not match:
                    continue
            filtered.append(item)
        return filtered

    def clear_logs(self) -> None:
        """Clears all audit logs."""
        self._write_logs([])


class FileManager:
    """
    Manages lossless image I/O and payload file exporting.
    """

    def __init__(self, logger: Optional[AuditLogger] = None):
        self.logger = logger or AuditLogger()

    @staticmethod
    def save_stego_image(image: Image.Image, output_path: str, optimize: bool = False) -> str:
        """
        Saves stego image in lossless PNG format.
        
        Args:
            image: Stego PIL Image.
            output_path: Target save path. Must have .png extension.
            optimize: If True, uses standard PNG chunk optimization without altering pixel data.
            
        Returns:
            Saved absolute file path.
        """
        if not output_path.lower().endswith(".png"):
            output_path = os.path.splitext(output_path)[0] + ".png"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Lossless PNG save
        image.save(output_path, format="PNG", optimize=optimize)
        return os.path.abspath(output_path)

    @staticmethod
    def export_extracted_file(
        data: bytes,
        output_directory: str,
        preferred_filename: Optional[str] = None,
        overwrite: bool = False,
    ) -> str:
        """
        Safely saves extracted binary payload to disk.
        
        Args:
            data: Raw file bytes.
            output_directory: Destination directory.
            preferred_filename: Stored filename from stego header.
            overwrite: If False, appends suffix (1), (2) to avoid collision.
            
        Returns:
            Destination file path.
        """
        os.makedirs(output_directory, exist_ok=True)
        filename = preferred_filename or "extracted_file.bin"
        # Sanitize filename
        filename = os.path.basename(filename)
        dest_path = os.path.join(output_directory, filename)

        if not overwrite and os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(output_directory, f"{base}_{counter}{ext}")
                counter += 1

        with open(dest_path, "wb") as f:
            f.write(data)

        return os.path.abspath(dest_path)

    @staticmethod
    def detect_mime_type(file_path: str) -> str:
        """Guesses MIME type from file extension or content."""
        mime, _ = mimetypes.guess_type(file_path)
        return mime or "application/octet-stream"
