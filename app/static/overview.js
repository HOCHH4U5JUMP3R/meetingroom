const searchInput = document.querySelector('#roomSearch');
const filterContainer = document.querySelector('#siteFilters');
const groupContainer = document.querySelector('#roomGroups');
const emptyState = document.querySelector('#overviewEmpty');
const errorState = document.querySelector('#overviewError');
const roomCount = document.querySelector('#roomCount');
let allRooms = [];
let selectedSite = '';

function escapeHtml(value) {
  return String(value == null || value === '' ? '–' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function siteFor(room) {
  return room.site || 'Ohne Standort';
}

function roomLocation(room) {
  const parts = [];
  if (room.building) parts.push(room.building);
  if (room.floor) parts.push(`Etage ${room.floor}`);
  if (room.room_number) parts.push(`Raum ${room.room_number}`);
  return parts.join(' · ') || 'Keine Standortdaten';
}

function filteredRooms() {
  const query = searchInput.value.trim().toLowerCase();
  return allRooms.filter(room => {
    if (selectedSite && siteFor(room) !== selectedSite) return false;
    const searchable = [room.name, room.site, room.building, room.floor, room.room_number, room.category, room.connections]
      .join(' ')
      .toLowerCase();
    return searchable.indexOf(query) !== -1;
  });
}

function renderRooms() {
  const rooms = filteredRooms();
  const grouped = {};
  rooms.forEach(room => {
    const site = siteFor(room);
    if (!grouped[site]) grouped[site] = [];
    grouped[site].push(room);
  });

  roomCount.textContent = String(rooms.length);
  emptyState.hidden = rooms.length !== 0;
  groupContainer.innerHTML = '';

  Object.keys(grouped).sort().forEach(site => {
    const siteRooms = grouped[site];
    const section = document.createElement('section');
    section.className = 'site-group';
    section.innerHTML = `
      <div class="site-group-header">
        <div><div class="eyebrow">STANDORT</div><h2>${escapeHtml(site)}</h2></div>
        <span>${siteRooms.length} ${siteRooms.length === 1 ? 'Raum' : 'Räume'}</span>
      </div>
      <div class="room-list" role="list"></div>`;

    const list = section.querySelector('.room-list');
    siteRooms.forEach(room => {
      const row = document.createElement('a');
      row.className = 'room-list-row';
      row.setAttribute('role', 'listitem');
      row.href = `/static/room-detail.html?id=${encodeURIComponent(room.id)}`;
      row.innerHTML = `
        <div><strong>${escapeHtml(room.name)}</strong><span>${escapeHtml(roomLocation(room))}</span></div>
        <div class="room-list-category">${escapeHtml(room.category || 'Meetingraum')}</div>
        <div class="room-list-seats">${room.seats != null ? `${escapeHtml(room.seats)} Plätze` : '–'}</div>
        <span class="status-badge">${escapeHtml(room.status || 'Aktiv')}</span>
        <span class="room-list-arrow" aria-hidden="true">›</span>`;
      list.appendChild(row);
    });
    groupContainer.appendChild(section);
  });
}


function renderFilters() {
  const seen = {};
  allRooms.forEach(room => { seen[siteFor(room)] = true; });
  const sites = Object.keys(seen).sort();
  filterContainer.innerHTML = '';

  const allButton = document.createElement('button');
  allButton.type = 'button';
  allButton.className = `site-filter ${selectedSite ? '' : 'active'}`;
  allButton.textContent = 'Alle Standorte';
  allButton.addEventListener('click', () => { selectedSite = ''; renderFilters(); renderRooms(); });
  filterContainer.appendChild(allButton);

  sites.forEach(site => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `site-filter ${site === selectedSite ? 'active' : ''}`;
    button.textContent = site;
    button.addEventListener('click', () => { selectedSite = site; renderFilters(); renderRooms(); });
    filterContainer.appendChild(button);
  });
}

async function loadRooms() {
  const roomsResponse = await fetch('/api/rooms', { headers: { Accept: 'application/json' } });
  if (!roomsResponse.ok) throw new Error(`Räume konnten nicht geladen werden (HTTP ${roomsResponse.status}).`);
  const data = await roomsResponse.json();
  if (!Array.isArray(data)) throw new Error('Die Raumdaten haben ein ungültiges Format.');
  allRooms = data;
  errorState.hidden = true;
  renderFilters();
  renderRooms();


}

searchInput.addEventListener('input', renderRooms);
loadRooms().catch(error => {
  console.error(error);
  errorState.textContent = error.message;
  errorState.hidden = false;
  emptyState.hidden = true;
});
