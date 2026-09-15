(()=>{
const normalize=v=>String(v||'').trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function fixHamburg(){
 document.querySelectorAll('#siteBudgets .site-budget-input[data-site]').forEach(input=>{
   if(normalize(decodeURIComponent(input.dataset.site))!=='hamburg') return;
   const allocationText=input.closest('tr')?.querySelector('.site-name')?.parentElement?.parentElement?.querySelector('small')?.textContent||'';
   const allocation=.5;
   const raw=Number(input.value)||0;
   if(!input.dataset.hamburgTotal || document.activeElement!==input){ input.value=raw>0?Math.round(raw/allocation*100)/100:''; input.dataset.hamburgTotal='1'; }
   input.disabled=false;
   const button=input.closest('tr')?.querySelector('.site-save');
   if(button){button.disabled=false;button.textContent='Speichern';button.dataset.hamburgFixed='1';}
 });
}
document.addEventListener('click',async e=>{
 const button=e.target.closest('.site-save[data-site]');
 if(!button||button.dataset.hamburgFixed!=='1')return;
 e.preventDefault();e.stopImmediatePropagation();
 const site=decodeURIComponent(button.dataset.site);
 if(normalize(site)!=='hamburg')return;
 const input=button.closest('tr').querySelector('.site-budget-input');
 try{
   button.disabled=true;button.textContent='Speichern …';
   const r=await fetch(`/api/budget-overview/sites/${encodeURIComponent(site)}?year=${encodeURIComponent(document.querySelector('#budgetYear').value)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({budget:Number(input.value)||0})});
   if(!r.ok)throw Error('Hamburg-Budget konnte nicht gespeichert werden.');
   location.reload();
 }catch(err){button.disabled=false;button.textContent='Speichern';const box=document.querySelector('#budgetError');box.textContent=err.message;box.hidden=false;}
},true);
new MutationObserver(fixHamburg).observe(document.querySelector('#siteBudgets')||document.body,{childList:true,subtree:true});
setInterval(fixHamburg,500);
})();
