const searchInput = document.querySelector('#roomSearch');
const filterContainer = document.querySelector('#siteFilters');
const groupContainer = document.querySelector('#roomGroups');
const emptyState = document.querySelector('#overviewEmpty');
const errorState = document.querySelector('#overviewError');
let allRooms = [];
let selectedSite = '';

const esc = v => String(v == null || v === '' ? '–' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const siteFor = r => r.site || 'Ohne Standort';
const status = r => String(r.status || 'Aktiv').toLowerCase();
const isBad = r => status(r).includes('störung') || status(r).includes('außer') || Number(r.open_ticket_count || 0) >= 3;
const isWarn = r => !isBad(r) && (status(r).includes('modern') || Number(r.open_ticket_count || 0) > 0);
const roomLocation = r => [r.building, r.floor && `Etage ${r.floor}`, r.room_number && `Raum ${r.room_number}`].filter(Boolean).join(' · ') || 'Keine Standortdaten';

function filteredRooms() {
  const q = searchInput.value.trim().toLowerCase();
  return allRooms.filter(r => {
    if (selectedSite && siteFor(r) !== selectedSite) return false;
    return [r.name,r.site,r.building,r.floor,r.room_number,r.category,r.connections,r.owner,r.host_name].join(' ').toLowerCase().includes(q);
  });
}

function renderDashboardMetrics() {
  const total = allRooms.length;
  const open = allRooms.reduce((n,r) => n + Number(r.open_ticket_count || 0), 0);
  const bad = allRooms.filter(isBad).length;
  const warn = allRooms.filter(isWarn).length;
  const ok = Math.max(0,total-bad-warn);
  document.querySelector('#kpiRooms').textContent = total;
  document.querySelector('#kpiTickets').textContent = open;
  document.querySelector('#kpiTicketHint').textContent = open ? 'Handlungsbedarf vorhanden' : 'alles ruhig';
  document.querySelector('#statusOk').textContent = ok;
  document.querySelector('#statusWarn').textContent = warn;
  document.querySelector('#statusBad').textContent = bad;
  document.querySelector('#statusOkBar').style.width = `${total ? ok/total*100 : 0}%`;
  document.querySelector('#statusWarnBar').style.width = `${total ? warn/total*100 : 0}%`;
  document.querySelector('#statusBadBar').style.width = `${total ? bad/total*100 : 0}%`;
}

async function loadBudget() {
  try {
    const res = await fetch('/api/budget-overview?year=2026');
    if (!res.ok) return;
    const data = await res.json();
    const t = data.total || data;
    const budget = Number(t.budget || 0), spent = Number(t.spent || 0), planned = Number(t.planned || 0);
    document.querySelector('#kpiBudget').textContent = budget.toLocaleString('de-DE',{maximumFractionDigits:0}) + ' €';
    const used = budget ? Math.min(100,(spent+planned)/budget*100) : 0;
    document.querySelector('#kpiBudgetHint').textContent = `${used.toFixed(0)} % verplant / verbraucht`;
    document.querySelector('#budgetHero').textContent = `${(budget-spent-planned).toLocaleString('de-DE',{maximumFractionDigits:0})} €`;
    document.querySelector('#budgetSub').textContent = `${(spent+planned).toLocaleString('de-DE',{maximumFractionDigits:0})} € verplant / verbraucht von ${budget.toLocaleString('de-DE',{maximumFractionDigits:0})} €`;
    document.querySelector('#budgetProgress').style.width = `${used}%`;
  } catch (_) {}
}

async function loadExtendedMetrics() {
  let projects = 0;
  const attention = [];
  await Promise.all(allRooms.slice(0,120).map(async r => {
    try {
      const x = await fetch(`/api/rooms/${r.id}`).then(v=>v.json());
      projects += (x.modernizations || []).length;
      if ((x.tickets || []).some(t => ['Offen','In Bearbeitung'].includes(t.status)) || isBad(x)) attention.push(x);
    } catch (_) {}
  }));
  document.querySelector('#kpiModern').textContent = projects;
  attention.sort((a,b)=>(b.open_ticket_count||0)-(a.open_ticket_count||0));
  const list = document.querySelector('#attentionList');
  if (!attention.length) list.innerHTML = '<div class="attention-good"><strong>Alles im grünen Bereich</strong><span>Aktuell wurden keine kritischen Räume erkannt.</span></div>';
  else list.innerHTML = attention.slice(0,6).map(r => `<a class="attention-row" href="/static/room-detail.html?id=${encodeURIComponent(r.id)}"><span class="attention-icon">!</span><div><strong>${esc(r.name)}</strong><small>${esc(roomLocation(r))}</small></div><span class="attention-reason">${Number(r.open_ticket_count||0)} offene Tickets</span><b>›</b></a>`).join('');
}

function renderFilters() {
  const sites = [...new Set(allRooms.map(siteFor))].sort();
  filterContainer.innerHTML = '';
  ['Alle',...sites].forEach(site => {
    const b = document.createElement('button'); b.type='button'; b.className=`site-filter ${(!selectedSite && site==='Alle') || site===selectedSite ? 'active':''}`; b.textContent=site;
    b.onclick=()=>{selectedSite=site==='Alle'?'':site;renderFilters();renderRooms();}; filterContainer.appendChild(b);
  });
}

function renderRooms() {
  const rooms = filteredRooms();
  document.querySelector('#roomResultText').textContent = `${rooms.length} ${rooms.length===1?'Raum':'Räume'}${selectedSite ? ` · ${selectedSite}` : ' · alle Standorte'}`;
  emptyState.hidden = rooms.length !== 0;
  groupContainer.innerHTML='';
  const grouped={}; rooms.forEach(r=>(grouped[siteFor(r)] ||= []).push(r));
  Object.keys(grouped).sort().forEach(site=>{
    const section=document.createElement('div'); section.className='v2-site-section';
    section.innerHTML=`<div class="v2-site-title"><span>${esc(site)}</span><small>${grouped[site].length} Räume</small></div><div class="v2-room-grid-inner"></div>`;
    const grid=section.querySelector('.v2-room-grid-inner');
    grouped[site].forEach(r=>{
      const state=isBad(r)?'danger':isWarn(r)?'warning':'success';
      const image=r.image_url?`<img src="${esc(r.image_url)}" alt="Raumbild ${esc(r.name)}">`:'<div class="room-placeholder">⌂</div>';
      const card=document.createElement('a'); card.className='v2-room-card'; card.href=`/static/room-detail.html?id=${encodeURIComponent(r.id)}`;
      card.innerHTML=`<div class="v2-room-image">${image}<span class="room-health ${state}">${state==='success'?'OK':state==='warning'?'Hinweis':'Störung'}</span></div><div class="v2-room-body"><div class="v2-room-title"><strong>${esc(r.name)}</strong><span>›</span></div><p>${esc(roomLocation(r))}</p><div class="v2-room-meta"><span>◷ ${esc(r.seats ?? '–')} Plätze</span><span>⚑ ${Number(r.open_ticket_count||0)} offen</span></div><div class="v2-room-footer"><span>${esc(r.category || 'Meetingraum')}</span><span>${esc(r.owner || 'Kein Verantwortlicher')}</span></div></div>`;
      grid.appendChild(card);
    });
    groupContainer.appendChild(section);
  });
}

async function loadRooms() {
  try {
    const res=await fetch('/api/rooms',{headers:{Accept:'application/json'}}); if(!res.ok) throw new Error(`Räume konnten nicht geladen werden (HTTP ${res.status}).`);
    allRooms=await res.json(); if(!Array.isArray(allRooms)) throw new Error('Ungültiges Raumdatenformat.');
    errorState.hidden=true; renderFilters(); renderDashboardMetrics(); renderRooms(); loadBudget(); loadExtendedMetrics();
  } catch(e){ console.error(e); errorState.textContent=e.message; errorState.hidden=false; emptyState.hidden=true; }
}
searchInput.addEventListener('input',renderRooms);
loadRooms();
