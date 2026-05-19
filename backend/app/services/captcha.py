"""图形验证码 — 基于 captcha 库生成 + 内存存储（带 TTL）。"""

from __future__ import annotations

import io
import time
import uuid
from typing import Optional

from captcha.image import ImageCaptcha

# 内存存储：captcha_id -> (code, expire_ts)
_store: dict[str, tuple[str, float]] = {}
_TTL = 120  # 验证码有效期 120 秒

_image = ImageCaptcha(width=160, height=60, fonts=None, font_sizes=(42,))


def _cleanup() -> None:
    """清理过期验证码。"""
    now = time.time()
    expired = [k for k, v in _store.items() if v[1] < now]
    for k in expired:
        del _store[k]


def generate() -> tuple[str, bytes]:
    """生成验证码，返回 (captcha_id, image_bytes_png)。"""
    _cleanup()
    # 生成 4 位随机数字
    import random
    code = f"{random.randint(1000, 9999)}"
    captcha_id = uuid.uuid4().hex
    _store[captcha_id] = (code.lower(), time.time() + _TTL)

    data = io.BytesIO()
    _image.write(code, data)
    return captcha_id, data.getvalue()


def verify(captcha_id: str, code: str) -> bool:
    """校验验证码，使用一次即失效。"""
    entry = _store.pop(captcha_id, None)
    if entry is None:
        return False
    stored_code, expire_ts = entry
    if time.time() > expire_ts:
        return False
    return stored_code == code.strip().lower()
