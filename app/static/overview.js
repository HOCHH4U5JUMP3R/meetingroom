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
      <div class="room-cards"></div>`;

    const cards = section.querySelector('.room-cards');
    siteRooms.forEach(room => {
      const card = document.createElement('a');
      card.className = 'room-card';
      card.href = `/static/room-detail.html?id=${encodeURIComponent(room.id)}`;
      card.innerHTML = `
        <div class="room-card-heading"><h3>${escapeHtml(room.name)}</h3><span class="status-badge">${escapeHtml(room.status || 'Aktiv')}</span></div>
        <p>${escapeHtml(roomLocation(room))}</p>
        <div class="room-card-meta"><span>${escapeHtml(room.category || 'Meetingraum')}</span>${room.seats != null ? `<span>${escapeHtml(room.seats)} Plätze</span>` : ''}</div>`;
      cards.appendChild(card);
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
  const response = await fetch('/api/rooms', { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Räume konnten nicht geladen werden (HTTP ${response.status}).`);
  const data = await response.json();
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
