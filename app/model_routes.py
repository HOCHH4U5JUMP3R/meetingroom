from pathlib import Path
from uuid import uuid4
from datetime import date
import json
from typing import Optional
from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Float, select, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from . import main

app=main.app; Base=main.Base; Equipment=main.Equipment; DATA=main.DATA
MODEL_UPLOADS=DATA/'uploads'/'models'; MODEL_UPLOADS.mkdir(parents=True,exist_ok=True)

class FlexibleEquipmentIn(BaseModel):
    name:str; category:str='Monitor'; manufacturer:str=''; model:str=''; serial:str=''; size_inches:Optional[float]=None; mounting:str=''; status:str='Aktiv'; purchase_date:Optional[date]=None; purchase_price:float=0; host_name:str=''; inventory_number:str=''; mac_address:str=''; notes:str=''; location_type:str='Meetingraum'; location_label:str=''; responsible:str=''; custom_fields:dict=Field(default_factory=dict)
main.EquipmentIn=FlexibleEquipmentIn

class EquipmentModel(Base):
    __tablename__='equipment_models'
    id:Mapped[int]=mapped_column(Integer,primary_key=True); name:Mapped[str]=mapped_column(String(200),index=True); manufacturer:Mapped[str]=mapped_column(String(100),default=''); model_number:Mapped[str]=mapped_column(String(150),default=''); category:Mapped[str]=mapped_column(String(80),default=''); size_inches:Mapped[float|None]=mapped_column(Float,nullable=True); mounting:Mapped[str]=mapped_column(String(100),default=''); description:Mapped[str]=mapped_column(Text,default=''); image_filename:Mapped[str]=mapped_column(String(255),default=''); active:Mapped[bool]=mapped_column(Boolean,default=True); field_config:Mapped[str]=mapped_column(Text,default='[]')

class EquipmentModelAssignment(Base):
    __tablename__='equipment_model_assignments'
    id:Mapped[int]=mapped_column(Integer,primary_key=True); equipment_id:Mapped[int]=mapped_column(ForeignKey('equipment.id',ondelete='CASCADE'),unique=True,index=True); model_id:Mapped[int]=mapped_column(ForeignKey('equipment_models.id',ondelete='RESTRICT'),index=True)

Base.metadata.create_all(main.engine)
with main.engine.begin() as c:
    cols={r[1] for r in c.exec_driver_sql('PRAGMA table_info(equipment_models)')}
    if 'field_config' not in cols:c.exec_driver_sql("ALTER TABLE equipment_models ADD COLUMN field_config TEXT DEFAULT '[]'")
    cols={r[1] for r in c.exec_driver_sql('PRAGMA table_info(equipment)')}
    for n,sql in [('custom_fields',"ALTER TABLE equipment ADD COLUMN custom_fields TEXT DEFAULT '{}'"),('location_type',"ALTER TABLE equipment ADD COLUMN location_type VARCHAR(50) DEFAULT 'Meetingraum'"),('location_label',"ALTER TABLE equipment ADD COLUMN location_label VARCHAR(200) DEFAULT ''"),('responsible',"ALTER TABLE equipment ADD COLUMN responsible VARCHAR(200) DEFAULT ''")]:
        if n not in cols:c.exec_driver_sql(sql)

class ModelIn(BaseModel):
    name:str; manufacturer:str=''; model_number:str=''; category:str=''; size_inches:float|None=None; mounting:str=''; description:str=''; active:bool=True; field_config:list[str]=Field(default_factory=list)

def model_dump(m):
    d={c.name:getattr(m,c.name) for c in m.__table__.columns}
    try:d['field_config']=json.loads(m.field_config or '[]')
    except Exception:d['field_config']=[]
    d['image_url']=f'/uploads/models/{m.image_filename}' if m.image_filename else None
    return d

def equipment_dump(e):
    d={c.name:getattr(e,c.name) for c in e.__table__.columns}
    try:d['custom_fields']=json.loads(e.custom_fields or '{}')
    except Exception:d['custom_fields']={}
    return d

@app.get('/api/equipment-models')
def equipment_models(db:Session=Depends(main.db)):
    models=db.scalars(select(EquipmentModel).order_by(EquipmentModel.manufacturer,EquipmentModel.name)).all(); counts={x.model_id:x.count for x in db.execute(select(EquipmentModelAssignment.model_id,func.count(EquipmentModelAssignment.id).label('count')).group_by(EquipmentModelAssignment.model_id)).all()}
    return [{**model_dump(m),'equipment_count':counts.get(m.id,0)} for m in models]

@app.get('/api/equipment-models/stats')
def equipment_model_stats(db:Session=Depends(main.db)):
    mc=db.scalar(select(func.count(EquipmentModel.id))) or 0; manufacturers=db.scalar(select(func.count(func.distinct(EquipmentModel.manufacturer))).where(EquipmentModel.manufacturer!='')) or 0; ec=db.scalar(select(func.count(Equipment.id))) or 0; ac=db.scalar(select(func.count(EquipmentModelAssignment.id))) or 0
    return {'models':mc,'manufacturers':manufacturers,'equipment':ec,'assigned':ac,'coverage':round(ac/ec*100,1) if ec else 0}

@app.get('/api/equipment-catalog')
def equipment_catalog(db:Session=Depends(main.db)):
    rows=db.execute(select(EquipmentModelAssignment.equipment_id,EquipmentModel).join(EquipmentModel,EquipmentModel.id==EquipmentModelAssignment.model_id)).all(); return [{'equipment_id':eid,'model':model_dump(m)} for eid,m in rows]

@app.post('/api/equipment-models')
def create_equipment_model(payload:ModelIn,db:Session=Depends(main.db)):
    m=EquipmentModel(**{**payload.model_dump(exclude={'field_config'}),'field_config':json.dumps(payload.field_config)}); db.add(m); db.commit(); db.refresh(m); return model_dump(m)

@app.get('/api/equipment-models/{model_id}')
def get_equipment_model(model_id:int,db:Session=Depends(main.db)):
    m=db.get(EquipmentModel,model_id)
    if not m:raise HTTPException(404,'Modell nicht gefunden')
    return model_dump(m)

@app.put('/api/equipment-models/{model_id}')
def update_equipment_model(model_id:int,payload:ModelIn,db:Session=Depends(main.db)):
    m=db.get(EquipmentModel,model_id)
    if not m:raise HTTPException(404,'Modell nicht gefunden')
    for k,v in payload.model_dump(exclude={'field_config'}).items():setattr(m,k,v)
    m.field_config=json.dumps(payload.field_config); db.commit(); db.refresh(m); return model_dump(m)

@app.delete('/api/equipment-models/{model_id}')
def delete_equipment_model(model_id:int,db:Session=Depends(main.db)):
    m=db.get(EquipmentModel,model_id)
    if not m:raise HTTPException(404,'Modell nicht gefunden')
    if db.scalar(select(EquipmentModelAssignment).where(EquipmentModelAssignment.model_id==model_id).limit(1)):raise HTTPException(409,'Modell wird noch von Equipment verwendet und kann nicht gelöscht werden.')
    db.delete(m);db.commit();return {'ok':True}

@app.post('/api/equipment-models/{model_id}/image')
async def upload_model_image(model_id:int,file:UploadFile=File(...),db:Session=Depends(main.db)):
    m=db.get(EquipmentModel,model_id)
    if not m:raise HTTPException(404,'Modell nicht gefunden')
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.jpg','.jpeg','.png','.webp','.gif'}:raise HTTPException(400,'Bitte ein Bild hochladen.')
    stored=f'{uuid4().hex}{suffix}';(MODEL_UPLOADS/stored).write_bytes(await file.read());m.image_filename=stored;db.commit();return model_dump(m)

@app.put('/api/equipment/{equipment_id}/model')
def assign_equipment_model(equipment_id:int,model_id:int|None=None,db:Session=Depends(main.db)):
    eq=db.get(Equipment,equipment_id)
    if not eq:raise HTTPException(404,'Gerät nicht gefunden')
    a=db.scalar(select(EquipmentModelAssignment).where(EquipmentModelAssignment.equipment_id==equipment_id))
    if model_id is None:
        if a:db.delete(a)
    else:
        if not db.get(EquipmentModel,model_id):raise HTTPException(404,'Modell nicht gefunden')
        if a:a.model_id=model_id
        else:db.add(EquipmentModelAssignment(equipment_id=equipment_id,model_id=model_id))
    db.commit();return {'equipment_id':equipment_id,'model':model_dump(db.get(EquipmentModel,model_id)) if model_id else None}

@app.get('/api/equipment/{equipment_id}/model')
def equipment_model(equipment_id:int,db:Session=Depends(main.db)):
    a=db.scalar(select(EquipmentModelAssignment).where(EquipmentModelAssignment.equipment_id==equipment_id)); return {'model':model_dump(db.get(EquipmentModel,a.model_id)) if a else None}
