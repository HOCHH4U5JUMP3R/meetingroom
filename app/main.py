from pathlib import Path
from datetime import date
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, String, Integer, Float, Date, Text, ForeignKey, Boolean, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
engine = create_engine(f"sqlite:///{DATA/'meetingrooms.db'}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

class Room(Base):
    __tablename__ = 'rooms'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    site: Mapped[str] = mapped_column(String(100), default='')
    building: Mapped[str] = mapped_column(String(100), default='')
    floor: Mapped[str] = mapped_column(String(50), default='')
    room_number: Mapped[str] = mapped_column(String(50), default='')
    length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seats: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    specialty: Mapped[str] = mapped_column(Text, default='')
    category: Mapped[str] = mapped_column(String(100), default='')
    outlook_resource: Mapped[str] = mapped_column(String(200), default='')
    connections: Mapped[str] = mapped_column(Text, default='')
    owner: Mapped[str] = mapped_column(String(200), default='')
    host_name: Mapped[str] = mapped_column(String(200), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(50), default='Aktiv')
    last_modernization: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    equipment = relationship('Equipment', cascade='all, delete-orphan')
    rules = relationship('BookingRule', cascade='all, delete-orphan')
    projects = relationship('Modernization', cascade='all, delete-orphan')
    tickets = relationship('Ticket', cascade='all, delete-orphan')

class Equipment(Base):
    __tablename__ = 'equipment'
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80), default='')
    manufacturer: Mapped[str] = mapped_column(String(80), default='')
    model: Mapped[str] = mapped_column(String(120), default='')
    serial: Mapped[str] = mapped_column(String(120), default='')
    size_inches: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mounting: Mapped[str] = mapped_column(String(80), default='')
    status: Mapped[str] = mapped_column(String(50), default='Aktiv')
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default='')

class BookingRule(Base):
    __tablename__ = 'booking_rules'
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id', ondelete='CASCADE'), index=True)
    entitlement: Mapped[str] = mapped_column(String(100), default='Alle Mitarbeiter')
    group_name: Mapped[str] = mapped_column(String(200), default='')
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approver: Mapped[str] = mapped_column(String(200), default='')
    approval_type: Mapped[str] = mapped_column(String(100), default='Keine Genehmigung')
    notes: Mapped[str] = mapped_column(Text, default='')

class Modernization(Base):
    __tablename__ = 'modernizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id', ondelete='CASCADE'), index=True)
    project_name: Mapped[str] = mapped_column(String(200))
    project_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='Idee')
    budget: Mapped[float] = mapped_column(Float, default=0)
    commissioned: Mapped[float] = mapped_column(Float, default=0)
    actual_cost: Mapped[float] = mapped_column(Float, default=0)
    supplier: Mapped[str] = mapped_column(String(200), default='')
    responsible: Mapped[str] = mapped_column(String(200), default='')
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    order_number: Mapped[str] = mapped_column(String(100), default='')
    notes: Mapped[str] = mapped_column(Text, default='')

class Ticket(Base):
    __tablename__ = 'tickets'
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id', ondelete='CASCADE'), index=True)
    ticket_number: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(80), default='Sonstiges')
    status: Mapped[str] = mapped_column(String(50), default='Offen')
    priority: Mapped[str] = mapped_column(String(50), default='Normal')
    created_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resolved_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    responsible: Mapped[str] = mapped_column(String(200), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    notes: Mapped[str] = mapped_column(Text, default='')

Base.metadata.create_all(engine)

app = FastAPI(title='Meetingraumverwaltung', version='1.0.0')
app.mount('/static', StaticFiles(directory=BASE/'app'/'static'), name='static')

def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()

def dump(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}

def model_for(kind):
    return {'rooms':Room,'equipment':Equipment,'rules':BookingRule,'modernizations':Modernization,'tickets':Ticket}[kind]

@app.get('/')
def index(): return FileResponse(BASE/'app'/'static'/'index.html')

@app.get('/health')
def health(): return {'status': 'ok'}

@app.get('/api/rooms')
def rooms(db:Session=Depends(db)):
    return [dump(x) for x in db.scalars(select(Room).order_by(Room.site,Room.building,Room.floor,Room.name)).all()]

@app.get('/api/rooms/{room_id}')
def room_detail(room_id:int, db:Session=Depends(db)):
    r=db.get(Room,room_id)
    if not r: raise HTTPException(404,'Raum nicht gefunden')
    data=dump(r)
    data['area']=round((r.length or 0)*(r.width or 0),2) if r.length and r.width else None
    data['volume']=round((r.length or 0)*(r.width or 0)*(r.height or 0),2) if r.length and r.width and r.height else None
    data['equipment']=[dump(x) for x in r.equipment]
    data['rules']=[dump(x) for x in r.rules]
    data['modernizations']=[dump(x) for x in r.projects]
    data['tickets']=[dump(x) for x in sorted(r.tickets,key=lambda x:x.id,reverse=True)]
    return data

@app.get('/api/dashboard')
def dashboard(db:Session=Depends(db)):
    rows=db.scalars(select(Modernization)).all()
    return {
      'rooms':db.scalar(select(func.count(Room.id))) or 0,
      'open_tickets':db.scalar(select(func.count(Ticket.id)).where(Ticket.status.in_(['Offen','In Bearbeitung']))) or 0,
      'budget':sum(x.budget or 0 for x in rows),
      'commissioned':sum(x.commissioned or 0 for x in rows),
      'actual':sum(x.actual_cost or 0 for x in rows),
      'available':sum((x.budget or 0)-(x.commissioned or 0) for x in rows),
    }

class RoomIn(BaseModel):
    name:str; site:str=''; building:str=''; floor:str=''; room_number:str=''; length:Optional[float]=None; width:Optional[float]=None; height:Optional[float]=None; seats:Optional[int]=None; specialty:str=''; category:str=''; outlook_resource:str=''; connections:str=''; owner:str=''; host_name:str=''; notes:str=''; status:str='Aktiv'; last_modernization:Optional[date]=None
class EquipmentIn(BaseModel):
    name:str; category:str=''; manufacturer:str=''; model:str=''; serial:str=''; size_inches:Optional[float]=None; mounting:str=''; status:str='Aktiv'; purchase_date:Optional[date]=None; notes:str=''
class RuleIn(BaseModel):
    entitlement:str='Alle Mitarbeiter'; group_name:str=''; approval_required:bool=False; approver:str=''; approval_type:str='Keine Genehmigung'; notes:str=''
class ModernizationIn(BaseModel):
    project_name:str; project_year:Optional[int]=None; status:str='Idee'; budget:float=0; commissioned:float=0; actual_cost:float=0; supplier:str=''; responsible:str=''; start_date:Optional[date]=None; planned_end:Optional[date]=None; completion_date:Optional[date]=None; order_number:str=''; notes:str=''
class TicketIn(BaseModel):
    ticket_number:str; subject:str; category:str='Sonstiges'; status:str='Offen'; priority:str='Normal'; created_at:Optional[date]=None; resolved_at:Optional[date]=None; responsible:str=''; description:str=''; notes:str=''

@app.post('/api/rooms')
def create_room(x:RoomIn, db:Session=Depends(db)):
    if db.scalar(select(Room).where(Room.name==x.name)): raise HTTPException(409,'Raumname existiert bereits')
    r=Room(**x.model_dump()); db.add(r); db.commit(); db.refresh(r); return dump(r)
@app.put('/api/rooms/{rid}')
def update_room(rid:int,x:RoomIn,db:Session=Depends(db)):
    r=db.get(Room,rid)
    if not r: raise HTTPException(404,'Raum nicht gefunden')
    for k,v in x.model_dump().items(): setattr(r,k,v)
    db.commit(); db.refresh(r); return dump(r)

@app.post('/api/rooms/{rid}/{kind}')
def create_child(rid:int,kind:str,payload:dict,db:Session=Depends(db)):
    r=db.get(Room,rid)
    if not r: raise HTTPException(404,'Raum nicht gefunden')
    if kind not in ['equipment','rules','modernizations','tickets']: raise HTTPException(400,'Ungültiger Bereich')
    cls=model_for(kind)
    data=dict(payload); data['room_id']=rid
    obj=cls(**data); db.add(obj); db.commit(); db.refresh(obj); return dump(obj)
@app.put('/api/{kind}/{oid}')
def update_child(kind:str,oid:int,payload:dict,db:Session=Depends(db)):
    if kind not in ['equipment','rules','modernizations','tickets']: raise HTTPException(400,'Ungültiger Bereich')
    obj=db.get(model_for(kind),oid)
    if not obj: raise HTTPException(404,'Eintrag nicht gefunden')
    for k,v in payload.items():
        if hasattr(obj,k) and k!='id' and k!='room_id': setattr(obj,k,v)
    db.commit(); db.refresh(obj); return dump(obj)
@app.delete('/api/{kind}/{oid}')
def delete_child(kind:str,oid:int,db:Session=Depends(db)):
    if kind not in ['equipment','rules','modernizations','tickets']: raise HTTPException(400,'Ungültiger Bereich')
    obj=db.get(model_for(kind),oid)
    if not obj: raise HTTPException(404,'Eintrag nicht gefunden')
    db.delete(obj); db.commit(); return {'ok':True}

# Optional starter room for a fresh installation; remove this block if a completely empty DB is desired.
with SessionLocal() as s:
    if not s.scalar(select(Room)):
        r=Room(name='Beispielraum 101',site='Nürnberg',building='Gebäude A',floor='EG',room_number='101',seats=12,category='Besprechungsraum',owner='Raumverantwortlicher',status='Aktiv',connections='HDMI · USB-C · Miracast')
        s.add(r); s.commit(); s.refresh(r)
        s.add_all([
            Equipment(room_id=r.id,name='Hauptdisplay',category='Display',manufacturer='Samsung',model='Beispielmodell',size_inches=86,mounting='Wand',status='Aktiv'),
            Equipment(room_id=r.id,name='VC-System',category='VC-System',manufacturer='Crestron',model='Beispielmodell',status='Aktiv')
        ])
        s.add(BookingRule(room_id=r.id,entitlement='Alle Mitarbeiter',approval_required=False,approval_type='Keine Genehmigung'))
        s.add(Modernization(room_id=r.id,project_name='Beispiel Modernisierung 2026',project_year=2026,status='Planung',budget=15000,commissioned=8500,actual_cost=0))
        s.add(Ticket(room_id=r.id,ticket_number='12345',subject='Beispiel: Kamera ohne Bild',category='Kamera',status='Offen',priority='Hoch',created_at=date.today()))
        s.commit()
