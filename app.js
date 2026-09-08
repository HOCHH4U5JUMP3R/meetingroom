let rooms = [];
let current = null;

const $ = (selector) => document.querySelector(selector);


/* ================================
   HELPERS
================================ */

const esc = (value) => {
    if (value === null || value === undefined || value === "") {
        return "–";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
};


const euro = (value) => {
    const number = Number(value || 0);

    return number.toLocaleString("de-DE", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0
    });
};


const api = async (url, options = {}) => {

    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    if (!response.ok) {

        let message = `HTTP ${response.status}`;

        try {
            const data = await response.json();

            message =
                data.detail ||
                data.message ||
                message;

        } catch (_) {}

        throw new Error(message);
    }

    return response.json();
};


const statusClass = (value) => {

    const s =
        String(value || "")
            .toLowerCase();

    if (
        s.includes("aktiv") ||
        s.includes("erledigt") ||
        s.includes("abgeschlossen") ||
        s.includes("beauftragt") ||
        s.includes("freigegeben") ||
        s === "ok"
    ) {
        return "success";
    }

    if (
        s.includes("offen") ||
        s.includes("geplant") ||
        s.includes("wart") ||
        s.includes("in umsetzung") ||
        s.includes("in arbeit")
    ) {
        return "warning";
    }

    if (
        s.includes("krit") ||
        s.includes("störung") ||
        s.includes("abgelehnt")
    ) {
        return "danger";
    }

    return "";
};


const badge = (value) => {

    const cls = statusClass(value);

    return `
        <span class="badge ${cls ? `badge-${cls}` : ""}">
            ${esc(value || "–")}
        </span>
    `;
};


/* ================================
   ROOMS
================================ */

async function loadRooms(selectId = null) {

    rooms = await api("/api/rooms");

    const select = $("#roomSelect");

    select.innerHTML = "";

    if (!rooms.length) {

        select.innerHTML =
            `<option value="">Keine Räume vorhanden</option>`;

        $("#empty").hidden = false;
        $("#app").hidden = true;

        return;
    }


    rooms.forEach(room => {

        const option =
            document.createElement("option");

        option.value = room.id;

        option.textContent =
            room.name +
            (
                room.room_number
                    ? ` · ${room.room_number}`
                    : ""
            );

        select.appendChild(option);
    });


    const wanted =
        selectId ??
        current?.id ??
        rooms[0].id;

    select.value = String(wanted);

    await loadRoom(Number(select.value));
}


async function loadRoom(id) {

    if (!id) {

        current = null;

        $("#empty").hidden = false;
        $("#app").hidden = true;

        return;
    }


    current =
        await api(`/api/rooms/${id}`);


    $("#empty").hidden = true;
    $("#app").hidden = false;

    renderRoom();
}


/* ================================
   ROOM
================================ */

function renderRoom() {

    const r = current;


    $("#roomTitle").textContent =
        r.name || "Unbenannter Raum";


    const status =
        r.status || "Aktiv";

    const statusEl =
        $("#roomStatus");

    statusEl.textContent =
        status;

    statusEl.className =
        `status-badge ${statusClass(status)}`;


    const location = [
        r.site,

        r.building
            ? `Gebäude ${r.building}`
            : null,

        r.floor
            ? `Etage ${r.floor}`
            : null,

        r.room_number
            ? `Raum ${r.room_number}`
            : null,

        r.seats != null
            ? `${r.seats} Plätze`
            : null

    ].filter(Boolean);


    $("#roomSubtitle").textContent =
        location.join(" · ") ||
        "Keine Standortdaten";


    $("#roomMeta").textContent =
        [
            r.site,

            r.building
                ? `Gebäude ${r.building}`
                : null,

            r.floor
                ? `Etage ${r.floor}`
                : null

        ]
        .filter(Boolean)
        .join(" · ");


    renderRoomData();
    renderBudget();
    renderEquipment();
    renderRules();
    renderModernizations();
    renderTickets();
}


/* ================================
   MASTER DATA
================================ */

function renderRoomData() {

    const r = current;


    const area =
        r.length && r.width
            ? `${r.length} × ${r.width} m`
            : null;


    const areaM2 =
        r.length && r.width
            ? `${(
                Number(r.length) *
                Number(r.width)
            ).toFixed(1)} m²`
            : null;


    const volume =
        r.length &&
        r.width &&
        r.height

            ? `${(
                Number(r.length) *
                Number(r.width) *
                Number(r.height)
            ).toFixed(1)} m³`

            : null;


    const data = [

        ["Standort", r.site],

        ["Gebäude", r.building],

        ["Etage", r.floor],

        ["Raum", r.room_number],

        ["Plätze", r.seats],

        ["Raumgröße", area],

        ["Raumhöhe",
            r.height
                ? `${r.height} m`
                : null
        ],

        ["Fläche", areaM2],

        ["Volumen", volume],

        ["Raumkategorie", r.category],

        ["Raumverantwortlicher", r.owner],

        ["Host-Name", r.host_name],

        ["Outlook-Ressource",
            r.outlook_resource
        ],

        ["Anschlussmöglichkeiten",
            r.connections
        ],

        ["Besonderheit",
            r.specialty
        ],

        ["Letzte Modernisierung",
            r.last_modernization
        ]

    ];


    $("#roomData").innerHTML =
        data.map(([label, value]) => `
            <div class="data-item">

                <div class="data-label">
                    ${esc(label)}
                </div>

                <div class="data-value">
                    ${esc(value)}
                </div>

            </div>
        `).join("");
}


/* ================================
   BUDGET
================================ */

function renderBudget() {

    const modernizations =
        current.modernizations || [];


    const budget =
        modernizations.reduce(
            (sum, item) =>
                sum + Number(item.budget || 0),
            0
        );


    const commissioned =
        modernizations.reduce(
            (sum, item) =>
                sum + Number(item.commissioned || 0),
            0
        );


    const actual =
        modernizations.reduce(
            (sum, item) =>
                sum + Number(item.actual_cost || 0),
            0
        );


    const percent =
        budget > 0
            ? Math.min(
                100,
                Math.round(
                    commissioned / budget * 100
                )
            )
            : 0;


    $("#budget").innerHTML = `

        <div class="budget-grid">

            <div class="budget-item">

                <div class="budget-label">
                    Gesamtbudget
                </div>

                <div class="budget-value">
                    ${euro(budget)}
                </div>

            </div>


            <div class="budget-item">

                <div class="budget-label">
                    Beauftragt
                </div>

                <div class="budget-value">
                    ${euro(commissioned)}
                </div>

            </div>


            <div class="budget-item">

                <div class="budget-label">
                    Verbraucht
                </div>

                <div class="budget-value">
                    ${euro(actual)}
                </div>

            </div>

        </div>


        <div class="budget-progress-row">

            <span>
                Beauftragtes Budget
            </span>

            <strong>
                ${percent} %
            </strong>

        </div>


        <div class="progress">
            <div style="width:${percent}%"></div>
        </div>

    `;
}


/* ================================
   EQUIPMENT
================================ */

function renderEquipment() {

    const items =
        current.equipment || [];

    const container =
        $("#equipment");


    if (!items.length) {

        container.innerHTML = `

            <div class="list-empty">

                <strong>
                    Keine Ausstattung hinterlegt
                </strong>

                Für diesen Raum wurden noch
                keine Geräte erfasst.

            </div>
        `;

        return;
    }


    container.innerHTML = `

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>

                        <th>Gerät</th>
                        <th>Kategorie</th>
                        <th>Hersteller</th>
                        <th>Modell</th>
                        <th>Größe</th>
                        <th>Montage</th>
                        <th>Status</th>
                        <th></th>

                    </tr>

                </thead>


                <tbody>

                    ${items.map(item => `

                        <tr>

                            <td>

                                <div class="primary-text">
                                    ${esc(item.name)}
                                </div>

                                ${
                                    item.serial
                                        ? `
                                            <div class="secondary-text">
                                                S/N ${esc(item.serial)}
                                            </div>
                                          `
                                        : ""
                                }

                            </td>


                            <td>
                                ${esc(item.category)}
                            </td>


                            <td>
                                ${esc(item.manufacturer)}
                            </td>


                            <td>
                                ${esc(item.model)}
                            </td>


                            <td>
                                ${
                                    item.size_inches
                                        ? `${esc(item.size_inches)}"`
                                        : "–"
                                }
                            </td>


                            <td>
                                ${esc(item.mounting)}
                            </td>


                            <td>
                                ${badge(item.status || "Aktiv")}
                            </td>


                            <td>

                                <div class="actions">

                                    <button
                                        type="button"
                                        onclick="editEquipment(${item.id})">
                                        Bearb.
                                    </button>

                                    <button
                                        type="button"
                                        onclick="deleteItem('equipment', ${item.id})">
                                        Löschen
                                    </button>

                                </div>

                            </td>

                        </tr>

                    `).join("")}

                </tbody>

            </table>

        </div>

    `;
}


/* ================================
   BOOKING RULES
================================ */

function renderRules() {

    const items =
        current.rules || [];

    const container =
        $("#rules");


    if (!items.length) {

        container.innerHTML = `

            <div class="list-empty">

                <strong>
                    Keine Buchungsregeln
                </strong>

                Für diesen Raum wurden noch
                keine Berechtigungen hinterlegt.

            </div>

        `;

        return;
    }


    container.innerHTML = `

        <div class="rule-list">

            ${items.map(item => `

                <div class="rule-row">

                    <div>

                        <div class="primary-text">
                            ${esc(
                                item.entitlement ||
                                "Berechtigung"
                            )}
                        </div>

                        ${
                            item.notes
                                ? `
                                    <div class="secondary-text">
                                        ${esc(item.notes)}
                                    </div>
                                  `
                                : ""
                        }

                    </div>


                    <div>

                        ${
                            item.group_name
                                ? esc(item.group_name)
                                : "–"
                        }

                        ${
                            item.approver
                                ? `
                                    <div class="secondary-text">
                                        Freigabe:
                                        ${esc(item.approver)}
                                    </div>
                                  `
                                : ""
                        }

                    </div>


                    <div class="actions">

                        <button
                            type="button"
                            onclick="editRule(${item.id})">
                            Bearb.
                        </button>

                        <button
                            type="button"
                            onclick="deleteItem('rules', ${item.id})">
                            Löschen
                        </button>

                    </div>

                </div>

            `).join("")}

        </div>

    `;
}


/* ================================
   MODERNIZATIONS
================================ */

function renderModernizations() {

    const items =
        current.modernizations || [];

    const container =
        $("#modernizations");


    if (!items.length) {

        container.innerHTML = `

            <div class="list-empty">

                <strong>
                    Keine Modernisierungen
                </strong>

                Für diesen Raum wurden noch
                keine Projekte erfasst.

            </div>

        `;

        return;
    }


    container.innerHTML = `

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>

                        <th>Projekt</th>
                        <th>Jahr</th>
                        <th>Status</th>
                        <th>Budget</th>
                        <th>Beauftragt</th>
                        <th>Verbraucht</th>
                        <th>Verantwortlich</th>
                        <th></th>

                    </tr>

                </thead>


                <tbody>

                    ${items.map(item => `

                        <tr>

                            <td>

                                <div class="primary-text">
                                    ${esc(item.project_name)}
                                </div>

                                ${
                                    item.supplier
                                        ? `
                                            <div class="secondary-text">
                                                ${esc(item.supplier)}
                                            </div>
                                          `
                                        : ""
                                }

                            </td>


                            <td>
                                ${esc(item.project_year)}
                            </td>


                            <td>
                                ${badge(item.status)}
                            </td>


                            <td>
                                ${euro(item.budget)}
                            </td>


                            <td>
                                ${euro(item.commissioned)}
                            </td>


                            <td>
                                ${euro(item.actual_cost)}
                            </td>


                            <td>
                                ${esc(item.responsible)}
                            </td>


                            <td>

                                <div class="actions">

                                    <button
                                        type="button"
                                        onclick="editModernization(${item.id})">
                                        Bearb.
                                    </button>

                                    <button
                                        type="button"
                                        onclick="deleteItem('modernizations', ${item.id})">
                                        Löschen
                                    </button>

                                </div>

                            </td>

                        </tr>

                    `).join("")}

                </tbody>

            </table>

        </div>

    `;
}


/* ================================
   TICKETS
================================ */

function renderTickets() {

    const items =
        current.tickets || [];

    const container =
        $("#tickets");


    if (!items.length) {

        container.innerHTML = `

            <div class="list-empty">

                <strong>
                    Keine Tickets
                </strong>

                Für diesen Raum sind keine
                Vorgänge hinterlegt.

            </div>

        `;

        return;
    }


    container.innerHTML = `

        <div class="ticket-list">

            ${items.map(item => `

                <div class="ticket-row">

                    <div class="ticket-number">
                        #${esc(item.ticket_number)}
                    </div>


                    <div>

                        <div class="ticket-title">
                            ${esc(item.subject)}
                        </div>

                        <div class="secondary-text">

                            ${esc(
                                item.category || "–"
                            )}

                            ${
                                item.priority
                                    ? ` · Priorität:
                                       ${esc(item.priority)}`
                                    : ""
                            }

                            ${
                                item.responsible
                                    ? ` · ${esc(item.responsible)}`
                                    : ""
                            }

                        </div>

                    </div>


                    <div>

                        ${badge(item.status || "Offen")}

                        <div
                            class="actions"
                            style="margin-top:4px">

                            <button
                                type="button"
                                onclick="editTicket(${item.id})">
                                Bearb.
                            </button>

                            <button
                                type="button"
                                onclick="deleteItem('tickets', ${item.id})">
                                Löschen
                            </button>

                        </div>

                    </div>

                </div>

            `).join("")}

        </div>

    `;
}


/* ================================
   DELETE
================================ */

async function deleteItem(kind, id) {

    if (!confirm(
        "Diesen Eintrag wirklich löschen?"
    )) {
        return;
    }


    try {

        await api(
            `/api/${kind}/${id}`,
            {
                method: "DELETE"
            }
        );


        await loadRoom(current.id);

    } catch (error) {

        alert(
            `Löschen fehlgeschlagen: ${error.message}`
        );
    }
}


/* ================================
   EDIT LINKS
================================ */

function editEquipment(id) {

    window.location.href =
        `/static/equipment-form.html` +
        `?room_id=${current.id}&id=${id}`;
}


function editRule(id) {

    window.location.href =
        `/static/booking-form.html` +
        `?room_id=${current.id}&id=${id}`;
}


function editModernization(id) {

    window.location.href =
        `/static/modernization-form.html` +
        `?room_id=${current.id}&id=${id}`;
}


function editTicket(id) {

    window.location.href =
        `/static/ticket-form.html` +
        `?room_id=${current.id}&id=${id}`;
}


/* ================================
   EVENTS
================================ */

$("#roomSelect").addEventListener(
    "change",
    async (event) => {
        await loadRoom(
            Number(event.target.value)
        );
    }
);


$("#newRoom").addEventListener(
    "click",
    () => {
        window.location.href =
            "/static/room-form.html";
    }
);


$("#editRoom").addEventListener(
    "click",
    () => {

        if (!current) return;

        window.location.href =
            `/static/room-form.html?id=${current.id}`;
    }
);


$("#addEquipment").addEventListener(
    "click",
    () => {

        if (!current) return;

        window.location.href =
            `/static/equipment-form.html?room_id=${current.id}`;
    }
);


$("#addRule").addEventListener(
    "click",
    () => {

        if (!current) return;

        window.location.href =
            `/static/booking-form.html?room_id=${current.id}`;
    }
);


$("#addModernization").addEventListener(
    "click",
    () => {

        if (!current) return;

        window.location.href =
            `/static/modernization-form.html?room_id=${current.id}`;
    }
);


$("#addTicket").addEventListener(
    "click",
    () => {

        if (!current) return;

        window.location.href =
            `/static/ticket-form.html?room_id=${current.id}`;
    }
);


/* ================================
   START
================================ */

loadRooms().catch(error => {

    console.error(error);

    $("#roomSelect").innerHTML =
        `<option value="">
            Fehler beim Laden der Räume
        </option>`;

    $("#empty").hidden = false;
    $("#app").hidden = true;
});
