/**
 * Behaviour of the inline script of `formulario_cdi_form.html` (CDI03): per-day
 * schedule rows, conditional fields, the CUIT mask, the room totals and the two
 * province/department/municipality/locality cascades. It works on the DOM of the
 * page like the native script (the fields are the server-rendered crispy
 * markup), with every listener bound once per mounted form and released through
 * the returned function. The schedule card is placed by the route module (the
 * native script moves it after the days row).
 */
export type GeographyUrls = { departamentos: string; municipios: string; localidades: string };
export type Geography = { load: (url: string) => Promise<unknown> };

/** Same-origin JSON for the cascading selects; replaceable in tests. */
export const geography: Geography = {
  load: async (url) => {
    const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
    if (!response.ok) throw new Error("No se pudieron cargar opciones");
    return response.json();
  },
};

type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
const byId = (id: string) => document.getElementById(id);
const value = (id: string) => (byId(id) as Control | null)?.value;
const checkedValues = (name: string) => Array.from(document.querySelectorAll<HTMLInputElement>(`input[name='${name}']:checked`)).map((i) => i.value);
const sinPrestaciones = () => !checkedValues("prestaciones_alimentarias").includes("ninguna");

const SHOW_WHEN: Record<string, () => boolean> = {
  tipo_jornada_otra: () => value("id_tipo_jornada") === "other",
  seguridad_electrica: () => value("id_acceso_energia") !== "sin_electricidad",
  modalidad_gestion_otra: () => value("id_modalidad_gestion") === "otra",
  modalidad_tenencia_otra: () => value("id_modalidad_tenencia") === "otra",
  combustible_cocinar: () => value("id_tiene_espacio_cocina") === "si",
  tiene_juegos_exteriores: () => value("id_tiene_espacio_exterior") === "si",
  prestaciones_alimentarias_otra: () => checkedValues("prestaciones_alimentarias").includes("otra"),
  calidad_elaboracion_menu: sinPrestaciones,
  evaluacion_periodica_menu: sinPrestaciones,
  cobertura_capacitacion_manipulacion_alimentos: sinPrestaciones,
};

export function formatCuit(raw: string): string {
  const digits = (raw || "").replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 10) return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  return `${digits.slice(0, 2)}-${digits.slice(2, 10)}-${digits.slice(10)}`;
}

function bindSchedule(signal: AbortSignal) {
  const wrappers = Array.from(document.querySelectorAll<HTMLElement>("[data-field-name]"));
  const diasInputs = Array.from(document.querySelectorAll<HTMLInputElement>("input[name='dias_funcionamiento']"));
  const rows = Array.from(document.querySelectorAll<HTMLElement>(".formulario-horario-row"));
  const touched: Record<string, boolean> = {};
  const selectedDias = () => diasInputs.filter((i) => i.checked).map((i) => i.value);
  const rowOf = (dia: string) => rows.find((r) => r.dataset.dia === dia);
  const open = (row: HTMLElement) => row.querySelector<HTMLInputElement>("input[id$='_apertura']");
  const close = (row: HTMLElement) => row.querySelector<HTMLInputElement>("input[id$='_cierre']");

  function copyFirstScheduleToOthers() {
    const dias = selectedDias();
    if (!dias.length) return;
    const first = dias.map(rowOf).find((row) => {
      if (!row) return false;
      const o = open(row), c = close(row);
      return !!o && !!c && !!(o.value || c.value);
    });
    if (!first) return;
    const firstOpen = open(first), firstClose = close(first);
    if (!firstOpen || !firstClose || (!firstOpen.value && !firstClose.value)) return;
    dias.slice(1).forEach((dia) => {
      if (touched[dia]) return;
      const row = rowOf(dia);
      if (!row) return;
      const o = open(row), c = close(row);
      if (o && !o.value) o.value = firstOpen.value;
      if (c && !c.value) c.value = firstClose.value;
    });
  }
  function refreshRows() {
    const dias = selectedDias();
    rows.forEach((row) => {
      const visible = dias.includes(row.dataset.dia ?? "");
      row.classList.toggle("d-none", !visible);
      row.querySelectorAll("input").forEach((input) => {
        input.disabled = !visible;
        if (!visible) { input.value = ""; touched[row.dataset.dia ?? ""] = false; }
      });
    });
    copyFirstScheduleToOthers();
  }
  function refreshVisibility() {
    wrappers.forEach((wrapper) => {
      const resolver = SHOW_WHEN[wrapper.dataset.fieldName ?? ""];
      if (!resolver) {
        wrapper.querySelectorAll<Control>("input, select, textarea").forEach((el) => { el.disabled = false; });
        wrapper.classList.remove("d-none");
        return;
      }
      const visible = resolver();
      wrapper.classList.toggle("d-none", !visible);
      wrapper.querySelectorAll<Control>("input, select, textarea").forEach((el) => {
        if (el.type === "hidden") return;
        el.disabled = !visible;
        if (visible) return;
        if (el.type === "checkbox" || el.type === "radio") { (el as HTMLInputElement).checked = false; return; }
        el.value = "";
      });
    });
  }
  document.addEventListener("change", refreshVisibility, { signal });
  diasInputs.forEach((input) => input.addEventListener("change", refreshRows, { signal }));
  rows.forEach((row) => {
    const dia = row.dataset.dia ?? "";
    row.querySelectorAll("input").forEach((input) => input.addEventListener("input", () => {
      touched[dia] = true;
      if (selectedDias()[0] === dia) copyFirstScheduleToOthers();
    }, { signal }));
  });
  refreshVisibility();
  refreshRows();
}

function bindCuit(signal: AbortSignal) {
  const cuit = byId("id_cuit_organizacion_gestora") as HTMLInputElement | null;
  if (!cuit) return;
  cuit.addEventListener("input", () => { cuit.value = formatCuit(cuit.value); }, { signal });
  cuit.value = formatCuit(cuit.value);
}

const toNumber = (input: Element | null): number => {
  if (!input) return 0;
  const parsed = parseFloat(((input as HTMLInputElement).value || "0").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
};

function refreshRoomTotals() {
  const rows = Array.from(document.querySelectorAll("tbody tr")).filter((row) => row.querySelector("input[id$='-cantidad_salas']"));
  let rooms = 0, area = 0, children = 0, staff = 0;
  rows.forEach((row) => {
    const roomCount = toNumber(row.querySelector("input[id$='-cantidad_salas']"));
    const surface = toNumber(row.querySelector("input[id$='-superficie_exclusiva_m2']"));
    const kids = toNumber(row.querySelector("input[id$='-cantidad_ninos']"));
    const personnel = toNumber(row.querySelector("input[id$='-cantidad_personal_sala']"));
    rooms += roomCount; area += surface; children += kids; staff += personnel;
    const ratio = row.querySelector(".room-staff-ratio");
    if (ratio) ratio.textContent = roomCount > 0 ? (personnel / roomCount).toFixed(2) : "-";
  });
  const set = (id: string, text: string | number) => { const el = byId(id); if (el) el.textContent = String(text); };
  set("room-total-count", rooms);
  set("room-total-area", area.toFixed(2));
  set("room-total-children", children);
  set("room-total-staff", staff);
  set("room-total-ratio", rooms > 0 ? (staff / rooms).toFixed(2) : "-");
}

function bindRoomTotals(signal: AbortSignal) {
  document.addEventListener("input", (event) => {
    const id = (event.target as HTMLElement | null)?.id || "";
    if (["-cantidad_salas", "-superficie_exclusiva_m2", "-cantidad_ninos", "-cantidad_personal_sala"].some((part) => id.includes(part))) refreshRoomTotals();
  }, { signal });
  refreshRoomTotals();
}

type Item = { id: unknown; nombre?: unknown };
const itemsValid = (v: unknown): v is Item[] => Array.isArray(v) && v.every((i) => !!i && typeof i === "object");

function replaceOptions(sel: HTMLSelectElement, items: Item[], placeholder: string, selected: string) {
  sel.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = placeholder || "---------";
  sel.appendChild(empty);
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    option.textContent = String(item.nombre ?? "");
    sel.appendChild(option);
  });
  if (selected) sel.value = String(selected);
}

async function fetchOptions(url: string): Promise<Item[]> {
  const rows = await geography.load(url);
  if (!itemsValid(rows)) throw new Error("No se pudieron cargar opciones");
  return rows;
}

function setupGeoCascade(suffix: string, urls: GeographyUrls, signal: AbortSignal) {
  const provincia = byId(`id_provincia_${suffix}`) as HTMLSelectElement | null;
  const departamento = byId(`id_departamento_${suffix}`) as HTMLSelectElement | null;
  const municipio = byId(`id_municipio_${suffix}`) as HTMLSelectElement | null;
  const localidad = byId(`id_localidad_${suffix}`) as HTMLSelectElement | null;
  if (!provincia || !departamento || !municipio || !localidad) return;
  const guard = <T,>(task: () => Promise<T>) => task().catch((error) => { console.error(error); });

  async function loadDepartamentos(selected: string) {
    if (!provincia!.value) { replaceOptions(departamento!, [], "Seleccione un departamento", ""); return; }
    const rows = await fetchOptions(`${urls.departamentos}?provincia_id=${encodeURIComponent(provincia!.value)}`);
    if (!signal.aborted) replaceOptions(departamento!, rows, "Seleccione un departamento", selected || "");
  }
  async function loadLocalidades(selected: string) {
    if (!municipio!.value) { replaceOptions(localidad!, [], "Seleccione una localidad", ""); return; }
    const rows = await fetchOptions(`${urls.localidades}?municipio_id=${encodeURIComponent(municipio!.value)}`);
    if (!signal.aborted) replaceOptions(localidad!, rows, "Seleccione una localidad", selected || "");
  }
  async function loadMunicipios(selectedMunicipio: string, selectedLocalidad: string) {
    if (!provincia!.value) {
      replaceOptions(municipio!, [], "Seleccione un municipio", "");
      replaceOptions(localidad!, [], "Seleccione una localidad", "");
      return;
    }
    const rows = await fetchOptions(`${urls.municipios}?provincia_id=${encodeURIComponent(provincia!.value)}`);
    if (signal.aborted) return;
    replaceOptions(municipio!, rows, "Seleccione un municipio", selectedMunicipio || "");
    await loadLocalidades(selectedLocalidad);
  }
  provincia.addEventListener("change", () => { void guard(() => loadDepartamentos("")); void guard(() => loadMunicipios("", "")); }, { signal });
  municipio.addEventListener("change", () => { void guard(() => loadLocalidades("")); }, { signal });
  if (provincia.value) {
    void guard(() => loadDepartamentos(departamento.value));
    void guard(() => loadMunicipios(municipio.value, localidad.value));
  }
}

/** Binds every behaviour to the mounted form; the result releases the listeners. */
export function bindFormularioForm(urls: GeographyUrls): () => void {
  const controller = new AbortController();
  const { signal } = controller;
  bindSchedule(signal);
  bindCuit(signal);
  bindRoomTotals(signal);
  setupGeoCascade("cdi", urls, signal);
  setupGeoCascade("organizacion", urls, signal);
  return () => controller.abort();
}
