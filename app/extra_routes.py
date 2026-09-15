from datetime import date
import unicodedata
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.routing import APIRoute
from . import main

app=main.app
Room=main.Room
Equipment=main.Equipment
Modernization=main.Modernization
Ticket=main.Ticket
SessionLocal=main.SessionLocal

DA_SITES={'nurnberg','frankfurt','uberlingen','rostock','toulouse'}
DAV_SITES={'lau pheim','lauph​​eim','gilching','dresden','colomiers','queretaro','craiova','nyirbator','debrecen'}
CONFIGURED_SITES=['Nürnberg','Frankfurt','Überlingen','Rostock','Toulouse','Hamburg','Laupheim','Gilching','Dresden','Colomiers','Queretaro','Craiova','Nyirbator','Debrecen']

def normalize_site(site):
    s=unicodedata.normalize('NFKD',str(site or '').strip()).encode('ascii','ignore').decode().casefold()
    return ' '.join(s.split())

def site_divisions(site):
    s=normalize_site(site)
    if s=='hamburg': return [('DA',0.5),('DAv',0.5)]
    if s in DA_SITES: return [('DA',1.0)]
    if s in {'lau pheim','laupheim','gilching','dresden','colomiers','queretaro','craiova','nyirbator','debrecen'}: return [('DAv',1.0)]
    return [('DAv',1.0)]

def division_for(site): return site_divisions(site)[0][0]
def project_year(p): return p.project_year or (p.start_date.year if p.start_date else None)
def in_period(value,year,quarter=None,month=None):
    if not value or value.year!=year:return False
    if month is not None:return value.month==month
    if quarter is not None:return (value.month-1)//3+1==quarter
    return True

def period_params(year,quarter,month):
    if quarter is not None and quarter not in (1,2,3,4):raise HTTPException(400,'Ungültiges Quartal')
    if month is not None and month not in range(1,13):raise HTTPException(400,'Ungültiger Monat')
    return year or date.today().year

for route in list(app.routes):
    if isinstance(route,APIRoute) and route.path=='/api/budget-overview' and 'GET' in route.methods:app.routes.remove(route)

@app.get('/api/budget-overview')
def budget_overview(year:int|None=None,quarter:int|None=None,month:int|None=None,db:Session=Depends(main.db)):
    selected=period_params(year,quarter,month)
    base=main.budget_overview(year=selected,quarter=quarter,month=month,db=db)
    source={normalize_site(x.get('site')):x for x in base.get('sites',[])}
    sites=[]
    for configured_site in CONFIGURED_SITES:
        x=source.get(normalize_site(configured_site),{'site':configured_site,'rooms':0,'budget':0,'modernization_planned':0,'modernization_commissioned':0,'modernization_spent':0,'equipment_spent':0})
        for division,factor in site_divisions(configured_site):
            row=dict(x);row['site']=configured_site;row['division']=division;row['allocation']=factor
            for key in ('budget','modernization_planned','modernization_commissioned','modernization_spent','equipment_spent','spent','committed','forecast','available'):row[key]=round(float(row.get(key) or 0)*factor,2)
            row['rooms']=round(float(row.get('rooms') or 0)*factor,1)
            row['utilization']=round(row['committed']/row['budget']*100,1) if row['budget'] else 0
            sites.append(row)
    divisions=[]
    for division in ('DA','DAv'):
        rows=[x for x in sites if x['division']==division];budget=sum(x['budget'] for x in rows);committed=sum(x['committed'] for x in rows)
        divisions.append({'division':division,'sites':len(rows),'rooms':sum(x['rooms'] for x in rows),'budget':budget,'modernization_planned':sum(x['modernization_planned'] for x in rows),'modernization_commissioned':sum(x['modernization_commissioned'] for x in rows),'modernization_spent':sum(x['modernization_spent'] for x in rows),'equipment_spent':sum(x['equipment_spent'] for x in rows),'spent':sum(x['spent'] for x in rows),'committed':committed,'forecast':sum(x['forecast'] for x in rows),'available':sum(x['available'] for x in rows),'utilization':round(committed/budget*100,1) if budget else 0})
    return {**base,'sites':sites,'divisions':divisions,'allocation_note':'Standortzuordnung: DA = Nürnberg, Frankfurt, Überlingen, Rostock, Toulouse + 50 % Hamburg. DAv = Laupheim, Gilching, Dresden, 50 % Hamburg, Colomiers, Queretaro, Craiova, Nyirbator, Debrecen.','site_count':len(CONFIGURED_SITES)}

@app.get('/api/budget-ledger')
def budget_ledger(year:int|None=None,quarter:int|None=None,month:int|None=None,division:str|None=None,site:str|None=None,db:Session=Depends(main.db)):
    selected=period_params(year,quarter,month);rows=[];rooms={r.id:r for r in db.scalars(select(Room)).all()}
    for eq in db.scalars(select(Equipment)).all():
        room=rooms.get(eq.room_id)
        if not room or not in_period(eq.purchase_date,selected,quarter,month):continue
        for d,factor in site_divisions(room.site):
            if (not division or d==division) and (not site or normalize_site(room.site)==normalize_site(site)):
                rows.append({'type':'equipment','date':eq.purchase_date.isoformat(),'room_id':room.id,'room':room.name,'site':room.site,'division':d,'allocation':factor,'description':eq.name,'category':eq.category,'amount':round((eq.purchase_price or 0)*factor,2),'status':eq.status,'source_id':eq.id})
    for p in db.scalars(select(Modernization)).all():
        room=rooms.get(p.room_id);value_date=p.start_date or p.completion_date or (date(p.project_year,12,31) if p.project_year else None)
        if not room or project_year(p)!=selected or ((quarter is not None or month is not None) and not in_period(value_date,selected,quarter,month)):continue
        for d,factor in site_divisions(room.site):
            if (not division or d==division) and (not site or normalize_site(room.site)==normalize_site(site)):
                amount=(p.actual_cost or p.commissioned or p.budget or 0)*factor
                rows.append({'type':'modernization','date':value_date.isoformat() if value_date else None,'room_id':room.id,'room':room.name,'site':room.site,'division':d,'allocation':factor,'description':p.project_name,'category':'Modernisierung','amount':round(amount,2),'status':p.status,'source_id':p.id})
    rows.sort(key=lambda x:(x['date'] or '',x['site'] or '',x['room'] or '',x['description'] or ''),reverse=True)
    return {'year':selected,'quarter':quarter,'month':month,'division':division,'site':site,'count':len(rows),'total':sum(float(x['amount'] or 0) for x in rows),'rows':rows}

@app.get('/api/dashboard-summary')
def dashboard_summary(year:int|None=None,db:Session=Depends(main.db)):
    selected=year or date.today().year;rooms=db.scalars(select(Room)).all();equipment=db.scalars(select(Equipment)).all();projects=db.scalars(select(Modernization)).all();tickets=db.scalars(select(Ticket)).all()
    open_status={'offen','in bearbeitung','neu','wiedereröffnet'};open_tickets=[t for t in tickets if str(t.status or '').strip().casefold() in open_status];critical=[t for t in open_tickets if any(x in str(t.priority or '').casefold() for x in ('krit','hoch'))]
    aging=[e for e in equipment if e.purchase_date and (date.today()-e.purchase_date).days>=6*365];overdue=[p for p in projects if p.planned_end and p.planned_end<date.today() and str(p.status or '').casefold() not in ('fertig','abgeschlossen')];budget=budget_overview(year=selected,db=db);recommendations=[]
    if aging:recommendations.append({'type':'equipment_age','severity':'warning','title':f'{len(aging)} Geräte sind mindestens 6 Jahre alt.','count':len(aging)})
    if len(open_tickets)>=5:recommendations.append({'type':'tickets','severity':'danger','title':f'{len(open_tickets)} offene Tickets erfordern Aufmerksamkeit.','count':len(open_tickets)})
    if overdue:recommendations.append({'type':'modernization','severity':'danger','title':f'{len(overdue)} Modernisierungsprojekte sind überfällig.','count':len(overdue)})
    if budget['total']['budget'] and budget['total']['committed']>budget['total']['budget']:recommendations.append({'type':'budget','severity':'danger','title':'Das Jahresbudget ist bereits überbucht.','count':1})
    return {'year':selected,'rooms':len(rooms),'equipment':len(equipment),'open_tickets':len(open_tickets),'critical_tickets':len(critical),'modernizations':len(projects),'modernizations_active':sum(str(p.status or '').casefold() not in ('fertig','abgeschlossen') for p in projects),'aging_equipment':len(aging),'overdue_modernizations':len(overdue),'budget':budget,'recommendations':recommendations}
