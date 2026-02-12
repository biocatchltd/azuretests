from __future__ import annotations

import json
import time
import uuid
from typing import Dict

TARGET_SIZE_BYTES = 125 * 1024  # 125 KiB


def build_payload_bytes(file_id: str, size_bytes: int = TARGET_SIZE_BYTES) -> bytes:
    """
    Build a JSON payload roughly 'size_bytes' in total when encoded as UTF-8.
    We'll pad with a 'padding' field to reach the desired size.
    """
    base: Dict[str, object] = {
        "fileId": file_id,

        "createdAtEpochMs": int(time.time() * 1000),
        "schemaVersion": 1,
        "data": {
            "message": "azure-files-loadgen",
            "note": "This is a synthetic file for performance validation.",
        },
    }
    head = json.dumps(base, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    remaining = max(0, size_bytes - len(head))
    # Create deterministic padding; not random to reduce CPU
    if remaining > 0:
        padding = {"padding": "x" * max(0, remaining - 20)}  # approximate, adjusting for JSON structure
        full = base.copy()
        full.update(padding)
        return json.dumps(full, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return head
