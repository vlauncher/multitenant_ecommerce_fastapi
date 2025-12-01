import uuid
import requests
from typing import Any, Dict

from core.config import settings


PAYSTACK_BASE_URL = "https://api.paystack.co"


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_transaction(email: str, amount: float, reference: str | None = None, callback_url: str | None = None, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ref = reference or str(uuid.uuid4())
    payload = {
        "email": email,
        "amount": int(round(amount * 100)),  # Paystack amount in kobo
        "reference": ref,
    }
    if callback_url or settings.PAYSTACK_CALLBACK_URL:
        payload["callback_url"] = callback_url or settings.PAYSTACK_CALLBACK_URL
    if metadata:
        payload["metadata"] = metadata

    resp = requests.post(f"{PAYSTACK_BASE_URL}/transaction/initialize", json=payload, headers=_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()


def verify_transaction(reference: str) -> Dict[str, Any]:
    resp = requests.get(f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()
