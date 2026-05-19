"""SSH 密钥模型 —— 存储 SSH 密钥对 / 密码凭据，供主机 SSH 连接复用。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SSHKey(Base):
    __tablename__ = "ssh_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="密钥名称，如「生产环境通用密钥」")
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="password", comment="认证类型：password / key")
    username: Mapped[str] = mapped_column(String(100), nullable=False, default="root", comment="SSH 登录用户名")
    password: Mapped[str] = mapped_column(String(200), default="", comment="SSH 密码（auth_type=password 时使用）")
    private_key: Mapped[str] = mapped_column(Text, default="", comment="SSH 私钥内容（auth_type=key 时使用）")
    passphrase: Mapped[str] = mapped_column(String(200), default="", comment="私钥密码（如果私钥有密码保护）")
    port: Mapped[int] = mapped_column(Integer, default=22, comment="默认 SSH 端口")
    description: Mapped[str] = mapped_column(Text, default="", comment="备注说明")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为默认密钥")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
