const search = document.querySelector('#roomSearch');
const filters = document.querySelector('#siteFilters');
const groups = document.querySelector('#roomGroups');
const empty = document.querySelector('#overviewEmpty');
const roomCount = document.querySelector('#roomCount');
let rooms = [];
let selectedSite = 'Alle Standorte';

const escapeHtml = value => String(value ?? '–').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
const location = room => [room.building, room.floor && `Etage ${room.floor}`, room.room_number && `Raum ${room.room_number}`].filter(Boolean).join(' · ') || 'Keine Standortdaten';

function render() {
  const query = search.value.trim().toLocaleLowerCase('de');
  const visible = rooms.filter(room => {
    const matchesSite = selectedSite === 'Alle Standorte' || (room.site || 'Ohne Standort') === selectedSite;
    const haystack = [room.name, room.site, room.building, room.floor, room.room_number, room.category, room.connections].join(' ').toLocaleLowerCase('de');
    return matchesSite && haystack.includes(query);
  });
  roomCount.textContent = rooms.length;
  empty.hidden = visible.length > 0;
  groups.innerHTML = Object.entries(visible.reduce((bySite, room) => { const site = room.site || 'Ohne Standort'; (bySite[site] ||= []).push(room); return bySite; }, {})).map(([site, siteRooms]) => `
    <section class="site-group">
      <div class="site-group-header"><div><div class="eyebrow">STANDORT</div><h2>${escapeHtml(site)}</h2></div><span>${siteRooms.length} ${siteRooms.length === 1 ? 'Raum' : 'Räume'}</span></div>
      <div class="room-cards">${siteRooms.map(room => `
        <a class="room-card" href="/static/room-detail.html?id=${room.id}">
          <div class="room-card-heading"><h3>${escapeHtml(room.name)}</h3><span class="status-badge">${escapeHtml(room.status || 'Aktiv')}</span></div>
          <p>${escapeHtml(location(room))}</p>
          <div class="room-card-meta"><span>${escapeHtml(room.category || 'Meetingraum')}</span>${room.seats != null ? `<span>${escapeHtml(room.seats)} Plätze</span>` : ''}</div>
        </a>`).join('')}</div>
    </section>`).join('');
}

function renderFilters() {
  const sites = ['Alle Standorte', ...new Set(rooms.map(room => room.site || 'Ohne Standort').sort((a, b) => a.localeCompare(b, 'de')))];
  filters.innerHTML = sites.map(site => `<button class="site-filter ${site === selectedSite ? 'active' : ''}" type="button" data-site="${escapeHtml(site)}">${escapeHtml(site)}</button>`).join('');
  filters.querySelectorAll('button').forEach(button => button.addEventListener('click', () => { selectedSite = button.dataset.site; renderFilters(); render(); }));
}

async function loadRooms() {
  const response = await fetch('/api/rooms');
  if (!response.ok) throw new Error('Räume konnten nicht geladen werden.');
  rooms = await response.json();
  renderFilters();
  render();
}
search.addEventListener('input', render);
loadRooms().catch(error => { empty.hidden = false; empty.querySelector('p').textContent = error.message; });
