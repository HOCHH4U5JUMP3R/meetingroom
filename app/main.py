from pathlib import Path
from uuid import uuid4
from datetime import date
from typing import Literal, Optional
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, String, Integer, Float, Date, Text, ForeignKey, Boolean, UniqueConstraint, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
engine = create_engine(f"sqlite:///{DATA/'meetingrooms.db'}", connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass
class Room(Base):
    __tablename__='rooms'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(200),unique=True,index=True); site:Mapped[str]=mapped_column(String(100),default=''); building:Mapped[str]=mapped_column(String(100),default=''); floor:Mapped[str]=mapped_column(String(50),default=''); room_number:Mapped[str]=mapped_column(String(50),default=''); length:Mapped[Optional[float]]=mapped_column(Float,nullable=True); width:Mapped[Optional[float]]=mapped_column(Float,nullable=True); height:Mapped[Optional[float]]=mapped_column(Float,nullable=True); seats:Mapped[Optional[int]]=mapped_column(Integer,nullable=True); specialty:Mapped[str]=mapped_column(Text,default=''); category:Mapped[str]=mapped_column(String(100),default=''); outlook_resource:Mapped[str]=mapped_column(String(200),default=''); connections:Mapped[str]=mapped_column(Text,default=''); owner:Mapped[str]=mapped_column(String(200),default=''); host_name:Mapped[str]=mapped_column(String(200),default=''); image_filename:Mapped[str]=mapped_column(String(255),default=''); notes:Mapped[str]=mapped_column(Text,default=''); status:Mapped[str]=mapped_column(String(50),default='Aktiv'); last_modernization:Mapped[Optional[date]]=mapped_column(Date,nullable=True); equipment=relationship('Equipment',cascade='all, delete-orphan'); rules=relationship('BookingRule',cascade='all, delete-orphan'); projects=relationship('Modernization',cascade='all, delete-orphan'); tickets=relationship('Ticket',cascade='all, delete-orphan')
class Equipment(Base):
    __tablename__='equipment'; id:Mapped[int]=mapped_column(primary_key=True); room_id:Mapped[int]=mapped_column(ForeignKey('rooms.id',ondelete='CASCADE'),index=True); name:Mapped[str]=mapped_column(String(150)); category:Mapped[str]=mapped_column(String(80),default=''); manufacturer:Mapped[str]=mapped_column(String(80),default=''); model:Mapped[str]=mapped_column(String(120),default=''); serial:Mapped[str]=mapped_column(String(120),default=''); size_inches:Mapped[Optional[float]]=mapped_column(Float,nullable=True); mounting:Mapped[str]=mapped_column(String(80),default=''); status:Mapped[str]=mapped_column(String(50),default='Aktiv'); purchase_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True); purchase_price:Mapped[float]=mapped_column(Float,default=0); host_name:Mapped[str]=mapped_column(String(200),default=''); inventory_number:Mapped[str]=mapped_column(String(120),default=''); mac_address:Mapped[str]=mapped_column(String(32),default=''); documents=relationship('EquipmentDocument',cascade='all, delete-orphan'); notes:Mapped[str]=mapped_column(Text,default='')
class EquipmentDocument(Base):
    __tablename__='equipment_documents'; id:Mapped[int]=mapped_column(primary_key=True); equipment_id:Mapped[int]=mapped_column(ForeignKey('equipment.id',ondelete='CASCADE'),index=True); kind:Mapped[str]=mapped_column(String(20)); filename:Mapped[str]=mapped_column(String(255)); stored_name:Mapped[str]=mapped_column(String(255))
class BookingRule(Base):
    __tablename__='booking_rules'; id:Mapped[int]=mapped_column(primary_key=True); room_id:Mapped[int]=mapped_column(ForeignKey('rooms.id',ondelete='CASCADE'),index=True); entitlement:Mapped[str]=mapped_column(String(100),default='Alle Mitarbeiter'); group_name:Mapped[str]=mapped_column(String(200),default=''); approval_required:Mapped[bool]=mapped_column(Boolean,default=False); approver:Mapped[str]=mapped_column(String(200),default=''); approval_type:Mapped[str]=mapped_column(String(100),default='Keine Genehmigung'); notes:Mapped[str]=mapped_column(Text,default='')
class Modernization(Base):
    __tablename__='modernizations'; id:Mapped[int]=mapped_column(primary_key=True); room_id:Mapped[int]=mapped_column(ForeignKey('rooms.id',ondelete='CASCADE'),index=True); project_name:Mapped[str]=mapped_column(String(200)); project_year:Mapped[Optional[int]]=mapped_column(Integer,nullable=True); status:Mapped[str]=mapped_column(String(50),default='Idee'); budget:Mapped[float]=mapped_column(Float,default=0); commissioned:Mapped[float]=mapped_column(Float,default=0); actual_cost:Mapped[float]=mapped_column(Float,default=0); supplier:Mapped[str]=mapped_column(String(200),default=''); responsible:Mapped[str]=mapped_column(String(200),default=''); start_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True); planned_end:Mapped[Optional[date]]=mapped_column(Date,nullable=True); completion_date:Mapped[Optional[date]]=mapped_column(Date,nullable=True); order_number:Mapped[str]=mapped_column(String(100),default=''); notes:Mapped[str]=mapped_column(Text,default='')
class Ticket(Base):
    __tablename__='tickets'; id:Mapped[int]=mapped_column(primary_key=True); room_id:Mapped[int]=mapped_column(ForeignKey('rooms.id',ondelete='CASCADE'),index=True); ticket_number:Mapped[str]=mapped_column(String(100)); subject:Mapped[str]=mapped_column(String(250)); category:Mapped[str]=mapped_column(String(80),default='Sonstiges'); status:Mapped[str]=mapped_column(String(50),default='Offen'); priority:Mapped[str]=mapped_column(String(50),default='Normal'); created_at:Mapped[Optional[date]]=mapped_column(Date,nullable=True); resolved_at:Mapped[Optional[date]]=mapped_column(Date,nullable=True); responsible:Mapped[str]=mapped_column(String(200),default=''); description:Mapped[str]=mapped_column(Text,default=''); notes:Mapped[str]=mapped_column(Text,default='')
class BudgetSettings(Base):
    __tablename__='budget_settings'; id:Mapped[int]=mapped_column(primary_key=True); overall_budget:Mapped[float]=mapped_column(Float,default=0)
class SiteBudget(Base):
    __tablename__='site_budgets'; id:Mapped[int]=mapped_column(primary_key=True); site:Mapped[str]=mapped_column(String(100),unique=True,index=True); budget:Mapped[float]=mapped_column(Float,default=0)
class YearlyBudget(Base):
    __tablename__='yearly_budgets'; __table_args__=(UniqueConstraint('year','site',name='uq_yearly_budget_year_site'),); id:Mapped[int]=mapped_column(primary_key=True); year:Mapped[int]=mapped_column(Integer,index=True); site:Mapped[Optional[str]]=mapped_column(String(100),nullable=True,index=True); budget:Mapped[float]=mapped_column(Float,default=0)

Base.metadata.create_all(engine)
with engine.begin() as connection:
    room_columns={row[1] for row in connection.exec_driver_sql('PRAGMA table_info(rooms)')}
    if 'image_filename' not in room_columns: connection.exec_driver_sql("ALTER TABLE rooms ADD COLUMN image_filename VARCHAR(255) DEFAULT ''")
    columns={row[1] for row in connection.exec_driver_sql('PRAGMA table_info(equipment)')}
    for name,sql in [('purchase_price','ALTER TABLE equipment ADD COLUMN purchase_price FLOAT DEFAULT 0'),('host_name',"ALTER TABLE equipment ADD COLUMN host_name VARCHAR(200) DEFAULT ''"),('inventory_number',"ALTER TABLE equipment ADD COLUMN inventory_number VARCHAR(120) DEFAULT ''"),('mac_address',"ALTER TABLE equipment ADD COLUMN mac_address VARCHAR(32) DEFAULT ''")]:
        if name not in columns: connection.exec_driver_sql(sql)

app=FastAPI(title='Meetingraumverwaltung',version='2.0.0'); app.mount('/static',StaticFiles(directory=BASE/'app'/'static'),name='static')
UPLOADS=DATA/'uploads'; UPLOADS.mkdir(exist_ok=True); app.mount('/uploads',StaticFiles(directory=UPLOADS),name='uploads')
def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
def dump(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
def room_image_url(room): return f'/uploads/rooms/{room.id}/{room.image_filename}' if room.image_filename else None
def model_for(kind): return {'rooms':Room,'equipment':Equipment,'rules':BookingRule,'modernizations':Modernization,'tickets':Ticket}[kind]
def schema_for(kind): return {'equipment':EquipmentIn,'rules':RuleIn,'modernizations':ModernizationIn,'tickets':TicketIn}[kind]
@app.get('/')
def index(): return FileResponse(BASE/'app'/'static'/'index.html')
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/api/rooms')
def rooms(db:Session=Depends(db)):
    return [dict(dump(x),image_url=room_image_url(x),ticket_count=len(x.tickets),open_ticket_count=sum(t.status in ['Offen','In Bearbeitung'] for t in x.tickets)) for x in db.scalars(select(Room).order_by(Room.site,Room.building,Room.floor,Room.name)).all()]
@app.get('/api/rooms/{room_id}')
def room_detail(room_id:int,db:Session=Depends(db)):
    r=db.get(Room,room_id)
    if not r: raise HTTPException(404,'Raum nicht gefunden')
    data=dump(r); data['image_url']=room_image_url(r); data['area']=round((r.length or 0)*(r.width or 0),2) if r.length and r.width else None
    data['equipment']=[dict(dump(x),documents=[dict(dump(doc),url=f'/uploads/{x.id}/{doc.stored_name}') for doc in x.documents]) for x in r.equipment]; data['rules']=[dump(x) for x in r.rules]; data['modernizations']=[dump(x) for x in r.projects]; data['tickets']=[dump(x) for x in sorted(r.tickets,key=lambda x:x.id,reverse=True)]
    dates=[item.completion_date or item.planned_end or item.start_date or date(item.project_year,12,31) for item in r.projects if item.completion_date or item.planned_end or item.start_date or item.project_year]+[item.purchase_date for item in r.equipment if item.purchase_date]; data['last_modernization']=max(dates,default=None).isoformat() if dates else None; data['host_name']=next((item.host_name for item in r.equipment if item.category=='VC-System' and item.host_name),''); return data

def project_year(p): return p.project_year or (p.start_date.year if p.start_date else None)
def budget_scope_matches(p,year,quarter=None,month=None):
    if project_year(p)!=year:return False
    if month is None and quarter is None:return True
    if not p.start_date:return False
    return p.start_date.month==month if month is not None else (p.start_date.month-1)//3+1==quarter
def budget_years(db):
    current=date.today().year; years=set(range(current-3,current+4)); years.update(x.year for x in db.scalars(select(YearlyBudget)).all()); projects=db.scalars(select(Modernization)).all(); years.update(x.project_year for x in projects if x.project_year); years.update(x.start_date.year for x in projects if x.start_date); years.update(x.purchase_date.year for x in db.scalars(select(Equipment).where(Equipment.purchase_date.is_not(None))).all()); return sorted(y for y in years if y)
DA_SITES={'nürnberg','nuernberg','frankfurt','rostock','überlingen','ueberlingen','toulouse'}
def division_for(site): return 'DA' if str(site or '').strip().casefold() in DA_SITES else 'DAv'

@app.get('/api/budget-overview')
def budget_overview(year:Optional[int]=None,quarter:Optional[int]=None,month:Optional[int]=None,db:Session=Depends(db)):
    selected=year or date.today().year
    if quarter is not None and quarter not in [1,2,3,4]: raise HTTPException(400,'Ungültiges Quartal')
    if month is not None and month not in range(1,13): raise HTTPException(400,'Ungültiger Monat')
    configured={(x.site,x.year):x.budget for x in db.scalars(select(YearlyBudget)).all()}; legacy={x.site:x.budget for x in db.scalars(select(SiteBudget)).all()}; totals={}
    for room in db.scalars(select(Room)).all():
        site=room.site or 'Ohne Standort'; e=totals.setdefault(site,{'site':site,'division':division_for(site),'rooms':0,'budget':configured.get((site,selected),legacy.get(site,0) if selected==date.today().year else 0),'modernization_planned':0,'modernization_commissioned':0,'modernization_spent':0,'equipment_spent':0}); e['rooms']+=1
        for eq in room.equipment:
            if eq.purchase_date and eq.purchase_date.year==selected and (month is None or eq.purchase_date.month==month) and (quarter is None or (eq.purchase_date.month-1)//3+1==quarter): e['equipment_spent']+=eq.purchase_price or 0
        for p in room.projects:
            if budget_scope_matches(p,selected,quarter,month): e['modernization_planned']+=p.budget or 0; e['modernization_commissioned']+=p.commissioned or 0; e['modernization_spent']+=p.actual_cost or 0
    for (site,budget_year),budget in configured.items():
        if budget_year==selected:
            key=site or 'Ohne Standort'; totals.setdefault(key,{'site':key,'division':division_for(key),'rooms':0,'budget':budget,'modernization_planned':0,'modernization_commissioned':0,'modernization_spent':0,'equipment_spent':0}); totals[key]['budget']=budget
    sites=sorted(totals.values(),key=lambda x:(x['division'],x['site']))
    for e in sites:
        e['spent']=e['modernization_spent']+e['equipment_spent']; e['committed']=max(e['modernization_commissioned'],e['modernization_spent'])+e['equipment_spent']; e['forecast']=e['modernization_planned']+e['equipment_spent']; e['available']=e['budget']-e['committed']; e['utilization']=round((e['committed']/e['budget']*100),1) if e['budget'] else 0
    settings=db.scalar(select(BudgetSettings).limit(1)); overall=configured.get((None,selected),settings.overall_budget if settings and selected==date.today().year else 0)
    total={'budget':overall,'modernization_planned':sum(x['modernization_planned'] for x in sites),'modernization_commissioned':sum(x['modernization_commissioned'] for x in sites),'modernization_spent':sum(x['modernization_spent'] for x in sites),'equipment_spent':sum(x['equipment_spent'] for x in sites)}; total['spent']=total['modernization_spent']+total['equipment_spent']; total['committed']=sum(x['committed'] for x in sites); total['forecast']=total['modernization_planned']+total['equipment_spent']; total['available']=total['budget']-total['committed']; total['utilization']=round(total['committed']/total['budget']*100,1) if total['budget'] else 0
    divisions=[]
    for d in ['DA','DAv']:
        items=[x for x in sites if x['division']==d]; row={'division':d,'sites':len(items),'rooms':sum(x['rooms'] for x in items),'budget':sum(x['budget'] for x in items),'modernization_planned':sum(x['modernization_planned'] for x in items),'modernization_commissioned':sum(x['modernization_commissioned'] for x in items),'modernization_spent':sum(x['modernization_spent'] for x in items),'equipment_spent':sum(x['equipment_spent'] for x in items),'spent':sum(x['spent'] for x in items),'committed':sum(x['committed'] for x in items),'forecast':sum(x['forecast'] for x in items),'available':sum(x['available'] for x in items)}; row['utilization']=round(row['committed']/row['budget']*100,1) if row['budget'] else 0; divisions.append(row)
    return {'year':selected,'quarter':quarter,'month':month,'years':budget_years(db),'total':total,'sites':sites,'divisions':divisions}

class BudgetAmountIn(BaseModel): budget:float=0
@app.put('/api/budget-overview/global')
def update_overall_budget(payload:BudgetAmountIn,year:int,db:Session=Depends(db)):
    e=db.scalar(select(YearlyBudget).where(YearlyBudget.year==year,YearlyBudget.site.is_(None))); e=e or YearlyBudget(year=year,site=None); e.budget=payload.budget; db.add(e); db.commit(); return {'year':year,'budget':e.budget}
@app.put('/api/budget-overview/sites/{site}')
def update_site_budget(site:str,payload:BudgetAmountIn,year:int,db:Session=Depends(db)):
    if not site.strip(): raise HTTPException(400,'Standort darf nicht leer sein')
    e=db.scalar(select(YearlyBudget).where(YearlyBudget.year==year,YearlyBudget.site==site)); e=e or YearlyBudget(year=year,site=site); e.budget=payload.budget; db.add(e); db.commit(); return {'site':site,'year':year,'budget':e.budget}
@app.get('/api/dashboard')
def dashboard(db:Session=Depends(db)):
    rows=db.scalars(select(Modernization)).all(); return {'rooms':db.scalar(select(func.count(Room.id))) or 0,'open_tickets':db.scalar(select(func.count(Ticket.id)).where(Ticket.status.in_(['Offen','In Bearbeitung']))) or 0,'budget':sum(x.budget or 0 for x in rows),'commissioned':sum(x.commissioned or 0 for x in rows),'actual':sum(x.actual_cost or 0 for x in rows),'available':sum((x.budget or 0)-(x.commissioned or 0) for x in rows)}
class RoomIn(BaseModel): name:str; site:str=''; building:str=''; floor:str=''; room_number:str=''; length:Optional[float]=None; width:Optional[float]=None; height:Optional[float]=None; seats:Optional[int]=None; specialty:str=''; category:str=''; outlook_resource:str=''; connections:str=''; owner:str=''; host_name:str=''; notes:str=''; status:str='Aktiv'; last_modernization:Optional[date]=None
class EquipmentIn(BaseModel): name:str; category:Literal['Monitor','VC-System','Mikrofon','Lautsprecher','Zubehör']='Monitor'; manufacturer:str=''; model:str=''; serial:str=''; size_inches:Optional[float]=None; mounting:str=''; status:str='Aktiv'; purchase_date:Optional[date]=None; purchase_price:float=0; host_name:str=''; inventory_number:str=''; mac_address:str=''; notes:str=''
class RuleIn(BaseModel): entitlement:str='Alle Mitarbeiter'; group_name:str=''; approval_required:bool=False; approver:str=''; approval_type:str='Keine Genehmigung'; notes:str=''
class ModernizationIn(BaseModel): project_name:str; project_year:Optional[int]=None; status:str='Idee'; budget:float=0; commissioned:float=0; actual_cost:float=0; supplier:str=''; responsible:str=''; start_date:Optional[date]=None; planned_end:Optional[date]=None; completion_date:Optional[date]=None; order_number:str=''; notes:str=''
class TicketIn(BaseModel): ticket_number:str; subject:str; category:str='Sonstiges'; status:str='Offen'; priority:str='Normal'; created_at:Optional[date]=None; resolved_at:Optional[date]=None; responsible:str=''; description:str=''; notes:str=''
@app.post('/api/rooms')
def create_room(x:RoomIn,db:Session=Depends(db)):
    if db.scalar(select(Room).where(Room.name==x.name)): raise HTTPException(409,'Raumname existiert bereits')
    r=Room(**x.model_dump()); db.add(r); db.commit(); db.refresh(r); return dump(r)
@app.put('/api/rooms/{rid}')
def update_room(rid:int,x:RoomIn,db:Session=Depends(db)):
    r=db.get(Room,rid)
    if not r: raise HTTPException(404,'Raum nicht gefunden')
    for k,v in x.model_dump().items(): setattr(r,k,v)
    db.commit(); db.refresh(r); return dump(r)
@app.delete('/api/rooms/{rid}')
def delete_room(rid:int,db:Session=Depends(db)):
    room=db.get(Room,rid)
    if not room: raise HTTPException(404,'Raum nicht gefunden')
    if room.image_filename:(UPLOADS/'rooms'/str(rid)/room.image_filename).unlink(missing_ok=True)
    db.delete(room); db.commit(); return {'ok':True}
@app.post('/api/rooms/{rid}/image')
async def upload_room_image(rid:int,file:UploadFile=File(...),db:Session=Depends(db)):
    room=db.get(Room,rid)
    if not room: raise HTTPException(404,'Raum nicht gefunden')
    if not (file.content_type or '').startswith('image/'): raise HTTPException(400,'Es kann nur eine Bilddatei hochgeladen werden')
    filename=Path(file.filename or '').name
    if not filename: raise HTTPException(400,'Datei fehlt')
    directory=UPLOADS/'rooms'/str(rid); directory.mkdir(parents=True,exist_ok=True)
    if room.image_filename:(directory/room.image_filename).unlink(missing_ok=True)
    room.image_filename=f'{uuid4().hex}_{filename}'; (directory/room.image_filename).write_bytes(await file.read()); db.commit(); return {'image_url':room_image_url(room)}
@app.post('/api/equipment/{equipment_id}/documents')
async def upload_equipment_document(equipment_id:int,kind:str,file:UploadFile=File(...),db:Session=Depends(db)):
    if kind not in ['offer','invoice','image']: raise HTTPException(400,'Ungültiger Dokumenttyp')
    equipment=db.get(Equipment,equipment_id)
    if not equipment: raise HTTPException(404,'Ausstattung nicht gefunden')
    filename=Path(file.filename or '').name
    if not filename: raise HTTPException(400,'Datei fehlt')
    directory=UPLOADS/str(equipment_id); directory.mkdir(parents=True,exist_ok=True); stored_name=f'{uuid4().hex}_{filename}'; (directory/stored_name).write_bytes(await file.read()); document=EquipmentDocument(equipment_id=equipment_id,kind=kind,filename=filename,stored_name=stored_name); db.add(document); db.commit(); db.refresh(document); return dict(dump(document),url=f'/uploads/{equipment_id}/{stored_name}')
@app.post('/api/rooms/{rid}/{kind}')
def create_child(rid:int,kind:str,payload:dict,db:Session=Depends(db)):
    r=db.get(Room,rid)
    if not r: raise HTTPException(404,'Raum nicht gefunden')
    if kind not in ['equipment','rules','modernizations','tickets']: raise HTTPException(400,'Ungültiger Bereich')
    cls=model_for(kind); data=schema_for(kind)(**payload).model_dump(); data['room_id']=rid; obj=cls(**data); db.add(obj); db.commit(); db.refresh(obj); return dump(obj)
@app.put('/api/{kind}/{oid}')
def update_child(kind:str,oid:int,payload:dict,db:Session=Depends(db)):
    if kind not in ['equipment','rules','modernizations','tickets']: raise HTTPException(400,'Ungültiger Bereich')
    obj=db.get(model_for(kind),oid)
    if not obj: raise HTTPException(404,'Eintrag nicht gefunden')
    data=schema_for(kind)(**payload).model_dump()
    for k,v in data.items():
        if hasattr(obj,k) and k not in ['id','room_id']: setattr(obj,k,v)
    db.commit(); db.refresh(obj); return dump(obj)
@app.delete('/api/{kind}/{oid}')
def delete_child(kind:str,oid:int,db:Session=Depends(db)):
    if kind not in ['equipment','rules','modernizations','tickets']: raise HTTPException(400,'Ungültiger Bereich')
    obj=db.get(model_for(kind),oid)
    if not obj: raise HTTPException(404,'Eintrag nicht gefunden')
    db.delete(obj); db.commit(); return {'ok':True}
with SessionLocal() as s:
    if not s.scalar(select(Room)):
        r=Room(name='Beispielraum 101',site='Nürnberg',building='Gebäude A',floor='EG',room_number='101',seats=12,category='Besprechungsraum',owner='Raumverantwortlicher',status='Aktiv',connections='HDMI · USB-C · Miracast'); s.add(r); s.commit(); s.refresh(r); s.add_all([Equipment(room_id=r.id,name='Hauptdisplay',category='Monitor',manufacturer='Samsung',model='Beispielmodell',size_inches=86,mounting='Wand',status='Aktiv'),Equipment(room_id=r.id,name='VC-System',category='VC-System',manufacturer='Crestron',model='Beispielmodell',status='Aktiv')]); s.add(BookingRule(room_id=r.id,entitlement='Alle Mitarbeiter',approval_required=False,approval_type='Keine Genehmigung')); s.add(Modernization(room_id=r.id,project_name='Beispiel Modernisierung 2026',project_year=2026,status='Planung',budget=15000,commissioned=8500,actual_cost=0)); s.add(Ticket(room_id=r.id,ticket_number='12345',subject='Beispiel: Kamera ohne Bild',category='Kamera',status='Offen',priority='Hoch',created_at=date.today())); s.commit()