"""Image metadata helpers for uploaded attachments."""

from __future__ import annotations


def detect_image_dimensions(file_bytes: bytes) -> dict:
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n") and len(file_bytes) >= 24:
        return {
            "format": "PNG",
            "width": int.from_bytes(file_bytes[16:20], "big"),
            "height": int.from_bytes(file_bytes[20:24], "big"),
        }
    if file_bytes[:3] == b"\xff\xd8\xff":
        offset = 2
        while offset + 9 < len(file_bytes):
            if file_bytes[offset] != 0xFF:
                offset += 1
                continue
            marker = file_bytes[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            if offset + 2 > len(file_bytes):
                break
            segment_length = int.from_bytes(file_bytes[offset : offset + 2], "big")
            if segment_length < 2:
                break
            if marker in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            } and offset + 7 < len(file_bytes):
                return {
                    "format": "JPEG",
                    "width": int.from_bytes(file_bytes[offset + 5 : offset + 7], "big"),
                    "height": int.from_bytes(file_bytes[offset + 3 : offset + 5], "big"),
                }
            offset += segment_length
    if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        if file_bytes[12:16] == b"VP8X" and len(file_bytes) >= 30:
            width = 1 + int.from_bytes(file_bytes[24:27], "little")
            height = 1 + int.from_bytes(file_bytes[27:30], "little")
            return {"format": "WEBP", "width": width, "height": height}
        return {"format": "WEBP"}
    return {}
