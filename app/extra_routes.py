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
YearlyBudget=main.YearlyBudget
SiteBudget=main.SiteBudget
BudgetSettings=main.BudgetSettings

DA_SITES={'nurnberg','frankfurt','uberlingen','rostock','toulouse'}
DAV_SITES={'laupheim','gilching','dresden','colomiers','queretaro','craiova','nyirbator','debrecen'}
CONFIGURED_SITES=['Nürnberg','Frankfurt','Überlingen','Rostock','Toulouse','Hamburg','Laupheim','Gilching','Dresden','Colomiers','Queretaro','Craiova','Nyirbator','Debrecen']

def normalize_site(site):
    s=unicodedata.normalize('NFKD',str(site or '').strip()).encode('ascii','ignore').decode().casefold()
    return ' '.join(s.split())

def site_divisions(site):
    s=normalize_site(site)
    if s=='hamburg': return [('DA',0.5),('DAv',0.5)]
    if s in DA_SITES: return [('DA',1.0)]
    if s in DAV_SITES: return [('DAv',1.0)]
    return [('DAv',1.0)]

def project_year(p):
    return p.project_year or (p.start_date.year if p.start_date else None)

def in_period(value,year,quarter=None,month=None):
    if not value or value.year!=year:return False
    if month is not None:return value.month==month
    if quarter is not None:return (value.month-1)//3+1==quarter
    return True

def period_params(year,quarter,month):
    if quarter is not None and quarter not in (1,2,3,4):raise HTTPException(400,'Ungültiges Quartal')
    if month is not None and month not in range(1,13):raise HTTPException(400,'Ungültiger Monat')
    return year or date.today().year

def budget_record(site,year,configured,legacy,settings):
    if site is None:
        value=configured.get((None,year))
        if value is not None:return float(value)
        return float(settings.overall_budget or 0) if settings and year==date.today().year else 0.0
    value=configured.get((site,year))
    if value is not None:return float(value)
    return float(legacy.get(site,0)) if year==date.today().year else 0.0

def empty_site(site,budget):
    return {'site':site,'rooms':0.0,'budget':budget,'modernization_planned':0.0,'modernization_committed':0.0,'modernization_actual':0.0,'equipment_spent':0.0,'spent':0.0,'committed':0.0,'forecast':0.0,'available':budget,'utilization':0.0}

def add_financial(row,planned=0,committed=0,actual=0,equipment=0):
    row['modernization_planned']+=planned
    row['modernization_committed']+=committed
    row['modernization_actual']+=actual
    row['equipment_spent']+=equipment

def finalize_financial(row):
    row['spent']=row['modernization_actual']+row['equipment_spent']
    row['committed']=row['modernization_committed']+row['equipment_spent']
    row['forecast']=max(row['modernization_planned'],row['modernization_committed'],row['modernization_actual'])+row['equipment_spent']
    row['available']=row['budget']-row['committed']
    row['utilization']=round(row['committed']/row['budget']*100,1) if row['budget'] else 0
    for key in ('budget','modernization_planned','modernization_committed','modernization_actual','equipment_spent','spent','committed','forecast','available'):
        row[key]=round(float(row.get(key) or 0),2)
    return row

for route in list(app.routes):
    if isinstance(route,APIRoute) and route.path=='/api/budget-overview' and 'GET' in route.methods:app.routes.remove(route)

@app.get('/api/budget-overview')
def budget_overview(year:int|None=None,quarter:int|None=None,month:int|None=None,db:Session=Depends(main.db)):
    selected=period_params(year,quarter,month)
    configured={(x.site,x.year):float(x.budget or 0) for x in db.scalars(select(YearlyBudget)).all()}
    legacy={x.site:float(x.budget or 0) for x in db.scalars(select(SiteBudget)).all()}
    settings=db.scalar(select(BudgetSettings).limit(1))
    overall_budget=budget_record(None,selected,configured,legacy,settings)
    raw={site:empty_site(site,budget_record(site,selected,configured,legacy,settings)) for site in CONFIGURED_SITES}
    rooms=db.scalars(select(Room)).all()
    rooms_by_id={r.id:r for r in rooms}
    for room in rooms:
        site=room.site or 'Ohne Standort'
        if site not in raw:continue
        for division,factor in site_divisions(site):
            raw[site]['rooms']+=factor
    for eq in db.scalars(select(Equipment)).all():
        room=rooms_by_id.get(eq.room_id)
        if not room or room.site not in raw or not in_period(eq.purchase_date,selected,quarter,month):continue
        amount=float(eq.purchase_price or 0)
        for _,factor in site_divisions(room.site):raw[room.site]['equipment_spent']+=amount*factor
    for p in db.scalars(select(Modernization)).all():
        room=rooms_by_id.get(p.room_id)
        if not room or room.site not in raw or project_year(p)!=selected:continue
        value_date=p.start_date or p.completion_date or (date(p.project_year,12,31) if p.project_year else None)
        if (quarter is not None or month is not None) and not in_period(value_date,selected,quarter,month):continue
        planned=float(p.budget or 0);committed=float(p.commissioned or 0);actual=float(p.actual_cost or 0)
        for _,factor in site_divisions(room.site):add_financial(raw[room.site],planned*factor,committed*factor,actual*factor)
    base_sites=[]
    for site,row in raw.items():
        finalize_financial(row)
        for division,factor in site_divisions(site):
            split=dict(row);split['site']=site;split['division']=division;split['allocation']=factor
            for key in ('budget','modernization_planned','modernization_committed','modernization_actual','equipment_spent','spent','committed','forecast','available'):
                split[key]=round(split[key]*factor,2)
            split['rooms']=round(split['rooms']*factor,1)
            split['utilization']=round(split['committed']/split['budget']*100,1) if split['budget'] else 0
            base_sites.append(split)
    total={'budget':overall_budget,'modernization_planned':0.0,'modernization_committed':0.0,'modernization_actual':0.0,'equipment_spent':0.0,'spent':0.0,'committed':0.0,'forecast':0.0,'available':overall_budget,'utilization':0.0}
    for row in raw.values():
        for key in ('modernization_planned','modernization_committed','modernization_actual','equipment_spent','spent','committed','forecast'):
            total[key]+=row[key]
    total['available']=total['budget']-total['committed'];total['utilization']=round(total['committed']/total['budget']*100,1) if total['budget'] else 0
    divisions=[]
    for division in ('DA','DAv'):
        rows=[x for x in base_sites if x['division']==division]
        g={'division':division,'sites':len(rows),'rooms':sum(x['rooms'] for x in rows),'budget':0.0,'modernization_planned':0.0,'modernization_committed':0.0,'modernization_actual':0.0,'equipment_spent':0.0,'spent':0.0,'committed':0.0,'forecast':0.0,'available':0.0,'utilization':0.0}
        for row in rows:
            for key in ('budget','modernization_planned','modernization_committed','modernization_actual','equipment_spent','spent','committed','forecast','available'):g[key]+=row[key]
        g['utilization']=round(g['committed']/g['budget']*100,1) if g['budget'] else 0
        divisions.append(g)
    return {'year':selected,'quarter':quarter,'month':month,'total':total,'sites':base_sites,'divisions':divisions,'years':sorted({y for _,y in configured if y is not None},reverse=True) or [selected],'allocation_note':'DAs = Nürnberg, Frankfurt, Überlingen, Rostock, Toulouse + 50 % Hamburg. DAv = Laupheim, Gilching, Dresden, 50 % Hamburg, Colomiers, Queretaro, Craiova, Nyirbator, Debrecen.','site_count':len(CONFIGURED_SITES)}

@app.get('/api/budget-ledger')
def budget_ledger(year:int|None=None,quarter:int|None=None,month:int|None=None,division:str|None=None,site:str|None=None,db:Session=Depends(main.db)):
    selected=period_params(year,quarter,month);rows=[];rooms={r.id:r for r in db.scalars(select(Room)).all()}
    for eq in db.scalars(select(Equipment)).all():
        room=rooms.get(eq.room_id)
        if not room or not in_period(eq.purchase_date,selected,quarter,month):continue
        for d,factor in site_divisions(room.site):
            if (not division or d==division) and (not site or normalize_site(room.site)==normalize_site(site)):
                amount=float(eq.purchase_price or 0)*factor
                rows.append({'type':'equipment','date':eq.purchase_date.isoformat(),'room_id':room.id,'room':room.name,'site':room.site,'division':d,'allocation':factor,'description':eq.name,'category':eq.category,'amount':round(amount,2),'status':eq.status,'source_id':eq.id,'financial_state':'Ist'})
    for p in db.scalars(select(Modernization)).all():
        room=rooms.get(p.room_id);value_date=p.start_date or p.completion_date or (date(p.project_year,12,31) if p.project_year else None)
        if not room or project_year(p)!=selected or ((quarter is not None or month is not None) and not in_period(value_date,selected,quarter,month)):continue
        for d,factor in site_divisions(room.site):
            if (not division or d==division) and (not site or normalize_site(room.site)==normalize_site(site)):
                planned=float(p.budget or 0)*factor;committed=float(p.commissioned or 0)*factor;actual=float(p.actual_cost or 0)*factor
                amount=actual if actual>0 else committed if committed>0 else planned
                state='Ist' if actual>0 else 'Beauftragt' if committed>0 else 'Geplant'
                rows.append({'type':'modernization','date':value_date.isoformat() if value_date else None,'room_id':room.id,'room':room.name,'site':room.site,'division':d,'allocation':factor,'description':p.project_name,'category':'Modernisierung','amount':round(amount,2),'status':p.status,'source_id':p.id,'financial_state':state,'planned':round(planned,2),'committed':round(committed,2),'actual':round(actual,2)})
    rows.sort(key=lambda x:(x['date'] or '',x['site'] or '',x['room'] or '',x['description'] or ''),reverse=True)
    return {'year':selected,'quarter':quarter,'month':month,'division':division,'site':site,'count':len(rows),'total':round(sum(float(x['amount'] or 0) for x in rows),2),'rows':rows}

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
