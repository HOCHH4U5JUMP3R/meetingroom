(() => {
  const $ = (selector) => document.querySelector(selector);
  const els = {
    year: $('#budgetYear'),
    quarter: $('#budgetQuarter'),
    month: $('#budgetMonth'),
    globalForm: $('#globalBudgetForm'),
    globalInput: $('#globalBudget'),
    totals: $('#budgetTotals'),
    divisions: $('#divisionTotals'),
    sites: $('#siteBudgets'),
    controlling: $('#budgetControlling'),
    error: $('#budgetError')
  };

  let activeDivision = '';
  let currentData = null;

  const money = (value) => Number(value || 0).toLocaleString('de-DE', {
    style: 'currency', currency: 'EUR', maximumFractionDigits: 0
  });
  const percent = (value) => `${Number(value || 0).toLocaleString('de-DE', { maximumFractionDigits: 1 })}%`;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  }[c]));
  const siteKey = (value) => String(value || '').trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  function showError(message) {
    if (!els.error) return;
    els.error.textContent = message;
    els.error.hidden = false;
  }
  function clearError() {
    if (els.error) els.error.hidden = true;
  }

  function params() {
    const p = new URLSearchParams();
    p.set('year', els.year.value || new Date().getFullYear());
    if (els.quarter.value) p.set('quarter', els.quarter.value);
    if (els.month.value) p.set('month', els.month.value);
    return p;
  }

  async function api(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
      let detail = '';
      try { detail = (await response.json()).detail || ''; } catch (_) {}
      throw new Error(detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  function moneyLine(label, value, className = '') {
    return `<div class="budget-metric ${className}"><span>${esc(label)}</span><strong>${money(value)}</strong></div>`;
  }

  function renderControlling(data) {
    if (!els.controlling) return;
    const t = data.total || {};
    const budget = Number(t.budget) || 0;
    const planned = Number(t.modernization_planned) || 0;
    const committed = Number(t.committed) || 0;
    const actual = Number(t.spent) || 0;
    const forecast = Number(t.forecast) || 0;
    const gap = budget - forecast;
    const ratio = budget ? Math.min(100, Math.max(0, forecast / budget * 100)) : 0;

    els.controlling.innerHTML = `
      <div class="controlling-grid">
        <div class="control-card plan"><span class="label">PLAN</span><strong>${money(planned)}</strong><small>Geplante Modernisierung</small></div>
        <div class="control-card commit"><span class="label">AUFTRAG / GEBUNDEN</span><strong>${money(committed)}</strong><small>Beauftragt + Equipmentkäufe</small></div>
        <div class="control-card actual"><span class="label">IST</span><strong>${money(actual)}</strong><small>Tatsächlich ausgegeben</small></div>
        <div class="control-card forecast"><span class="label">FORECAST</span><strong>${money(forecast)}</strong><small>Erwarteter Jahresendstand</small></div>
      </div>
      <div class="control-gap">
        <strong>Forecast vs. Jahresbudget</strong>
        <div class="control-track"><span style="width:${ratio}%"></span></div>
        <span class="${gap < 0 ? 'control-bad' : 'control-good'}">${money(Math.abs(gap))} ${gap < 0 ? 'über dem Budget' : 'Puffer bis zum Budget'}</span>
        · ${percent(budget ? forecast / budget * 100 : 0)} prognostiziert.
      </div>`;
  }

  function renderDivisions(data) {
    const groups = data.divisions || [];
    els.divisions.innerHTML = `<div class="division-grid">${groups.map((g) => `
      <article class="division-card ${activeDivision === g.division ? 'selected' : ''}" data-division="${esc(g.division)}">
        <div class="division-head"><strong>${g.division === 'DA' ? 'DAs' : 'DAv'}</strong><span>${g.sites || 0} Standort-Zuordnungen · ${g.rooms || 0} Räume</span></div>
        <div class="division-number">${money(g.budget)}</div>
        <div class="division-bar"><span style="width:${Math.min(100, Number(g.utilization) || 0)}%"></span></div>
        <div class="division-stats">
          <span>Gebunden<b>${money(g.committed)}</b></span>
          <span>Ist<b>${money(g.spent)}</b></span>
          <span>Forecast<b>${money(g.forecast)}</b></span>
          <span>Frei<b>${money(g.available)}</b></span>
        </div>
      </article>`).join('')}</div>`;

    els.divisions.querySelectorAll('.division-card').forEach((card) => {
      card.addEventListener('click', () => {
        activeDivision = activeDivision === card.dataset.division ? '' : card.dataset.division;
        render(currentData);
      });
    });
  }

  function renderSites(data) {
    const visible = (data.sites || []).filter((s) => !activeDivision || s.division === activeDivision);
    const divisions = ['DA', 'DAv'];
    let html = '';

    divisions.forEach((division) => {
      const group = visible.filter((s) => s.division === division);
      if (!group.length) return;
      html += `<tr><td colspan="9"><div class="site-group"><strong>${division === 'DA' ? 'DAs' : 'DAv'} · ${group.length} Standort-Zuordnungen</strong><span>${group.map(s => esc(s.site)).join(' · ')}</span></div></td></tr>`;
      html += group.map((s) => {
        const hamburg = siteKey(s.site) === 'hamburg';
        const allocation = Number(s.allocation || 1);
        return `<tr>
          <td><div class="site-name"><span class="division-pill ${s.division === 'DA' ? 'da' : 'dav'}">${s.division === 'DA' ? 'DAs' : 'DAv'}</span><strong>${esc(s.site)}</strong></div><small>${s.rooms || 0} Räume · ${percent(s.utilization)} gebunden${allocation < 1 ? ' · 50 % Anteil' : ''}</small></td>
          <td>${s.rooms || 0}</td>
          <td><input class="site-budget-input" data-site="${encodeURIComponent(s.site)}" type="number" min="0" step="0.01" value="${s.budget || ''}" ${hamburg ? 'disabled' : ''}></td>
          <td>${money(s.modernization_planned)}</td><td>${money(s.committed)}</td><td>${money(s.spent)}</td><td>${money(s.forecast)}</td><td>${money(s.available)}</td>
          <td>${hamburg ? '<small>50 % DA / 50 % DAv</small>' : `<button class="btn btn-small site-save" data-site="${encodeURIComponent(s.site)}">Speichern</button>`}</td>
        </tr>`;
      }).join('');
    });

    els.sites.innerHTML = html || '<tr><td colspan="9">Keine Standorte für den gewählten Filter.</td></tr>';
    els.sites.querySelectorAll('.site-save').forEach((button) => button.addEventListener('click', async () => {
      const input = button.closest('tr').querySelector('.site-budget-input');
      try {
        button.disabled = true;
        button.textContent = 'Speichern …';
        await api(`/api/budget-overview/sites/${encodeURIComponent(decodeURIComponent(button.dataset.site))}?year=${encodeURIComponent(data.year)}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ budget: Number(input.value) || 0 })
        });
        await load();
      } catch (e) {
        showError(`Standortbudget konnte nicht gespeichert werden: ${e.message}`);
        button.disabled = false;
        button.textContent = 'Speichern';
      }
    }));
  }

  function render(data) {
    currentData = data;
    clearError();
    if (!els.year.options.length) {
      (data.years || []).forEach((year) => els.year.add(new Option(year, year)));
    }
    els.year.value = String(data.year);
    els.globalInput.value = data.total?.budget || '';
    $('#budgetKpi').textContent = money(data.total?.budget);
    $('#plannedKpi').textContent = money(data.total?.committed);
    $('#spentKpi').textContent = money(data.total?.spent);
    $('#availableKpi').textContent = money(data.total?.available);

    renderControlling(data);
    renderDivisions(data);
    renderSites(data);

    const t = data.total || {};
    const forecastGap = Number(t.budget || 0) - Number(t.forecast || 0);
    els.totals.innerHTML = `
      <div class="budget-hero-grid">
        ${moneyLine('Jahresbudget', t.budget)}
        ${moneyLine('Modernisierung geplant', t.modernization_planned)}
        ${moneyLine('Modernisierung beauftragt', t.modernization_committed)}
        ${moneyLine('Modernisierung Ist', t.modernization_actual)}
        ${moneyLine('Equipment Ist', t.equipment_spent)}
        ${moneyLine('Gesamt Ist', t.spent, 'strong')}
        ${moneyLine('Gesamt gebunden', t.committed)}
        ${moneyLine('Forecast', t.forecast, forecastGap < 0 ? 'warning-value' : '')}
        ${moneyLine('Verfügbar', t.available, 'strong')}
      </div>
      <div class="budget-progress"><span style="width:${Math.min(100, Number(t.utilization) || 0)}%"></span></div>
      <small>${percent(t.utilization)} Budgetbindung · Equipmentkäufe werden sofort als Ist und gebunden berücksichtigt.</small>`;
  }

  async function load() {
    try {
      clearError();
      const data = await api(`/api/budget-overview?${params().toString()}`);
      render(data);
    } catch (e) {
      showError(`Budgetdaten konnten nicht geladen werden: ${e.message}`);
      console.error('Budget load failed', e);
    }
  }

  els.globalForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const year = els.year.value || new Date().getFullYear();
      const budget = Number(els.globalInput.value) || 0;
      const data = await api(`/api/budget-overview?year=${encodeURIComponent(year)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ budget })
      });
      render(data);
    } catch (e) {
      showError(`Gesamtbudget konnte nicht gespeichert werden: ${e.message}`);
    }
  });

  els.year.addEventListener('change', load);
  els.quarter.addEventListener('change', load);
  els.month.addEventListener('change', load);

  load();
})();
