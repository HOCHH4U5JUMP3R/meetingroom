from pathlib import Path
from uuid import uuid4
from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Float, select, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from . import main

app = main.app
Base = main.Base
Equipment = main.Equipment
DATA = main.DATA
MODEL_UPLOADS = DATA / 'uploads' / 'models'
MODEL_UPLOADS.mkdir(parents=True, exist_ok=True)

class EquipmentModel(Base):
    __tablename__ = 'equipment_models'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), default='')
    model_number: Mapped[str] = mapped_column(String(150), default='')
    category: Mapped[str] = mapped_column(String(80), default='')
    size_inches: Mapped[float | None] = mapped_column(Float, nullable=True)
    mounting: Mapped[str] = mapped_column(String(100), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    image_filename: Mapped[str] = mapped_column(String(255), default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class EquipmentModelAssignment(Base):
    __tablename__ = 'equipment_model_assignments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey('equipment.id', ondelete='CASCADE'), unique=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey('equipment_models.id', ondelete='RESTRICT'), index=True)

Base.metadata.create_all(main.engine)

class ModelIn(BaseModel):
    name: str
    manufacturer: str = ''
    model_number: str = ''
    category: str = ''
    size_inches: float | None = None
    mounting: str = ''
    description: str = ''
    active: bool = True

def model_dump(m):
    data = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    data['image_url'] = f'/uploads/models/{m.image_filename}' if m.image_filename else None
    return data

@app.get('/api/equipment-models')
def equipment_models(db: Session = Depends(main.db)):
    models = db.scalars(select(EquipmentModel).order_by(EquipmentModel.manufacturer, EquipmentModel.name)).all()
    counts = {x.model_id: x.count for x in db.execute(select(EquipmentModelAssignment.model_id, func.count(EquipmentModelAssignment.id).label('count')).group_by(EquipmentModelAssignment.model_id)).all()}
    return [{**model_dump(m), 'equipment_count': counts.get(m.id, 0)} for m in models]

@app.get('/api/equipment-models/stats')
def equipment_model_stats(db: Session = Depends(main.db)):
    model_count = db.scalar(select(func.count(EquipmentModel.id))) or 0
    manufacturer_count = db.scalar(select(func.count(func.distinct(EquipmentModel.manufacturer))).where(EquipmentModel.manufacturer != '')) or 0
    equipment_count = db.scalar(select(func.count(Equipment.id))) or 0
    assigned_count = db.scalar(select(func.count(EquipmentModelAssignment.id))) or 0
    return {
        'models': model_count,
        'manufacturers': manufacturer_count,
        'equipment': equipment_count,
        'assigned': assigned_count,
        'coverage': round(assigned_count / equipment_count * 100, 1) if equipment_count else 0,
    }

@app.get('/api/equipment-catalog')
def equipment_catalog(db: Session = Depends(main.db)):
    rows = db.execute(
        select(EquipmentModelAssignment.equipment_id, EquipmentModel)
        .join(EquipmentModel, EquipmentModel.id == EquipmentModelAssignment.model_id)
    ).all()
    return [
        {'equipment_id': equipment_id, 'model': model_dump(model)}
        for equipment_id, model in rows
    ]

@app.post('/api/equipment-models')
def create_equipment_model(payload: ModelIn, db: Session = Depends(main.db)):
    m = EquipmentModel(**payload.model_dump())
    db.add(m); db.commit(); db.refresh(m)
    return model_dump(m)

@app.get('/api/equipment-models/{model_id}')
def get_equipment_model(model_id: int, db: Session = Depends(main.db)):
    m = db.get(EquipmentModel, model_id)
    if not m: raise HTTPException(404, 'Modell nicht gefunden')
    return model_dump(m)

@app.put('/api/equipment-models/{model_id}')
def update_equipment_model(model_id: int, payload: ModelIn, db: Session = Depends(main.db)):
    m = db.get(EquipmentModel, model_id)
    if not m: raise HTTPException(404, 'Modell nicht gefunden')
    for key, value in payload.model_dump().items(): setattr(m, key, value)
    db.commit(); db.refresh(m)
    return model_dump(m)

@app.delete('/api/equipment-models/{model_id}')
def delete_equipment_model(model_id: int, db: Session = Depends(main.db)):
    m = db.get(EquipmentModel, model_id)
    if not m: raise HTTPException(404, 'Modell nicht gefunden')
    used = db.scalar(select(EquipmentModelAssignment).where(EquipmentModelAssignment.model_id == model_id).limit(1))
    if used: raise HTTPException(409, 'Modell wird noch von Equipment verwendet und kann nicht gelöscht werden.')
    db.delete(m); db.commit(); return {'ok': True}

@app.post('/api/equipment-models/{model_id}/image')
async def upload_model_image(model_id: int, file: UploadFile = File(...), db: Session = Depends(main.db)):
    m = db.get(EquipmentModel, model_id)
    if not m: raise HTTPException(404, 'Modell nicht gefunden')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}: raise HTTPException(400, 'Bitte ein Bild hochladen.')
    stored = f'{uuid4().hex}{suffix}'
    target = MODEL_UPLOADS / stored
    target.write_bytes(await file.read())
    m.image_filename = stored
    db.commit()
    return model_dump(m)

@app.put('/api/equipment/{equipment_id}/model')
def assign_equipment_model(equipment_id: int, model_id: int | None = None, db: Session = Depends(main.db)):
    eq = db.get(Equipment, equipment_id)
    if not eq: raise HTTPException(404, 'Gerät nicht gefunden')
    assignment = db.scalar(select(EquipmentModelAssignment).where(EquipmentModelAssignment.equipment_id == equipment_id))
    if model_id is None:
        if assignment: db.delete(assignment)
        db.commit(); return {'equipment_id': equipment_id, 'model': None}
    model = db.get(EquipmentModel, model_id)
    if not model: raise HTTPException(404, 'Modell nicht gefunden')
    if assignment: assignment.model_id = model_id
    else: db.add(EquipmentModelAssignment(equipment_id=equipment_id, model_id=model_id))
    db.commit()
    return {'equipment_id': equipment_id, 'model': model_dump(model)}

@app.get('/api/equipment/{equipment_id}/model')
def equipment_model(equipment_id: int, db: Session = Depends(main.db)):
    assignment = db.scalar(select(EquipmentModelAssignment).where(EquipmentModelAssignment.equipment_id == equipment_id))
    if not assignment: return {'model': None}
    model = db.get(EquipmentModel, assignment.model_id)
    return {'model': model_dump(model) if model else None}
