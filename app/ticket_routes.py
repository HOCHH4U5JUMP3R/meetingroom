from collections import Counter
from datetime import date
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import main

app=main.app
Ticket=main.Ticket
Room=main.Room

def closed(status):
    return str(status or '').strip().casefold() in {'erledigt','geschlossen','abgeschlossen','closed','gelöst','geloest'}

def period_key(d):
    if not d:return None,None,None
    return str(d.year),f'{d.year}-Q{(d.month-1)//3+1}',f'{d.year}-{d.month:02d}'

@app.get('/api/ticket-analytics')
def ticket_analytics(year:int|None=None,quarter:int|None=None,month:int|None=None,db:Session=Depends(main.db)):
    rooms={r.id:r for r in db.scalars(select(Room)).all()}
    tickets=db.scalars(select(Ticket).order_by(Ticket.created_at,Ticket.id)).all()
    records=[]
    for t in tickets:
        room=rooms.get(t.room_id)
        d=t.created_at
        y,q,m=period_key(d)
        records.append({'id':t.id,'ticket_number':t.ticket_number,'subject':t.subject,'category':t.category or 'Sonstiges','status':t.status or 'Offen','priority':t.priority or 'Normal','created_at':d.isoformat() if d else None,'resolved_at':t.resolved_at.isoformat() if t.resolved_at else None,'room_id':t.room_id,'room':room.name if room else 'Unbekannter Raum','site':room.site if room else '','year':y,'quarter':q,'month':m})
    def matches(r):
        if year is not None and r['year']!=str(year):return False
        if quarter is not None and r['quarter']!=f'{year or date.today().year}-Q{quarter}':return False
        if month is not None and r['month']!=f'{year or date.today().year}-{month:02d}':return False
        return True
    filtered=[r for r in records if matches(r)]
    def counts(key):
        c=Counter((r.get(key) or 'Ohne Angabe') for r in filtered)
        return [{'label':k,'count':v} for k,v in sorted(c.items(),key=lambda x:(-x[1],x[0]))]
    by_year=counts('year');by_quarter=counts('quarter');by_month=counts('month');by_category=counts('category');by_room=counts('room')
    open_count=sum(not closed(r['status']) for r in filtered)
    return {'filters':{'year':year,'quarter':quarter,'month':month},'total':len(filtered),'open':open_count,'closed':len(filtered)-open_count,'high_priority':sum(str(r['priority']).casefold() in {'hoch','kritisch'} for r in filtered),'categories':by_category,'rooms':by_room,'years':by_year,'quarters':by_quarter,'months':by_month,'records':records}
