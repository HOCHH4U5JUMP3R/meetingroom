const list=document.querySelector('#list'),q=document.querySelector('#q'),modal=document.querySelector('#modal'),form=document.querySelector('#modelForm');let models=[],editId=0;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
async function load(){
  const [modelRes,statsRes]=await Promise.all([fetch('/api/equipment-models'),fetch('/api/equipment-models/stats')]);
  if(!modelRes.ok||!statsRes.ok) throw new Error('Modelldaten konnten nicht geladen werden.');
  models=await modelRes.json();
  const stats=await statsRes.json();
  document.querySelector('#count').textContent=stats.models;
  document.querySelector('#manufacturers').textContent=stats.manufacturers;
  document.querySelector('#assigned').textContent=stats.assigned;
  document.querySelector('#coverage').textContent=`${stats.coverage.toLocaleString('de-DE',{maximumFractionDigits:1})} %`;
  render();
}
function render(){
  const term=(q.value||'').toLowerCase().trim();
  const rows=models.filter(m=>[m.name,m.manufacturer,m.model_number,m.category].some(v=>String(v||'').toLowerCase().includes(term)));
  list.innerHTML=rows.length?rows.map(m=>`<article class="model-card"><div class="model-image">${m.image_url?`<img src="${esc(m.image_url)}" alt="">`:'<span>NO IMAGE</span>'}</div><div class="model-body"><div class="eyebrow">${esc(m.category||'MODELL')}</div><h3>${esc(m.name)}</h3><p>${esc([m.manufacturer,m.model_number].filter(Boolean).join(' · ')||'Keine Herstellerangabe')}</p><small>${esc([m.size_inches?m.size_inches+' Zoll':'',m.mounting].filter(Boolean).join(' · '))}</small><div class="model-foot"><span>${m.equipment_count||0} Geräte</span><button class="btn" onclick="editModel(${m.id})">Bearbeiten</button></div></div></article>`).join(''):'<div class="v2-loading">Keine Modelle gefunden.</div>';
}
function openNew(){editId=0;form.reset();document.querySelector('#modalTitle').textContent='Modell anlegen';document.querySelector('#message').textContent='';modal.hidden=false}
window.editModel=id=>{const m=models.find(x=>x.id===id);if(!m)return;editId=id;for(const k of ['name','manufacturer','model_number','category','size_inches','mounting','description'])form.elements[k].value=m[k]??'';document.querySelector('#modalTitle').textContent='Modell bearbeiten';document.querySelector('#message').textContent='';modal.hidden=false}
async function save(e){e.preventDefault();const data={name:form.elements.name.value.trim(),manufacturer:form.elements.manufacturer.value.trim(),model_number:form.elements.model_number.value.trim(),category:form.elements.category.value.trim(),size_inches:form.elements.size_inches.value===''?null:Number(form.elements.size_inches.value),mounting:form.elements.mounting.value.trim(),description:form.elements.description.value.trim(),active:true};const r=await fetch(editId?`/api/equipment-models/${editId}`:'/api/equipment-models',{method:editId?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){document.querySelector('#message').textContent='Speichern fehlgeschlagen.';return}const saved=await r.json();const file=form.elements.image.files[0];if(file){const fd=new FormData();fd.append('file',file);const u=await fetch(`/api/equipment-models/${saved.id}/image`,{method:'POST',body:fd});if(!u.ok){document.querySelector('#message').textContent='Modell gespeichert, Bild konnte aber nicht hochgeladen werden.';return}}modal.hidden=true;await load()}
q.addEventListener('input',render);form.addEventListener('submit',save);document.querySelector('#newBtn').onclick=openNew;document.querySelector('#closeBtn').onclick=()=>modal.hidden=true;document.querySelector('#cancelBtn').onclick=()=>modal.hidden=true;load().catch(e=>list.innerHTML=`<div class="v2-loading">Fehler: ${esc(e.message)}</div>`);