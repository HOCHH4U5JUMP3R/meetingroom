const q=document.querySelector('#q'),list=document.querySelector('#list'),filters=document.querySelector('#filters');let projects=[],selected='';
const esc=v=>String(v??'–').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const euro=v=>Number(v||0).toLocaleString('de-DE',{style:'currency',currency:'EUR',maximumFractionDigits:0});
const n=v=>String(v||'').toLowerCase();
function year(p){return p.project_year||(p.start_date?new Date(p.start_date).getFullYear():null)}
function badge(v){const s=n(v),c=s.includes('fertig')||s.includes('abgeschlossen')?'badge-success':s.includes('störung')||s.includes('abgelehnt')?'badge-danger':'badge-warning';return `<span class="badge ${c}">${esc(v||'–')}</span>`}
function state(p){const b=Number(p.budget||0),c=Number(p.commissioned||0),a=Number(p.actual_cost||0);return a>0?'Ist':c>0?'Beauftragt':'Geplant'}
function pct(v){return Number(v||0).toLocaleString('de-DE',{maximumFractionDigits:0})+' %'}
function variance(p){const b=Number(p.budget||0),a=Number(p.actual_cost||0);return b&&a?(a/b*100):0}
async function load(){
  const rooms=await fetch('/api/rooms').then(r=>r.json());
  const d=await Promise.all(rooms.map(r=>fetch(`/api/rooms/${r.id}`).then(x=>x.ok?x.json():null).catch(()=>null)));
  projects=d.filter(Boolean).flatMap(r=>(r.modernizations||[]).map(p=>({...p,room:r})));
  renderKpis();renderFilters();render();
}
function renderKpis(){
  const planned=projects.reduce((s,p)=>s+Number(p.budget||0),0),commissioned=projects.reduce((s,p)=>s+Number(p.commissioned||0),0),spent=projects.reduce((s,p)=>s+Number(p.actual_cost||0),0);
  document.querySelector('#count').textContent=projects.length;document.querySelector('#planned').textContent=euro(planned);document.querySelector('#commissioned').textContent=euro(commissioned);document.querySelector('#spent').textContent=euro(spent);
}
function renderFilters(){
  const years=[...new Set(projects.map(year).filter(Boolean))].sort((a,b)=>a-b);
  filters.innerHTML='<button class="site-filter active" data-v="">Alle</button>'+years.map(y=>`<button class="site-filter" data-v="${y}">${y}</button>`).join('')+['__active','__overdue','__risk'].map(v=>`<button class="site-filter" data-v="${v}">${v==='__active'?'In Arbeit':v==='__overdue'?'Überfällig':'Budgetrisiko'}</button>`).join('');
  filters.querySelectorAll('button').forEach(b=>b.onclick=()=>{selected=b.dataset.v;filters.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));render()});
}
function render(){
  const term=n(q.value),now=Date.now();
  const rows=projects.filter(p=>{const y=String(year(p)||'');let m=!selected||y===selected;if(selected==='__active')m=/ausschreibung|beauftragt|in arbeit/.test(n(p.status));if(selected==='__overdue')m=p.planned_end&&new Date(p.planned_end).getTime()<now&&!/fertig|abgeschlossen/.test(n(p.status));if(selected==='__risk')m=Number(p.actual_cost||0)>Number(p.budget||0)&&Number(p.budget||0)>0;return m&&[p.project_name,p.status,p.supplier,p.responsible,p.order_number,p.notes,p.room?.name,p.room?.site].some(v=>n(v).includes(term))}).sort((a,b)=>(year(b)||0)-(year(a)||0)||b.id-a.id);
  renderRoadmap(rows);renderList(rows);
}
function renderRoadmap(rows){
  const byYear={};rows.forEach(p=>{const y=year(p)||'Ohne Jahr';const x=byYear[y] ||= {planned:0,committed:0,actual:0,count:0,done:0,overdue:0};x.planned+=Number(p.budget||0);x.committed+=Number(p.commissioned||0);x.actual+=Number(p.actual_cost||0);x.count++;if(/fertig|abgeschlossen/.test(n(p.status)))x.done++;if(p.planned_end&&new Date(p.planned_end)<new Date()&&!/fertig|abgeschlossen/.test(n(p.status)))x.overdue++});
  let box=document.querySelector('#roadmapControl');if(!box){box=document.createElement('div');box.id='roadmapControl';box.className='v2-card';document.querySelector('.v2-main').insertBefore(box,document.querySelector('.v2-card:last-of-type'));}
  const years=Object.keys(byYear).sort((a,b)=>String(b).localeCompare(String(a),undefined,{numeric:true}));
  box.innerHTML=`<div class="v2-card-head"><div><div class="eyebrow">MODERNISIERUNGS-CONTROLLING</div><h2>Roadmap · Budget · Fortschritt</h2><p>Jeder Jahresblock verbindet die geplanten Maßnahmen direkt mit Auftrag, Ist-Kosten und Projektfortschritt.</p></div></div><div class="controlling-grid">${years.length?years.map(y=>{const x=byYear[y],forecast=Math.max(x.planned,x.committed,x.actual),remaining=Math.max(0,forecast-x.actual),progress=x.planned?Math.min(100,x.actual/x.planned*100):0;return `<article class="control-card forecast"><span class="label">${esc(y)}</span><strong>${euro(forecast)}</strong><small>${x.count} Projekte · ${x.done} fertig${x.overdue?` · ${x.overdue} überfällig`:''}</small><div class="control-track"><span style="width:${progress}%"></span></div><small>Plan ${euro(x.planned)} · Auftrag ${euro(x.committed)} · Ist ${euro(x.actual)} · offen ${euro(remaining)}</small></article>`}).join(''):'<div class="ledger-empty">Keine Modernisierungsprojekte vorhanden.</div>'}</div>`;
}
function renderList(rows){
  if(!rows.length){list.innerHTML='<div class="v2-loading">Keine Projekte gefunden.</div>';return}
  list.innerHTML=`<div class="asset-row asset-head"><span>Projekt</span><span>Raum</span><span>Status</span><span>Plan / Auftrag</span><span>Ist / Forecast</span></div>`+rows.map(p=>{const b=Number(p.budget||0),c=Number(p.commissioned||0),a=Number(p.actual_cost||0),forecast=Math.max(b,c,a),over=a>b&&b>0,progress=b?Math.min(100,a/b*100):0;return `<a class="asset-row" href="/static/room-detail.html?id=${p.room.id}"><div><strong>${esc(p.project_name)}</strong><small>${esc([year(p),p.supplier].filter(Boolean).join(' · '))}</small></div><div><strong>${esc(p.room.name)}</strong><small>${esc([p.room.site,p.room.building,p.room.floor].filter(Boolean).join(' · '))}</small></div><div>${badge(p.status)}${p.planned_end&&new Date(p.planned_end)<new Date()&&!/fertig|abgeschlossen/.test(n(p.status))?'<small style="display:block;margin-top:4px">Überfällig</small>':''}</div><div><strong>${euro(b)}</strong><small>Beauftragt ${euro(c)}</small></div><div><strong>${euro(a)}</strong><small>${over?'⚠ über Budget':`Forecast ${euro(forecast)} · ${pct(progress)}`}</small></div></a>`}).join('')
}
q.addEventListener('input',render);load().catch(e=>list.innerHTML=`<div class="v2-loading">Fehler: ${esc(e.message)}</div>`);