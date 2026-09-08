const form = document.querySelector('#entityForm');
const config = JSON.parse(document.querySelector('#formConfig').textContent);
const params = new URLSearchParams(window.location.search);
const roomId = Number(params.get('room_id'));
const entryId = Number(params.get('id'));

function message(text, type = 'error') {
  const element = document.querySelector('#formMessage');
  element.textContent = text;
  element.className = `form-message ${type}`;
}

function valueFor(field) {
  const input = form.elements[field.name];
  if (field.type === 'checkbox') return input.checked;
  if (field.type === 'number') return input.value === '' ? null : Number(input.value);
  return input.value.trim();
}

async function loadEntry() {
  if (!roomId) {
    message('Es wurde kein Meetingraum ausgewählt.');
    form.querySelector('button[type="submit"]').disabled = true;
    return;
  }
  if (!entryId) return;

  document.querySelector('#pageTitle').textContent = config.editTitle;
  const response = await fetch(`/api/rooms/${roomId}`);
  if (!response.ok) throw new Error('Raum konnte nicht geladen werden.');
  const room = await response.json();
  const entry = (room[config.collection] || []).find(item => item.id === entryId);
  if (!entry) throw new Error('Der Eintrag wurde nicht gefunden.');

  config.fields.forEach(field => {
    const input = form.elements[field.name];
    if (!input) return;
    if (field.type === 'checkbox') input.checked = Boolean(entry[field.name]);
    else input.value = entry[field.name] ?? '';
  });
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!roomId) return;
  const data = Object.fromEntries(config.fields.map(field => [field.name, valueFor(field)]));
  const url = entryId ? `/api/${config.kind}/${entryId}` : `/api/rooms/${roomId}/${config.kind}`;
  const response = await fetch(url, {
    method: entryId ? 'PUT' : 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    message(error.detail || 'Speichern fehlgeschlagen.');
    return;
  }
  window.location.href = '/';
});

document.querySelector('#cancel').addEventListener('click', () => window.location.href = '/');
loadEntry().catch(error => message(error.message));
