import hmac
import hashlib
from fastapi import HTTPException, Header, status


def verify_github_signature(payload_bytes: bytes, secret: str, signature_header: str | None) -> bool:
    """
    Сравнивает HMAC-SHA256 подпись из заголовка GitHub с вычисленной подписью тела запроса.
    """
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    # Заголовок приходит в формате: "sha256=abcdef123456..."
    sha_type, _, signature = signature_header.partition("=")
    if sha_type != "sha256":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature algorithm. Only sha256 is supported.",
        )

    # Вычисляем HMAC-SHA256 от сырых байт тела запроса
    mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    # hmac.compare_digest защищает от атак по времени (timing attacks)
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    return True