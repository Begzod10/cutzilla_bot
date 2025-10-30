import time
import hmac
import hashlib
import base64
from typing import Optional
import os
from dotenv import load_dotenv
import struct

load_dotenv()


def _secret() -> bytes:
    s = os.getenv("DEEP_LINK_SECRET", "change-me-rotate-regularly")
    return s.encode("utf-8") if isinstance(s, str) else s


SECRET: bytes = _secret()


def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)


TAG_BARBER = b"b"  # 1 byte


def sign_barber_token(barber_id: int) -> str:
    ts = int(time.time())
    data = TAG_BARBER + struct.pack("!I", barber_id) + struct.pack("!I", ts)
    sig = hmac.new(SECRET, data, hashlib.sha256).digest()[:10]  # 10-byte MAC
    return _b64u_encode(data + sig)


def verify_barber_token(token: str, max_age_sec: int = 86400 * 365) -> Optional[int]:
    try:
        raw = _b64u_decode(token)
        if len(raw) != 1 + 4 + 4 + 10 or raw[:1] != TAG_BARBER:
            return None
        data, sig = raw[:-10], raw[-10:]
        if not hmac.compare_digest(hmac.new(SECRET, data, hashlib.sha256).digest()[:10], sig):
            return None
        barber_id = struct.unpack("!I", data[1:5])[0]
        ts = struct.unpack("!I", data[5:9])[0]
        if time.time() - ts > max_age_sec:
            return None
        return barber_id
    except Exception:
        return None
