from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import main

app=main.app
Modernization=main.Modernization

with main.engine.begin() as connection:
    info=list(connection.exec_driver_sql('PRAGMA table_info(modernizations)'))
    room_col=next((row for row in info if row[1]=='room_id'),None)
    if room_col is not None and room_col[3]==1:
        connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
        connection.exec_driver_sql('ALTER TABLE modernizations RENAME TO modernizations_old')
        connection.exec_driver_sql('''CREATE TABLE modernizations (id INTEGER NOT NULL PRIMARY KEY,room_id INTEGER,project_name VARCHAR(200) NOT NULL,project_year INTEGER,status VARCHAR(50) DEFAULT 'Idee',budget FLOAT DEFAULT 0,commissioned FLOAT DEFAULT 0,actual_cost FLOAT DEFAULT 0,supplier VARCHAR(200) DEFAULT '',responsible VARCHAR(200) DEFAULT '',start_date DATE,planned_end DATE,completion_date DATE,order_number VARCHAR(100) DEFAULT '',notes TEXT DEFAULT '',FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE)''')
        connection.exec_driver_sql('''INSERT INTO modernizations (id,room_id,project_name,project_year,status,budget,commissioned,actual_cost,supplier,responsible,start_date,planned_end,completion_date,order_number,notes) SELECT id,room_id,project_name,project_year,status,budget,commissioned,actual_cost,supplier,responsible,start_date,planned_end,completion_date,order_number,notes FROM modernizations_old''')
        connection.exec_driver_sql('DROP TABLE modernizations_old')
        connection.exec_driver_sql('CREATE INDEX IF NOT EXISTS ix_modernizations_room_id ON modernizations(room_id)')
        connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    main.Modernization.__table__.c.room_id.nullable=True

@app.get('/api/modernizations')
def list_modernizations(db:Session=Depends(main.db)):
    return [main.dump(x) for x in db.scalars(select(Modernization).order_by(Modernization.project_year.desc(),Modernization.id.desc())).all()]

@app.get('/api/modernizations/{oid}')
def get_modernization(oid:int,db:Session=Depends(main.db)):
    obj=db.get(Modernization,oid)
    if not obj:raise HTTPException(404,'Modernisierungsprojekt nicht gefunden')
    return main.dump(obj)

@app.post('/api/modernizations')
def create_standalone_modernization(payload:dict,db:Session=Depends(main.db)):
    allowed=['project_name','project_year','status','budget','commissioned','actual_cost','supplier','responsible','start_date','planned_end','completion_date','order_number','notes']
    data={k:payload.get(k) for k in allowed}
    if not str(data.get('project_name') or '').strip():raise HTTPException(422,'Projektname ist erforderlich')
    obj=Modernization(room_id=None,project_name=str(data['project_name']).strip(),project_year=data['project_year'],status=data.get('status') or 'Idee',budget=float(data.get('budget') or 0),commissioned=float(data.get('commissioned') or 0),actual_cost=float(data.get('actual_cost') or 0),supplier=data.get('supplier') or '',responsible=data.get('responsible') or '',start_date=data.get('start_date') or None,planned_end=data.get('planned_end') or None,completion_date=data.get('completion_date') or None,order_number=data.get('order_number') or '',notes=data.get('notes') or '')
    db.add(obj);db.commit();db.refresh(obj);return main.dump(obj)
