import hashlib
import hmac


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    expected = generate_signature(payload_bytes, secret)
    return hmac.compare_digest(expected, signature_header)