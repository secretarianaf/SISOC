/* eslint-disable react-refresh/only-export-components -- the module exports the page-script helpers (navigation, POST) with the modals that use them. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { record, text, webClient } from "./MainFrame";
import { useModalTabTrap } from "./nativeParity";
import { Control, initialValues, type Field, type FormValues } from "./vatFormShared";
import { vatNavigation } from "./vatShared";

/**
 * The scripts of `comision_detail.html` that act on the page: the Bootstrap modals (`ci-modal`), the JSON POSTs of the
 * quick enrolment and of the new teacher, and the full-page reload that follows a POST with redirect.
 */
export const comisionNav = {
  assign: (url: string) => vatNavigation.assign(url),
  reload: () => window.location.reload(),
};

/**
 * The native POST answers with a redirect to the detail page (`#tab` for the batch and the results). A hash-only change
 * would not reload the page, so it sets the hash and reloads, like the native «Cancelar» of the results.
 */
export function goTo(url: string) {
  const target = new URL(url, window.location.href);
  if (target.hash && target.pathname + target.search === window.location.pathname + window.location.search) {
    window.location.hash = target.hash;
    comisionNav.reload();
  } else comisionNav.assign(url);
}

/** A POST whose JSON body is read whatever the status (`fetch(...).then(response.json())` of the native scripts). */
export async function postJson(endpoint: string, body: URLSearchParams): Promise<{ status: number; data: unknown }> {
  try {
    const response = await webClient.post(endpoint, body, { validateStatus: () => true });
    return { status: response.status, data: response.data };
  } catch {
    return { status: 0, data: null };
  }
}

/** `error.message || fallback`, replaced by the joined field errors when the body has them (the native `catch`). */
export function errorMessage(data: unknown, fallback: string) {
  let message = record(data) && text(data.message) && data.message ? data.message : fallback;
  if (record(data) && record(data.errors)) {
    const parts = Object.values(data.errors).map((messages) => (Array.isArray(messages) ? messages.join(" ") : ""));
    if (parts.length) message = parts.join(" ");
  }
  return message;
}

type Alert = { level: "warning" | "danger"; message: string } | null;
const ALL_CONTROLS = "button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])";

/** `modal fade ci-modal` opened in place (the native one stays at the end of the content). */
function CiModal({ id, close, busy = false, size, children }: { id: string; close: () => void; busy?: boolean; size: string; children: ReactNode }) {
  const modal = useRef<HTMLDivElement>(null);
  useModalTabTrap(modal, close, { busy, lockScroll: false, controls: ALL_CONTROLS });
  return <>
    <div className="modal-backdrop fade show" />
    <div ref={modal} className="modal fade ci-modal show d-block" id={id} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={`${id}Label`}
      onClick={(e) => { if (e.target === e.currentTarget && !busy) close(); }}>
      <div className={`modal-dialog${size}`}>{children}</div>
    </div>
  </>;
}

const Header = ({ id, title, close }: { id: string; title: string; close: () => void }) => (
  <div className="modal-header">
    <h5 className="modal-title" id={`${id}Label`}>{title}</h5>
    <button type="button" className="btn-close" aria-label="Close" onClick={close} />
  </div>
);

/** `#modalInscriptosLote`: the confirmation of the batch accept/reject. */
export function LoteModal({ resumen, detalle, close, confirm }: { resumen: string; detalle: string; close: () => void; confirm: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  return (
    <CiModal id="modalInscriptosLote" close={close} busy={busy} size=" modal-dialog-centered">
      <div className="modal-content">
        <Header id="modalInscriptosLote" title="Confirmar acción" close={close} />
        <div className="modal-body">
          <p className="mb-2" id="inscriptosLoteResumen">{resumen}</p>
          <p className="text-muted small mb-0" id="inscriptosLoteDetalle">{detalle}</p>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
          <button type="button" className="btn btn-primary" id="inscriptosLoteConfirmar" disabled={busy}
            onClick={() => { setBusy(true); void confirm().finally(() => setBusy(false)); }}>{busy ? "Procesando..." : "Confirmar"}</button>
        </div>
      </div>
    </CiModal>
  );
}

type Citizen = { id: number; text: string };
const citizensValid = (v: unknown): v is { results: Citizen[] } => record(v) && Array.isArray(v.results) && v.results.every((c) => record(c) && typeof c.id === "number" && text(c.text));

/** `#modalInscripcionRapida`: search a citizen by document or create one, then enrol it in the commission. */
export function RapidaModal({ comision, endpoint, fields, close }: { comision: number; endpoint: string; fields: Field[]; close: () => void }) {
  const [tipoBusqueda, setTipoBusqueda] = useState("DNI");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Citizen[] | null>(null);
  const [selected, setSelected] = useState<Citizen | null>(null);
  const [quick, setQuick] = useState(false);
  const [values, setValues] = useState<FormValues>(() => initialValues(fields));
  const [observaciones, setObservaciones] = useState("");
  const [alert, setAlert] = useState<Alert>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const reset = () => { setSelected(null); setResults(null); setQuick(false); setAlert(null); };
  const field = (name: string) => fields.find((f) => f.name === name) as Field;
  const set = (name: string, value: string | boolean) => setValues((v) => ({ ...v, [name]: value }));
  const pasaporte = tipoBusqueda === "PASAPORTE";

  async function buscar() {
    const term = pasaporte ? query.trim().toUpperCase().replace(/\s/g, "") : query.trim();
    reset();
    if (pasaporte) {
      if (!/^[A-Z0-9]{6,15}$/.test(term)) { setAlert({ level: "warning", message: "Ingrese un pasaporte de 6 a 15 caracteres alfanuméricos." }); return; }
    } else if (!/^\d{7,}$/.test(term)) { setAlert({ level: "warning", message: "Ingrese un documento numérico de al menos 7 dígitos." }); return; }
    try {
      const response = await webClient.get("ciudadanos/buscar/", { params: { q: term, tipo_documento: tipoBusqueda } });
      const found = citizensValid(response.data) ? response.data.results : [];
      if (found.length) setResults(found);
      else {
        // The new citizen inherits the searched document type and number.
        setQuick(true);
        setValues((v) => ({ ...v, documento: term, tipo_documento: tipoBusqueda }));
      }
    } catch {
      setAlert({ level: "danger", message: "No se pudo buscar ciudadanos en este momento." });
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setAlert(null);
    const body = new URLSearchParams({ comision: String(comision), ciudadano_id: selected ? String(selected.id) : "" });
    for (const f of fields) body.append(f.name, String(values[f.name] ?? ""));
    body.append("observaciones", observaciones);
    const { status, data } = await postJson(endpoint, body);
    if (status >= 200 && status < 300 && record(data) && data.ok === true) comisionNav.reload();
    else setAlert({ level: "danger", message: errorMessage(data, "No se pudo completar la inscripción.") });
    busyRef.current = false;
    setBusy(false);
  }

  const quickField = (name: string, label: string) => {
    const f = field(name);
    return <div className="col-md-6">
      <label htmlFor={f.id} className="form-label">{label}</label>
      <Control f={f} state={values} set={set} />
    </div>;
  };
  return (
    <CiModal id="modalInscripcionRapida" close={close} busy={busy} size=" modal-lg modal-dialog-centered">
      <div className="modal-content">
        <Header id="modalInscripcionRapida" title="Inscribir ciudadano" close={close} />
        <form id="formInscripcionRapida" method="post" noValidate onSubmit={(e) => void submit(e)}>
          <input type="hidden" name="comision" value={comision} />
          <input type="hidden" name="ciudadano_id" id="inscripcionCiudadanoId" value={selected?.id ?? ""} readOnly />
          <div className="modal-body">
            <div id="inscripcionRapidaAlert" className={alert ? `alert alert-${alert.level}` : "alert d-none"} role="alert">{alert?.message ?? ""}</div>
            <div className="border rounded-3 p-3 mb-3">
              <label htmlFor="inscripcionDocumentoSearch" className="form-label fw-semibold">Buscar por documento</label>
              <div className="input-group">
                <select className="form-select flex-grow-0 w-auto" id="inscripcionTipoDocumentoSearch" aria-label="Tipo de documento a buscar" value={tipoBusqueda}
                  onChange={(e) => { setTipoBusqueda(e.target.value); reset(); }}>
                  <option value="DNI">DNI</option>
                  <option value="PASAPORTE">Pasaporte</option>
                </select>
                <input type="text" className="form-control" id="inscripcionDocumentoSearch" value={query}
                  placeholder={pasaporte ? "Ingrese pasaporte (6 a 15 caracteres)" : "Ingrese DNI (mín. 7 dígitos)"}
                  onChange={(e) => { setQuery(e.target.value); reset(); }}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void buscar(); } }} />
                <button type="button" className="btn btn-outline-secondary" id="inscripcionBuscarBtn" onClick={() => void buscar()}>Buscar</button>
              </div>
              <div className="form-text">Se buscará el ciudadano por número de documento.</div>
            </div>
            <div id="inscripcionSelectedCitizen" className={`alert alert-success${selected ? "" : " d-none"}`}>{selected ? `Ciudadano seleccionado: ${selected.text}` : ""}</div>
            <div id="inscripcionSearchResults" className={`list-group mb-3${results ? "" : " d-none"}`}>
              {results?.map((c) => <button key={c.id} type="button" className="list-group-item list-group-item-action"
                onClick={() => { setSelected(c); setResults(null); setQuick(false); setAlert(null); }}>{c.text}</button>)}
            </div>
            <div id="inscripcionNoResults" className={`alert alert-info mb-3${quick ? "" : " d-none"}`}>
              No se encontraron coincidencias. Completá el formulario corto para crear el ciudadano e inscribirlo.
            </div>
            <div id="inscripcionQuickCitizenSection" className={`border rounded-3 p-3${quick ? "" : " d-none"}`}>
              <h6 className="mb-3">Crear ciudadano nuevo</h6>
              <div className="row g-3">
                {quickField("apellido", "Apellido")}
                {quickField("nombre", "Nombre")}
                {quickField("tipo_documento", "Tipo de documento")}
                {quickField("documento", "Documento")}
                {quickField("fecha_nacimiento", "Fecha de Nacimiento")}
                {quickField("sexo", "Sexo")}
              </div>
            </div>
            <div className="mt-3">
              <label htmlFor="inscripcionObservaciones" className="form-label">Observaciones</label>
              <textarea className="form-control" id="inscripcionObservaciones" name="observaciones" rows={3} value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Inscribiendo..." : "Inscribir"}</button>
          </div>
        </form>
      </div>
    </CiModal>
  );
}

export type Profesor = { id: number; text: string };
const profesorValid = (v: unknown): v is Profesor => record(v) && typeof v.id === "number" && text(v.text);

/** `#modalProfesorNuevo`: direct creation of a teacher (no identity validation); the created one is selected in the acta. */
export function ProfesorModal({ endpoint, fields, close, created }: { endpoint: string; fields: Field[]; close: () => void; created: (p: Profesor) => void }) {
  const [values, setValues] = useState<FormValues>(() => initialValues(fields));
  const [alert, setAlert] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const set = (name: string, value: string | boolean) => setValues((v) => ({ ...v, [name]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setAlert(null);
    const body = new URLSearchParams();
    for (const f of fields) body.append(f.name, String(values[f.name] ?? ""));
    const { status, data } = await postJson(endpoint, body);
    if (status >= 200 && status < 300) {
      if (record(data) && profesorValid(data.profesor)) created(data.profesor);
      close();
      return;
    }
    setAlert(errorMessage(data, "No se pudo dar de alta al profesor."));
    busyRef.current = false;
    setBusy(false);
  }
  return (
    <CiModal id="modalProfesorNuevo" close={close} busy={busy} size=" modal-dialog-centered">
      <div className="modal-content">
        <Header id="modalProfesorNuevo" title="Agregar profesor" close={close} />
        <form id="formProfesorNuevo" method="post" onSubmit={(e) => void submit(e)}>
          <div className="modal-body">
            <div id="profesorNuevoAlert" className={alert ? "alert alert-danger" : "alert d-none"} role="alert">{alert ?? ""}</div>
            <p className="text-muted small">El alta es directa: no se valida la identidad contra RENAPER.</p>
            <div className="row g-3">
              {fields.map((f) => <div key={f.name} className="col-md-6">
                <label htmlFor={f.id} className="form-label fw-bold">{f.label}{" "}{f.attrs.required !== undefined && <span className="text-danger">*</span>}</label>
                <Control f={f} state={values} set={set} />
              </div>)}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Guardando..." : "Guardar profesor"}</button>
          </div>
        </form>
      </div>
    </CiModal>
  );
}

/** Debounced teacher search of the acta (`profesorBuscador`): 250 ms, two characters, Enter searches now. */
export function useProfesorSearch(endpoint: string) {
  const [items, setItems] = useState<Profesor[] | null>(null);
  const timer = useRef<number | null>(null);
  const hide = () => setItems(null);
  async function run(query: string) {
    const term = query.trim();
    if (term.length < 2) { hide(); return; }
    try {
      const response = await webClient.get(endpoint, { params: { q: term } });
      const results = record(response.data) && Array.isArray(response.data.results) ? response.data.results.filter(profesorValid) : [];
      setItems(results);
    } catch { hide(); }
  }
  const schedule = (query: string) => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void run(query), 250);
  };
  const now = (query: string) => { if (timer.current) window.clearTimeout(timer.current); void run(query); };
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);
  return { items, hide, schedule, now };
}
