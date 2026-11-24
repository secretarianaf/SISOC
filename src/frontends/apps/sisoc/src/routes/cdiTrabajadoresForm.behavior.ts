/**
 * Behaviour of `trabajadorForm.js` and `cdiSinCuil.js` (CDI05): progress and
 * section status, conditional rows, contact geography, age and the "No posee
 * CUIL" box. It works on the DOM of the form like the native scripts (the fields
 * are the server-rendered crispy markup), with listeners bound once per mounted
 * form and released through the returned function. The collapsible cards are
 * React state in the route module, not part of this file.
 */
export type GeographyUrls = { departamentos: string; municipios: string; localidades: string };
export type Geography = { load: (url: string) => Promise<unknown> };

/** Same-origin JSON for the cascading selects; replaceable in tests. */
export const geography: Geography = {
  load: async (url) => {
    const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },
};

const TOTAL_SECTIONS = 7;
const NIVELES_HABILITAN_FORMACION = new Set(["secundario_completo", "superior_incompleto", "superior_en_curso", "superior_completo"]);
type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

const byId = (id: string) => document.getElementById(id);
const val = (id: string) => (byId(id) as Control | null)?.value.trim() ?? "";
const select = (id: string) => byId(id) as HTMLSelectElement | null;

function hasSectionData(sectionId: string): boolean {
  const section = byId(`section-${sectionId}`);
  if (!section) return false;
  for (const input of section.querySelectorAll<Control>("input:not([type=hidden]):not([type=checkbox]), select, textarea")) {
    if (input.value && input.value.trim() !== "") return true;
  }
  return section.querySelectorAll("input[type=checkbox]:checked").length > 0;
}

function updateProgress() {
  const sections: Record<string, boolean> = {
    espacio_temporal: val("id_fecha_carga") !== "",
    fuerza_trabajo: val("id_nombre") !== "" && val("id_apellido") !== "" && val("id_subcomponente") !== "",
    formacion: val("id_nivel_educativo") !== "",
    contratacion: val("id_tipo_contratacion") !== "",
    contacto: val("id_email") !== "" || val("id_telefono") !== "",
    identidad: document.querySelectorAll("#id_grupo_pertenencia input[type=checkbox]:checked").length > 0,
    discapacidad: val("id_tiene_discapacidad") !== "",
  };
  let completed = 0;
  for (const id of Object.keys(sections)) {
    const badge = byId(`status-${id}`);
    if (!badge) continue;
    if (sections[id]) {
      completed++;
      badge.className = "status-badge complete";
      badge.innerHTML = '<i class="fas fa-check-circle"></i> Completada';
    } else if (hasSectionData(id)) {
      badge.className = "status-badge incomplete";
      badge.innerHTML = '<i class="fas fa-exclamation-circle"></i> Incompleta';
    } else {
      badge.className = "status-badge empty";
      badge.innerHTML = '<i class="fas fa-circle"></i> Sin completar';
    }
  }
  const bar = byId("progressBarFill");
  const span = byId("completedSections");
  if (bar) bar.style.width = `${(completed / TOTAL_SECTIONS) * 100}%`;
  if (span) span.textContent = String(completed);
}

const toggleVisible = (el: HTMLElement | null, show: boolean) => el?.classList.toggle("d-none", !show);

function setContainerControlsEnabled(container: HTMLElement | null, enabled: boolean, clearWhenDisabled: boolean, requiredWhenEnabled: boolean) {
  if (!container) return;
  container.querySelectorAll<Control>("input, select, textarea").forEach((control) => {
    if (!enabled && clearWhenDisabled) {
      if (control instanceof HTMLInputElement && (control.type === "checkbox" || control.type === "radio")) control.checked = false;
      else control.value = "";
    }
    control.disabled = !enabled;
    control.required = Boolean(enabled && requiredWhenEnabled);
  });
}

function bindConditionalFields(signal: AbortSignal) {
  const subcomponente = select("id_subcomponente");
  const nivel = select("id_nivel_educativo");
  const tieneDiscapacidad = select("id_tiene_discapacidad");
  const tieneCud = select("id_tiene_cud");
  const rows = {
    pfpi: byId("row-funcion-pfpi"), egp: byId("row-funcion-egp"), cdi: byId("row-funcion-cdi"), sala: byId("row-sala-cdi"), uaf: byId("row-funcion-uaf"),
  };
  const applyFunciones = () => {
    if (!subcomponente) return;
    const v = subcomponente.value;
    toggleVisible(rows.pfpi, v === "pfpi");
    toggleVisible(rows.egp, v === "egp");
    toggleVisible(rows.cdi, v === "cdi");
    toggleVisible(rows.sala, v === "cdi");
    toggleVisible(rows.uaf, v === "uaf");
    setContainerControlsEnabled(rows.pfpi, v === "pfpi", true, true);
    setContainerControlsEnabled(rows.egp, v === "egp", true, true);
    setContainerControlsEnabled(rows.cdi, v === "cdi", true, true);
    setContainerControlsEnabled(rows.sala, v === "cdi", true, true);
    setContainerControlsEnabled(rows.uaf, v === "uaf", true, true);
  };
  const applyFormacion = () => { if (nivel) toggleVisible(byId("row-formacion-academica"), NIVELES_HABILITAN_FORMACION.has(nivel.value)); };
  const applyPueblo = () => {
    const checked = Array.from(document.querySelectorAll<HTMLInputElement>("#id_grupo_pertenencia input[type=checkbox]:checked")).map((c) => c.value);
    toggleVisible(byId("row-pueblo-originario"), checked.includes("indigena"));
  };
  const applyDiscapacidad = () => { if (tieneDiscapacidad) toggleVisible(byId("bloque-discapacidad"), tieneDiscapacidad.value === "si"); };
  const applyCud = () => { if (tieneCud) toggleVisible(byId("row-numero-cud"), tieneCud.value === "si"); };
  applyFunciones(); applyFormacion(); applyPueblo(); applyDiscapacidad(); applyCud();
  const on = (el: Element | null, handler: () => void) => el?.addEventListener("change", handler, { signal });
  on(subcomponente, applyFunciones);
  on(nivel, applyFormacion);
  on(tieneDiscapacidad, applyDiscapacidad);
  on(tieneCud, applyCud);
  document.querySelectorAll("#id_grupo_pertenencia input[type=checkbox]").forEach((cb) => on(cb, applyPueblo));
}

type Row = Record<string, unknown>;
const rowsValid = (v: unknown): v is Row[] => Array.isArray(v) && v.every((r) => !!r && typeof r === "object");

function bindGeography(urls: GeographyUrls, signal: AbortSignal) {
  const provincia = select("id_provincia_contacto");
  const departamento = select("id_departamento_contacto");
  const municipio = select("id_municipio_contacto");
  const localidad = select("id_localidad_contacto");
  const initialMunicipio = municipio?.value ?? "";
  const initialLocalidad = localidad?.value ?? "";
  const reset = (sel: HTMLSelectElement | null, label: string) => {
    if (!sel) return;
    sel.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = label;
    sel.appendChild(option);
  };
  const selectValue = (sel: HTMLSelectElement | null, value: string) => {
    if (!sel || !value) return;
    if (!Array.from(sel.options).some((o) => o.value === value)) sel.appendChild(new Option(value, value));
    sel.value = value;
  };
  async function loadOptions(url: string, sel: HTMLSelectElement | null, emptyLabel: string, valueKey = "id") {
    if (!sel || !url) return;
    const rows = await geography.load(url);
    if (!rowsValid(rows)) throw new Error("invalid options");
    reset(sel, emptyLabel);
    for (const item of rows) {
      const option = document.createElement("option");
      option.value = String(item[valueKey] ?? "");
      option.textContent = String(item.nombre ?? item.nombre_region ?? "");
      sel.appendChild(option);
    }
  }
  const loadProvincia = (value: string) => Promise.all([
    loadOptions(`${urls.departamentos}?provincia_id=${value}`, departamento, "Seleccionar departamento...", "nombre"),
    loadOptions(`${urls.municipios}?provincia_id=${value}`, municipio, "Seleccionar municipio..."),
  ]);
  if (provincia && municipio) {
    provincia.addEventListener("change", async () => {
      try {
        reset(departamento, "Seleccionar departamento...");
        reset(municipio, "Seleccionar municipio...");
        reset(localidad, "Seleccionar localidad...");
        if (!provincia.value) return;
        await loadOptions(`${urls.departamentos}?provincia_id=${provincia.value}`, departamento, "Seleccionar departamento...", "nombre");
        await loadOptions(`${urls.municipios}?provincia_id=${provincia.value}`, municipio, "Seleccionar municipio...");
      } catch (error) { console.error("Error al cargar municipios:", error); }
    }, { signal });
  }
  if (municipio && localidad) {
    municipio.addEventListener("change", async () => {
      try {
        reset(localidad, "Seleccionar localidad...");
        if (!municipio.value) return;
        await loadOptions(`${urls.localidades}?municipio_id=${municipio.value}`, localidad, "Seleccionar localidad...");
      } catch (error) { console.error("Error al cargar localidades:", error); }
    }, { signal });
  }
  if (provincia?.value) {
    const initialDepartamento = departamento?.value ?? "";
    loadProvincia(provincia.value).then(() => {
      if (signal.aborted) return undefined;
      selectValue(departamento, initialDepartamento);
      selectValue(municipio, initialMunicipio);
      if (municipio?.value && localidad) {
        return loadOptions(`${urls.localidades}?municipio_id=${municipio.value}`, localidad, "Seleccionar localidad...").then(() => {
          if (!signal.aborted) selectValue(localidad, initialLocalidad);
        });
      }
      return undefined;
    }).catch((error) => console.error("Error al precargar ubicación:", error));
  }
}

function bindAge(signal: AbortSignal) {
  const nacimiento = byId("id_fecha_nacimiento") as HTMLInputElement | null;
  const edad = byId("id_edad_calculada") as HTMLInputElement | null;
  if (!nacimiento || !edad) return;
  const calcular = (value: string) => {
    if (!value) { edad.value = ""; return; }
    const nac = new Date(`${value}T00:00:00`);
    if (Number.isNaN(nac.getTime())) { edad.value = ""; return; }
    const hoy = new Date();
    let years = hoy.getFullYear() - nac.getFullYear();
    const mes = hoy.getMonth() - nac.getMonth();
    if (mes < 0 || (mes === 0 && hoy.getDate() < nac.getDate())) years--;
    edad.value = years >= 0 ? String(years) : "";
  };
  calcular(nacimiento.value);
  nacimiento.addEventListener("change", () => calcular(nacimiento.value), { signal });
}

function bindSinCuil(signal: AbortSignal) {
  document.querySelectorAll<HTMLInputElement>("[data-sin-cuil-de]").forEach((casilla) => {
    const cuit = byId(casilla.dataset.sinCuilDe ?? "") as HTMLInputElement | null;
    if (!cuit) return;
    const requerido = cuit.required || casilla.checked;
    const aplicar = () => {
      if (casilla.checked) cuit.value = "";
      cuit.readOnly = casilla.checked || cuit.dataset.renaper === "1";
      cuit.required = requerido && !casilla.checked;
    };
    casilla.addEventListener("change", aplicar, { signal });
    cuit.addEventListener("change", () => { if (cuit.value) casilla.checked = false; aplicar(); }, { signal });
    aplicar();
  });
}

/** Binds every behaviour to the mounted form; the result releases the listeners. */
export function bindTrabajadorForm(form: HTMLFormElement, urls: GeographyUrls): () => void {
  const controller = new AbortController();
  const { signal } = controller;
  // The native scripts run in this order: the progress first (before the conditional rows clear their controls).
  updateProgress();
  form.addEventListener("input", updateProgress, { signal });
  form.addEventListener("change", updateProgress, { signal });
  bindConditionalFields(signal);
  bindGeography(urls, signal);
  bindAge(signal);
  bindSinCuil(signal);
  return () => controller.abort();
}
