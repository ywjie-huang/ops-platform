"""命令预设 CRUD API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.batch_exec import CommandPreset
from app.models.user import User

router = APIRouter(prefix="/batch-exec/presets", tags=["命令预设"])


class PresetCreate(BaseModel):
    name: str
    command: str
    description: str = ""
    sort_order: int = 0


class PresetUpdate(BaseModel):
    name: str | None = None
    command: str | None = None
    description: str | None = None
    sort_order: int | None = None


@router.get("/")
def list_presets(
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("batch_exec.view")),
):
    items = list(db.scalars(select(CommandPreset).order_by(CommandPreset.sort_order, CommandPreset.id)).all())
    return {
        "code": 0,
        "data": [
            {"id": p.id, "name": p.name, "command": p.command, "description": p.description, "sort_order": p.sort_order}
            for p in items
        ],
    }


@router.post("/")
def create_preset(
    body: PresetCreate,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("batch_exec.execute")),
):
    preset = CommandPreset(name=body.name, command=body.command, description=body.description, sort_order=body.sort_order)
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return {"code": 0, "data": {"id": preset.id}}


@router.put("/{preset_id}")
def update_preset(
    preset_id: int,
    body: PresetUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("batch_exec.execute")),
):
    preset = db.get(CommandPreset, preset_id)
    if not preset:
        return {"code": 1, "msg": "预设不存在"}
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(preset, field, val)
    db.commit()
    return {"code": 0, "msg": "更新成功"}


@router.delete("/{preset_id}")
def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("batch_exec.delete")),
):
    preset = db.get(CommandPreset, preset_id)
    if not preset:
        return {"code": 1, "msg": "预设不存在"}
    db.delete(preset)
    db.commit()
    return {"code": 0, "msg": "删除成功"}
