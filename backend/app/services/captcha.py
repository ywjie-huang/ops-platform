"""图形验证码 — 基于 captcha 库生成 + Redis 存储（带 TTL，Redis 不可用时降级为内存）。"""

from __future__ import annotations

import io
import random
import time
import uuid

from captcha.image import ImageCaptcha

from app.db.redis import get_redis

_TTL = 120  # 验证码有效期 120 秒
_KEY_PREFIX = "captcha:"

# 内存降级存储：captcha_id -> (code, expire_ts)
_store: dict[str, tuple[str, float]] = {}

_image = ImageCaptcha(width=160, height=60, fonts=None, font_sizes=(42,))


def _cleanup() -> None:
    """清理内存中过期的验证码（Redis 由 TTL 自动过期，无需清理）。"""
    now = time.time()
    expired = [k for k, v in _store.items() if v[1] < now]
    for k in expired:
        del _store[k]


def generate() -> tuple[str, bytes]:
    """生成验证码，返回 (captcha_id, image_bytes_png)。"""
    code = f"{random.randint(1000, 9999)}"
    captcha_id = uuid.uuid4().hex

    r = get_redis()
    if r is not None:
        r.setex(f"{_KEY_PREFIX}{captcha_id}", _TTL, code.lower())
    else:
        _cleanup()
        _store[captcha_id] = (code.lower(), time.time() + _TTL)

    data = io.BytesIO()
    _image.write(code, data)
    return captcha_id, data.getvalue()


def verify(captcha_id: str, code: str) -> bool:
    """校验验证码，使用一次即失效。"""
    if not captcha_id or not code:
        return False

    r = get_redis()
    if r is not None:
        key = f"{_KEY_PREFIX}{captcha_id}"
        # GETDEL 原子取出并删除，保证一次性使用（Redis >= 6.2）
        stored = r.getdel(key)
        if stored is None:
            return False
        return stored == code.strip().lower()

    entry = _store.pop(captcha_id, None)
    if entry is None:
        return False
    stored_code, expire_ts = entry
    if time.time() > expire_ts:
        return False
    return stored_code == code.strip().lower()
