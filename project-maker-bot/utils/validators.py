from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Dict, Tuple

from pydantic import BaseModel, EmailStr, Field, ValidationError


class TaskRequest(BaseModel):
    email: EmailStr
    secret: str
    task: str
    round: int
    nonce: str
    evaluation_url: str = Field(min_length=1)


def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_secret(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided, expected)


def validate_request(payload: Dict[str, Any]) -> Tuple[TaskRequest | None, str | None]:
    try:
        req = TaskRequest.model_validate(payload)
    except ValidationError as e:
        return None, e.json()
    return req, None
