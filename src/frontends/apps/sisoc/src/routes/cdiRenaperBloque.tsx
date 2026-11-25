/* eslint-disable react-refresh/only-export-components -- shared module: the block component plus the hook and helpers that drive it. */
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { client, record, text } from "./cdiFrame";

/**
 * The CDI RENAPER block: `partials/renaper_bloque.html` + `static/custom/js/cdiRenaperBloques.js`.
 *
 * A block is one person of a form with four states (`agregar`, `dni`, `verificado`, `manual`).
 * The server stays the authority: it locks the identity from the signed token the lookup returns
 * (`renaper_token_<bloque>`), never from the inputs. This module only orders the screen, exactly
 * like the native script, and the lookup goes through `/api/web/cdi/renaper/<bloque>/` (always the
 * native view behind the web gate; tests stub it, never the real service).
 */
export type Modo = "agregar" | "dni" | "verificado" | "manual";
export type BloqueConfig = {
  bloque: string; url: string; modo: "dni" | "verificado" | "manual"; campos: string[]; tipo_field: string;
  tipos_con_dni: string[]; verificado: boolean; permite_cambiar: boolean; opcional: boolean; token: string;
};
export type FieldInfo = { label: string; type: string; choices?: { value: string; label: string }[] | null };
type Lock = "server" | "client";

export const bloqueValid = (v: unknown): v is BloqueConfig => record(v) && text(v.bloque) && text(v.url) &&
  ["dni", "verificado", "manual"].includes(v.modo as string) && Array.isArray(v.campos) && v.campos.every(text) &&
  text(v.tipo_field) && Array.isArray(v.tipos_con_dni) && v.tipos_con_dni.every(text) && typeof v.verificado === "boolean" &&
  typeof v.permite_cambiar === "boolean" && typeof v.opcional === "boolean" && text(v.token);

/** What the block needs of its form: the field holding the DNI, the columns it governs and the locked fields. */
export type BloqueSpec = BloqueConfig & {
  dni: string;
  /** Names of every field of the block's section (`.section-body`, or the whole form). */
  scope: string[];
  /** Fields that arrive locked from the server (`data-renaper="1"`, disabled). */
  serverLocked: string[];
  textoAgregar?: string;
};
type FormIo = { get: (name: string) => string; set: (name: string, value: string) => void };

const INSTRUCCION_DNI = "Ingresá el DNI y validalo con RENAPER: los datos de identidad se completan solos.";
const COLOR_ERROR = "#f87171";
const COLOR_NEUTRAL = "#9ca3af";
const NO_ENCONTRADO = "No se encontraron datos en RENAPER.";
const SIN_RESPUESTA = "No se pudo consultar RENAPER. Intentá de nuevo.";

function focusField(name: string) {
  const input = document.getElementById(`id_${name}`) as HTMLInputElement | null;
  if (input && !input.disabled) input.focus();
}

/** `valorVisible` of the native script: select label, CUIT/CUIL with dashes, dates as dd/mm/yyyy. */
export function valorVisible(name: string, info: FieldInfo, value: string): string {
  if (info.type === "select") {
    const option = info.choices?.find((c) => c.value === value);
    return option && option.value ? option.label : "";
  }
  if (/(cuit|cuil)/.test(name)) {
    const digits = value.replace(/\D/g, "");
    if (digits.length === 11) return `${digits.slice(0, 2)}-${digits.slice(2, 10)}-${digits.slice(10)}`;
  }
  if (info.type === "date" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-");
    return `${day}/${month}/${year}`;
  }
  return value;
}

/** Props of a locked control: a select cannot be readonly, so it only loses pointer events and focus. */
export function lockProps(lock: Lock | undefined, select: boolean) {
  if (!lock) return {};
  if (lock === "server") return { disabled: true, "data-renaper": "1" };
  return select
    ? { style: { pointerEvents: "none" as const }, tabIndex: -1, "aria-readonly": "true" as const, "data-renaper": "1" }
    : { readOnly: true, "data-renaper": "1" };
}

export function useRenaperBloque(spec: BloqueSpec, io: FormIo) {
  const start: Modo = spec.opcional && spec.modo === "dni" ? "agregar" : spec.modo;
  const [modo, setModo] = useState<Modo>(start);
  const [locks, setLocks] = useState<Record<string, Lock>>(() => Object.fromEntries(spec.serverLocked.map((n) => [n, "server" as Lock])));
  const [token, setToken] = useState(spec.token);
  const [mensaje, setMensaje] = useState<{ texto: string; error: boolean } | null>(null);
  const [instruccion, setInstruccion] = useState<string | null>(null);
  const [manualVisible, setManualVisible] = useState(false);
  const [cancelarVisible, setCancelarVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [manualPorRenaper, setManualPorRenaper] = useState(false);
  const [dniAnterior, setDniAnterior] = useState("");
  const [tipoAnterior, setTipoAnterior] = useState(() => (spec.tipo_field ? io.get(spec.tipo_field) : ""));

  const say = (texto: string, error: boolean) => setMensaje({ texto, error });

  /** `liberarCampo`: unlock (and optionally clear) one field. */
  function liberar(name: string, limpiar: boolean) {
    setLocks((prev) => Object.fromEntries(Object.entries(prev).filter(([key]) => key !== name)));
    if (limpiar) io.set(name, "");
  }
  const bloquear = (name: string) => setLocks((prev) => ({ ...prev, [name]: "client" }));

  function pasarAManual() {
    // A lookup of this screen that was not saved yet is discarded whole.
    if (token) {
      setToken("");
      spec.campos.forEach((name) => { if (locks[name]) liberar(name, true); });
    }
    setMensaje(null);
    setModo("manual");
  }

  function volverAValidarDni() {
    // What was typed by hand is discarded: hidden, it would still be sent without passing RENAPER.
    spec.campos.forEach((name) => { if (name !== spec.dni) liberar(name, true); });
    setInstruccion(null);
    say("Con este tipo de documento hay que validar el DNI con RENAPER.", false);
    setModo("dni");
    focusField(spec.dni);
  }

  function agregar() {
    setModo("dni");
    focusField(spec.dni);
  }

  function manual() {
    setManualPorRenaper(true);
    pasarAManual();
  }

  function cambiar() {
    setDniAnterior(io.get(spec.dni));
    liberar(spec.dni, true);
    setCancelarVisible(true);
    setManualVisible(false);
    setInstruccion("Ingresá el DNI de la nueva persona y validalo con RENAPER.");
    setMensaje(null);
    setModo("dni");
    focusField(spec.dni);
  }

  function cancelar() {
    io.set(spec.dni, dniAnterior);
    bloquear(spec.dni);
    setCancelarVisible(false);
    setInstruccion(null);
    setMensaje(null);
    setModo("verificado");
  }

  function aplicarValores(valores: Record<string, unknown>) {
    spec.campos.forEach((name) => {
      if (Object.prototype.hasOwnProperty.call(valores, name)) {
        io.set(name, String(valores[name]));
        bloquear(name);
      } else if (locks[name]) {
        // A datum of the previous person the new one lacks stays to be completed.
        liberar(name, true);
      }
    });
  }

  async function consultar() {
    const dni = io.get(spec.dni).replace(/\D/g, "");
    if (dni.length < 7) {
      say("Ingresá un DNI de 7 u 8 dígitos.", true);
      focusField(spec.dni);
      return;
    }
    setBusy(true);
    say("Consultando RENAPER...", false);
    // The native script keeps going to the manual option unless the ficha already holds the person.
    const ofrecerManual = () => { if (!spec.verificado) setManualVisible(true); };
    try {
      const { data, status } = await client.get(`web/cdi/renaper/${spec.bloque}/`, { params: { dni }, validateStatus: () => true });
      // A refusal of the gate or the veto is not JSON of the lookup: same text as a failed request.
      if (status === 401 || status === 403 || status === 404 || status === 405) {
        say(SIN_RESPUESTA, true);
        ofrecerManual();
        return;
      }
      if (status < 200 || status >= 300 || !record(data) || data.success !== true || !record(data.valores) || !text(data.token)) {
        say((record(data) && text(data.message) && data.message) || NO_ENCONTRADO, true);
        ofrecerManual();
        return;
      }
      aplicarValores(data.valores);
      setToken(data.token);
      setCancelarVisible(false);
      setManualVisible(false);
      setInstruccion(null);
      setMensaje(null);
      setModo("verificado");
    } catch {
      say(SIN_RESPUESTA, true);
      ofrecerManual();
    } finally {
      setBusy(false);
    }
  }

  function onDniKeyDown(event: KeyboardEvent) {
    // Enter in the DNI validates instead of sending the whole form.
    if (event.key !== "Enter" || modo !== "dni") return;
    event.preventDefault();
    void consultar();
  }

  /** `change` of the document type select: no DNI means manual load; a DNI type validates again. */
  function onTipo(value: string) {
    const conDni = spec.tipos_con_dni;
    const teniaDni = !tipoAnterior || conDni.includes(tipoAnterior);
    // The empty option does not count: "Ninguna" -> empty -> DNI validates again.
    if (value) setTipoAnterior(value);
    if (value && !conDni.includes(value)) setManualPorRenaper(false);
    if (modo === "dni" && value && !conDni.includes(value)) {
      pasarAManual();
      say("Sin DNI no hay datos para consultar en RENAPER: completá los datos manualmente.", false);
    } else if (modo === "manual" && !teniaDni && conDni.includes(value) && !manualPorRenaper) {
      // The manual load was for lacking a DNI: with a DNI it validates again.
      volverAValidarDni();
    }
  }

  /** A required field of a hidden column blocks the submit silently: say so in the block. */
  function onInvalid(name: string): boolean {
    if (!spec.scope.includes(name) || !hidden(name)) return false;
    // Manual load is not opened: the person has to go through RENAPER first.
    if (modo === "agregar") setModo("dni");
    say("Falta completar esta persona: validá el DNI con RENAPER.", true);
    document.querySelector(`[data-renaper-bloque="${spec.bloque}"]`)?.scrollIntoView({ block: "center" });
    focusField(spec.dni);
    return true;
  }

  /** `setModo` of the native script: which columns of the section stay visible. */
  function hidden(name: string): boolean {
    if (!spec.scope.includes(name)) return false;
    if (modo === "agregar") return true;
    if (modo === "dni") return name !== spec.dni && name !== spec.tipo_field;
    if (modo === "verificado") return Boolean(locks[name]);
    return false;
  }

  return {
    spec, modo, token, mensaje, instruccion, manualVisible, cancelarVisible, busy, locks,
    hidden, lock: (name: string) => locks[name], onDniKeyDown, onTipo, onInvalid,
    actions: { consultar, agregar, manual, cambiar, cancelar },
  };
}
export type RenaperBloqueApi = ReturnType<typeof useRenaperBloque>;

/** `onInvalidCapture` of the form: the first block that owns the invalid field answers. */
export function handleInvalid(event: FormEvent, blocks: RenaperBloqueApi[]) {
  const name = (event.target as HTMLElement).getAttribute("name") ?? "";
  blocks.some((block) => block.onInvalid(name));
}

/** `partials/renaper_bloque.html`, with the card the native script renders in `[data-renaper-datos]`. */
export function RenaperBloque({ api, info, values }: {
  api: RenaperBloqueApi;
  info: (name: string) => FieldInfo;
  values: Record<string, string>;
}) {
  const { spec, modo } = api;
  const hiddenPanel = (panel: Modo) => modo !== panel;
  const datos = spec.campos.filter((name) => api.locks[name]).map((name) => ({
    name, label: info(name).label.replace("*", "").trim(), value: valorVisible(name, info(name), values[name] ?? "") || "—",
  }));
  return (
    <div className="renaper-bloque mb-3" data-renaper-bloque={spec.bloque} data-renaper-url={spec.url}
      data-renaper-modo={modo} data-renaper-campos={spec.campos.join(",")} data-dni-input={`id_${spec.dni}`}
      data-tipos-con-dni={spec.tipos_con_dni.join(",")} data-tipo-input={spec.tipo_field ? `id_${spec.tipo_field}` : undefined}
      data-verificado-servidor={spec.verificado ? "1" : undefined} data-permite-cambiar={spec.permite_cambiar ? "1" : undefined}
      data-opcional={spec.opcional ? "1" : undefined}>
      <input type="hidden" name={`renaper_token_${spec.bloque}`} value={api.token} />

      {spec.opcional && (
        <div data-renaper-panel="agregar" hidden={hiddenPanel("agregar")}>
          <button type="button" className="btn btn-sm btn-outline-info" data-renaper-agregar="" onClick={api.actions.agregar}>
            <i className="fas fa-plus me-1" />{spec.textoAgregar}
          </button>
        </div>
      )}

      <div data-renaper-panel="dni" hidden={hiddenPanel("dni")}>
        <p className="small mb-2" style={{ color: COLOR_NEUTRAL }} data-renaper-instruccion="">{api.instruccion ?? INSTRUCCION_DNI}</p>
        <div className="d-flex flex-wrap gap-2">
          <button type="button" className="btn btn-sm btn-info" data-renaper-consultar="" disabled={api.busy} onClick={() => void api.actions.consultar()}>
            <i className="fas fa-id-card me-1" />Validar con RENAPER
          </button>
          <button type="button" className="btn btn-sm btn-outline-light" data-renaper-manual="" hidden={!api.manualVisible} onClick={api.actions.manual}>
            <i className="fas fa-keyboard me-1" />Cargar manualmente
          </button>
          <button type="button" className="btn btn-sm btn-secondary" data-renaper-cancelar="" hidden={!api.cancelarVisible} onClick={api.actions.cancelar}>Cancelar</button>
        </div>
      </div>

      <div data-renaper-panel="manual" hidden={hiddenPanel("manual")}>
        <button type="button" className="btn btn-sm btn-outline-info" data-renaper-consultar="" disabled={api.busy} onClick={() => void api.actions.consultar()}>
          <i className="fas fa-id-card me-1" />Validar con RENAPER
        </button>
      </div>

      <div className="p-3 rounded" style={{ background: "#1f2a37", border: "1px solid #2f855a" }} data-renaper-panel="verificado" hidden={hiddenPanel("verificado")}>
        <div className="d-flex justify-content-between align-items-center mb-2">
          <span className="badge bg-success"><i className="fas fa-id-card me-1" />Verificado por RENAPER</span>
          {spec.permite_cambiar && (
            <button type="button" className="btn btn-sm btn-outline-light" data-renaper-cambiar="" onClick={api.actions.cambiar}>
              <i className="fas fa-user-edit me-1" />Cambiar persona
            </button>
          )}
        </div>
        <dl className="row mb-0" data-renaper-datos="">
          {modo === "verificado" && datos.map((d) => (
            <div key={d.name} className="col-md-3 mb-2">
              <dt className="small fw-normal" style={{ color: COLOR_NEUTRAL }}>{d.label}</dt>
              <dd className="mb-0" style={{ color: "#e5e7eb" }}>{d.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <small className="d-block mt-2" data-renaper-mensaje="" style={api.mensaje ? { color: api.mensaje.error ? COLOR_ERROR : COLOR_NEUTRAL } : undefined}>
        {api.mensaje?.texto}
      </small>
    </div>
  );
}
