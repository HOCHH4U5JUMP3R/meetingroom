from datetime import date
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main

app = main.app
Room = main.Room
Equipment = main.Equipment
Modernization = main.Modernization
Ticket = main.Ticket
YearlyBudget = main.YearlyBudget
BudgetSettings = main.BudgetSettings
SessionLocal = main.SessionLocal
DA_SITES = main.DA_SITES

def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()

def division_for(site):
    return 'DA' if str(site or '').strip().casefold() in DA_SITES else 'DAv'

def project_year(p):
    return p.project_year or (p.start_date.year if p.start_date else None)

def in_period(value, year, quarter=None, month=None):
    if not value or value.year != year:
        return False
    if month is not None:
        return value.month == month
    if quarter is not None:
        return (value.month - 1) // 3 + 1 == quarter
    return True

def period_params(year, quarter, month):
    if quarter is not None and quarter not in (1, 2, 3, 4):
        raise HTTPException(400, 'Ungültiges Quartal')
    if month is not None and month not in range(1, 13):
        raise HTTPException(400, 'Ungültiger Monat')
    return year or date.today().year

@app.get('/api/budget-ledger')
def budget_ledger(year: int | None = None, quarter: int | None = None, month: int | None = None, division: str | None = None, site: str | None = None, db: Session = Depends(db)):
    selected = period_params(year, quarter, month)
    rows = []
    rooms = {r.id: r for r in db.scalars(select(Room)).all()}
    for eq in db.scalars(select(Equipment)).all():
        room = rooms.get(eq.room_id)
        if room and in_period(eq.purchase_date, selected, quarter, month):
            d = division_for(room.site)
            if (not division or d == division) and (not site or room.site == site):
                rows.append({'type':'equipment','date':eq.purchase_date.isoformat(),'room_id':room.id,'room':room.name,'site':room.site,'division':d,'description':eq.name,'category':eq.category,'amount':eq.purchase_price or 0,'status':eq.status,'source_id':eq.id})
    for p in db.scalars(select(Modernization)).all():
        room = rooms.get(p.room_id)
        value_date = p.start_date or p.completion_date or (date(p.project_year,12,31) if p.project_year else None)
        if room and project_year(p) == selected and in_period(value_date, selected, quarter, month):
            d = division_for(room.site)
            if (not division or d == division) and (not site or room.site == site):
                amount = p.actual_cost or p.commissioned or p.budget or 0
                rows.append({'type':'modernization','date':value_date.isoformat() if value_date else None,'room_id':room.id,'room':room.name,'site':room.site,'division':d,'description':p.project_name,'category':'Modernisierung','amount':amount,'status':p.status,'source_id':p.id})
    rows.sort(key=lambda x:(x['date'] or '', x['site'] or '', x['room'] or '', x['description'] or ''), reverse=True)
    return {'year':selected,'quarter':quarter,'month':month,'division':division,'site':site,'count':len(rows),'total':sum(float(x['amount'] or 0) for x in rows),'rows':rows}

@app.get('/api/dashboard-summary')
def dashboard_summary(year: int | None = None, db: Session = Depends(db)):
    selected = year or date.today().year
    rooms = db.scalars(select(Room)).all()
    equipment = db.scalars(select(Equipment)).all()
    projects = db.scalars(select(Modernization)).all()
    tickets = db.scalars(select(Ticket)).all()
    open_status = {'offen','in bearbeitung','neu','wiedereröffnet'}
    open_tickets = [t for t in tickets if str(t.status or '').strip().casefold() in open_status]
    critical = [t for t in open_tickets if any(x in str(t.priority or '').casefold() for x in ('krit','hoch'))]
    aging_equipment = [e for e in equipment if e.purchase_date and (date.today() - e.purchase_date).days >= 6 * 365]
    overdue = [p for p in projects if p.planned_end and p.planned_end < date.today() and str(p.status or '').casefold() not in ('fertig','abgeschlossen')]
    budget = main.budget_overview(year=selected, db=db)
    recommendations = []
    if aging_equipment:
        recommendations.append({'type':'equipment_age','severity':'warning','title':f'{len(aging_equipment)} Geräte sind mindestens 6 Jahre alt.','count':len(aging_equipment)})
    if len(open_tickets) >= 5:
        recommendations.append({'type':'tickets','severity':'danger','title':f'{len(open_tickets)} offene Tickets erfordern Aufmerksamkeit.','count':len(open_tickets)})
    if overdue:
        recommendations.append({'type':'modernization','severity':'danger','title':f'{len(overdue)} Modernisierungsprojekte sind überfällig.','count':len(overdue)})
    if budget['total']['budget'] and budget['total']['committed'] > budget['total']['budget']:
        recommendations.append({'type':'budget','severity':'danger','title':'Das Jahresbudget ist bereits überbucht.','count':1})
    return {'year':selected,'rooms':len(rooms),'equipment':len(equipment),'open_tickets':len(open_tickets),'critical_tickets':len(critical),'modernizations':len(projects),'modernizations_active':sum(str(p.status or '').casefold() not in ('fertig','abgeschlossen') for p in projects),'aging_equipment':len(aging_equipment),'overdue_modernizations':len(overdue),'budget':budget,'recommendations':recommendations}
