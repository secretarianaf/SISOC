import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { CanonicalError, internal, loadProjection, sendNative } from "./transport";

type Message = { level: string; text: string };
type Metrics = { total_asignado: number; usados: number; disponibles: number; fuera: number };
type DashboardRow = {
  provincia: { id: number; nombre: string };
  total_asignado: number | null; usados: number | null; disponibles: number | null; fuera: number | null;
  url: string;
};
type DashboardData = { version: number; rows: DashboardRow[]; urls: { expedientes: string }; messages: Message[] };

type Person = {
  id: number; documento: string; nombre: string; apellido: string;
  revision_tecnico: string; resultado_sintys: string; estado_cupo: string; es_titular_activo: boolean;
};
type Action = { kind: "suspender" | "reactivar" | "baja"; url: string };
type Legajo = Person & { expediente: string; actions: Action[] };
type Movimiento = {
  id: number; fecha: string; tipo: string; delta: number; motivo: string | null; usuario: string;
  expediente: string; legajo: Person | null;
};
type FormField = { name: string; label: string; required: boolean };
type ProvinceData = {
  version: number;
  provincia: { id: number; nombre: string };
  metrics: Metrics | null;
  ocupados: Legajo[]; suspendidos: Legajo[]; lista_espera: Legajo[];
  movimientos: Movimiento[];
  forms: { baja: FormField; suspender: FormField };
  urls: { dashboard: string; config: string; pagos: string; crear_pago: string };
  csrf_token: string;
  messages: Message[];
};

type Alert = { kind: "success" | "warning" | "danger"; text: string };

const STYLE = `
.canonical-cupos{max-width:1400px;margin:auto;padding:1rem;font-family:inherit}
.canonical-cupos h1{font-size:1.5rem;margin:.5rem 0}
.canonical-cupos button,.canonical-cupos input,.canonical-cupos textarea{font:inherit;max-width:100%}
.canonical-cupos button,.canonical-cupos .cc-btn{display:inline-block;padding:.4rem .75rem;border:1px solid #1263b5;border-radius:4px;background:#fff;color:#0b4d8f;cursor:pointer;text-decoration:none;margin:.15rem}
.canonical-cupos button.cc-primary{background:#1263b5;color:#fff}
.canonical-cupos button.cc-danger{border-color:#b02a37;color:#b02a37}
.canonical-cupos button.cc-warning{border-color:#996c00;color:#6b4b00}
.canonical-cupos button.cc-success,.canonical-cupos .cc-btn.cc-success{border-color:#157347;color:#0f5132}
.canonical-cupos button:disabled{opacity:.6;cursor:not-allowed}
.canonical-cupos :focus-visible{outline:3px solid #1263b5;outline-offset:2px}
.cc-header{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:space-between;align-items:center}
.cc-actions{display:flex;flex-wrap:wrap;gap:.25rem;align-items:center}
.cc-actions form{display:inline}
.cc-breadcrumb ol{display:flex;gap:.4rem;list-style:none;padding:0;margin:0}
.cc-breadcrumb li+li::before{content:"/";margin-right:.4rem;color:#555}
.cc-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.75rem;margin:1rem 0}
.cc-metric{border:1px solid #d0d5dc;border-radius:6px;padding:.75rem}
.cc-metric div:first-child{color:#555;font-size:.875rem}
.cc-metric div:last-child{font-size:1.5rem;font-weight:600}
.cc-alert{padding:.75rem;border-radius:4px;margin:.5rem 0;border:1px solid}
.cc-alert-success{background:#d1e7dd;border-color:#a3cfbb;color:#0a3622}
.cc-alert-warning{background:#fff3cd;border-color:#ffe69c;color:#664d03;display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.5rem}
.cc-alert-danger,.cc-alert-error{background:#f8d7da;border-color:#f1aeb5;color:#58151c}
.cc-alert-info{background:#cff4fc;border-color:#9eeaf9;color:#055160}
.cc-card{border:1px solid #d0d5dc;border-radius:6px;margin-top:1rem}
.cc-card-header{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:space-between;align-items:center;padding:.6rem .75rem;background:#212529;color:#fff;border-radius:6px 6px 0 0}
.cc-card-header h2{font-size:1rem;margin:0}
.cc-card-header input{padding:.3rem .5rem;min-width:min(260px,100%)}
.cc-scroll{overflow-x:auto}
.canonical-cupos table{width:100%;border-collapse:collapse}
.canonical-cupos th,.canonical-cupos td{padding:.55rem .6rem;text-align:left;border-bottom:1px solid #d0d5dc;white-space:nowrap}
.canonical-cupos thead th{background:#212529;color:#fff}
.canonical-cupos .cc-num{text-align:right}
.cc-empty{text-align:center!important;color:#555}
.cc-badge{display:inline-block;padding:.15rem .45rem;border-radius:4px;font-size:.8rem;font-weight:600;background:#6c757d;color:#fff}
.cc-badge-success{background:#157347}.cc-badge-danger{background:#b02a37}.cc-badge-primary{background:#1263b5}.cc-badge-warning{background:#ffc107;color:#212529}
.cc-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:flex-start;justify-content:center;padding:1rem;overflow-y:auto;z-index:1000}
.cc-dialog{background:#fff;border-radius:6px;width:min(500px,100%);max-height:calc(100vh - 2rem);overflow:auto}
.cc-dialog.cc-wide{width:min(1140px,100%)}
.cc-dialog header,.cc-dialog footer{display:flex;justify-content:space-between;align-items:center;gap:.5rem;padding:.75rem 1rem}
.cc-dialog header h2{font-size:1.15rem;margin:0}
.cc-dialog footer{justify-content:flex-end;border-top:1px solid #d0d5dc}
.cc-dialog .cc-body{padding:1rem}
.cc-dialog label{display:block;margin-bottom:.35rem}
.cc-dialog input,.cc-dialog textarea{width:100%;padding:.4rem;box-sizing:border-box}
.cc-muted{color:#555;font-size:.875rem}
`;

function badgeKind(value: string, map: Record<string, string>) {
  return `cc-badge cc-badge-${map[value] ?? "secondary"}`;
}
const REVISION = { APROBADO: "success", RECHAZADO: "danger" };
const SINTYS = { MATCH: "success", NO_MATCH: "danger" };
const ESTADO = { DENTRO: "primary", FUERA: "warning" };
const TIPO = { ALTA: "success", BAJA: "danger", SUSPENDIDO: "warning" };

function useProjection<T extends { version: number }>() {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    loadProjection<T>(undefined, controller.signal)
      .then((body) => {
        if (body.version !== 1) throw new Error("La pantalla no es compatible con esta versión.");
        setData(body);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setError(cause instanceof CanonicalError || cause instanceof Error ? cause.message : "No se pudo cargar la pantalla.");
      });
    return () => controller.abort();
  }, []);
  return { data, error };
}

function DjangoMessages({ messages }: { messages: Message[] }) {
  if (!messages.length) return null;
  return <div aria-live="polite">{messages.map((message, index) => (
    <div key={index} role={message.level === "error" ? "alert" : "status"} className={`cc-alert cc-alert-${message.level}`}>{message.text}</div>
  ))}</div>;
}

function Loading({ title, error }: { title: string; error: string }) {
  return <main className="canonical-cupos"><style>{STYLE}</style><h1>{title}</h1>
    {error ? <p role="alert">{error}</p> : <p role="status">Cargando…</p>}</main>;
}

const dash = (value: number | null) => value ?? "—";

export function CuposScreen() {
  const { data, error } = useProjection<DashboardData>();
  if (!data) return <Loading title="Cupos por provincia" error={error} />;
  return <main className="canonical-cupos">
    <style>{STYLE}</style>
    <nav aria-label="Ruta de navegación" className="cc-breadcrumb"><ol>
      <li><a href={internal(data.urls.expedientes)}>Expedientes</a></li>
      <li aria-current="page">Cupos</li>
    </ol></nav>
    <h1>Cupos por provincia</h1>
    <DjangoMessages messages={data.messages} />
    <div className="cc-card"><div className="cc-scroll" role="region" aria-label="Cupos por provincia" tabIndex={0}>
      <table>
        <thead><tr>
          <th scope="col">Provincia</th><th scope="col" className="cc-num">Total asignado</th><th scope="col" className="cc-num">Usados</th>
          <th scope="col" className="cc-num">Disponibles</th><th scope="col" className="cc-num">Fuera de cupo</th><th scope="col" className="cc-num">Acciones</th>
        </tr></thead>
        <tbody>
          {data.rows.map((row) => <tr key={row.provincia.id}>
            <td>{row.provincia.nombre}</td>
            <td className="cc-num">{row.total_asignado !== null ? row.total_asignado : <span className="cc-badge">Sin configurar</span>}</td>
            <td className="cc-num">{dash(row.usados)}</td>
            <td className="cc-num">{dash(row.disponibles)}</td>
            <td className="cc-num">{dash(row.fuera)}</td>
            <td className="cc-num"><a className="cc-btn" href={internal(row.url)} aria-label={`Ver cupo de ${row.provincia.nombre}`}>Ver</a></td>
          </tr>)}
          {data.rows.length === 0 && <tr><td colSpan={6} className="cc-empty">No hay provincias para mostrar.</td></tr>}
        </tbody>
      </table>
    </div></div>
  </main>;
}

function Modal({ title, wide, onClose, children, footer, onSubmit }: {
  title: string; wide?: boolean; onClose: () => void; children: ReactNode; footer: ReactNode; onSubmit?: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const titleId = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const target = ref.current?.querySelector<HTMLElement>("input, textarea") ?? ref.current;
    target?.focus();
    return () => previous?.focus?.();
  }, []);
  const keyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") { event.stopPropagation(); onClose(); return; }
    if (event.key !== "Tab" || !ref.current) return;
    // Keep keyboard focus inside the modal dialog.
    const focusable = Array.from(ref.current.querySelectorAll<HTMLElement>("button:not(:disabled), input, textarea, a[href], [tabindex='0']"));
    if (!focusable.length) return;
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };
  const content = <>
    <header><h2 id={titleId}>{title}</h2><button type="button" onClick={onClose} aria-label="Cerrar">×</button></header>
    <div className="cc-body">{children}</div>
    <footer>{footer}</footer>
  </>;
  return <div className="cc-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className={`cc-dialog${wide ? " cc-wide" : ""}`} onKeyDown={keyDown}>
      {onSubmit ? <form onSubmit={onSubmit} noValidate>{content}</form> : content}
    </div>
  </div>;
}

type TableConfig = { revision?: boolean; resultado?: boolean; activo?: boolean; actions?: boolean };

function matches(row: Legajo, query: string) {
  const q = query.trim().toLowerCase();
  return !q || [row.documento, row.nombre, row.apellido, row.expediente].some((value) => value.toLowerCase().includes(q));
}

const ACTION_LABEL = { suspender: "Suspender", reactivar: "Reactivar", baja: "Baja" } as const;
const ACTION_CLASS = { suspender: "cc-warning", reactivar: "cc-success", baja: "cc-danger" } as const;

function CupoTable({ title, filterLabel, rows, empty, config, disabled, onAction }: {
  title: string; filterLabel: string; rows: Legajo[]; empty: string; config: TableConfig; disabled: boolean;
  onAction: (row: Legajo, action: Action) => void;
}) {
  const [query, setQuery] = useState("");
  const filterId = useId();
  const visible = rows.filter((row) => matches(row, query));
  const columns = 5 + Number(!!config.revision) + Number(!!config.resultado) + Number(!!config.activo) + Number(!!config.actions);
  return <section className="cc-card">
    <div className="cc-card-header">
      <h2>{title}</h2>
      <label htmlFor={filterId} className="visually-hidden" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>{filterLabel}</label>
      <input id={filterId} type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filtrar por CUIL, nombre o expediente" />
    </div>
    <div className="cc-scroll" role="region" aria-label={`Tabla: ${title}`} tabIndex={0}>
      <table aria-label={title}>
        <thead><tr>
          <th scope="col">CUIL</th><th scope="col">Nombre</th><th scope="col">Apellido</th><th scope="col">Expediente</th>
          {config.revision && <th scope="col">Revisión</th>}
          {config.resultado && <th scope="col">Resultado</th>}
          <th scope="col">Estado cupo</th>
          {config.activo && <th scope="col">Activo</th>}
          {config.actions && <th scope="col" className="cc-num">Acciones</th>}
        </tr></thead>
        <tbody>
          {visible.map((row) => <tr key={row.id}>
            <td>{row.documento}</td><td>{row.nombre}</td><td>{row.apellido}</td><td>{row.expediente}</td>
            {config.revision && <td><span className={badgeKind(row.revision_tecnico, REVISION)}>{row.revision_tecnico}</span></td>}
            {config.resultado && <td><span className={badgeKind(row.resultado_sintys, SINTYS)}>{row.resultado_sintys}</span></td>}
            <td><span className={badgeKind(row.estado_cupo, ESTADO)}>{row.estado_cupo}</span></td>
            {config.activo && <td><span className={`cc-badge${row.es_titular_activo ? " cc-badge-success" : ""}`}>{row.es_titular_activo ? "Sí" : "No"}</span></td>}
            {config.actions && <td className="cc-num">{row.actions.map((action) => (
              <button key={action.kind} type="button" className={ACTION_CLASS[action.kind]} disabled={disabled}
                aria-label={`${ACTION_LABEL[action.kind]} ${row.documento}`} onClick={() => onAction(row, action)}>{ACTION_LABEL[action.kind]}</button>
            ))}</td>}
          </tr>)}
          {rows.length === 0 && <tr><td colSpan={columns} className="cc-empty">{empty}</td></tr>}
        </tbody>
      </table>
    </div>
  </section>;
}

function Historico({ data, onClose }: { data: ProvinceData; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const filterId = useId();
  const q = query.trim().toLowerCase();
  const rows = data.movimientos.filter((m) => !q || (m.legajo?.documento ?? "").toLowerCase().includes(q));
  return <Modal title={`Histórico de movimientos — ${data.provincia.nombre}`} wide onClose={onClose}
    footer={<button type="button" onClick={onClose}>Cerrar</button>}>
    <div className="cc-header">
      <small className="cc-muted">Se listan altas/bajas/ajustes y estado actual de cada legajo.</small>
      <span><label htmlFor={filterId}>Filtrar histórico</label>
        <input id={filterId} type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filtrar por CUIL" /></span>
    </div>
    <div className="cc-scroll" role="region" aria-label="Histórico de movimientos" tabIndex={0}>
      <table aria-label="Histórico de movimientos">
        <thead><tr>
          {["Fecha", "CUIL", "Nombre", "Apellido", "Expediente", "Movimiento", "Motivo", "Usuario", "Revisión", "Resultado", "Estado cupo", "Activo"].map((label) => <th key={label} scope="col">{label}</th>)}
        </tr></thead>
        <tbody>
          {rows.map((m) => <tr key={m.id}>
            <td>{m.fecha}</td><td>{m.legajo?.documento}</td><td>{m.legajo?.nombre}</td><td>{m.legajo?.apellido}</td><td>{m.expediente}</td>
            <td><span className={badgeKind(m.tipo, TIPO)}>{m.tipo}</span>{m.delta ? <small className="cc-muted"> ({m.delta})</small> : null}</td>
            <td style={{ whiteSpace: "normal", wordBreak: "break-word" }}>{m.motivo ?? "-"}</td>
            <td>{m.usuario}</td>
            <td><span className={badgeKind(m.legajo?.revision_tecnico ?? "", REVISION)}>{m.legajo?.revision_tecnico}</span></td>
            <td><span className={badgeKind(m.legajo?.resultado_sintys ?? "", SINTYS)}>{m.legajo?.resultado_sintys}</span></td>
            <td><span className={badgeKind(m.legajo?.estado_cupo ?? "", ESTADO)}>{m.legajo?.estado_cupo}</span></td>
            <td><span className={`cc-badge${m.legajo?.es_titular_activo ? " cc-badge-success" : ""}`}>{m.legajo?.es_titular_activo ? "Sí" : "No"}</span></td>
          </tr>)}
          {data.movimientos.length === 0 && <tr><td colSpan={12} className="cc-empty">No hay movimientos registrados.</td></tr>}
        </tbody>
      </table>
    </div>
  </Modal>;
}

type Dialog = { kind: "config" } | { kind: "historico" } | { kind: "suspender" | "baja"; row: Legajo; url: string } | null;

const SUCCESS = {
  suspender: "Suspensión registrada y cupo actualizado.",
  baja: "Baja registrada y cupo actualizado.",
  reactivar: "Titular reactivado.",
} as const;
const FAILURE = {
  suspender: "No se pudo suspender el legajo.",
  baja: "No se pudo dar de baja el legajo.",
  reactivar: "No se pudo reactivar el legajo.",
} as const;

export function CupoProvinciaScreen() {
  const { data, error } = useProjection<ProvinceData>();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [alert, setAlert] = useState<Alert | null>(null);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [total, setTotal] = useState("");
  const [motivo, setMotivo] = useState("");
  const [dialogError, setDialogError] = useState("");

  if (!data) return <Loading title="Cupo" error={error} />;
  const disabled = pending || uncertain;

  const open = (next: Dialog) => {
    setDialogError("");
    if (next?.kind === "config") setTotal(data.metrics ? String(data.metrics.total_asignado) : "");
    if (next?.kind === "suspender" || next?.kind === "baja") setMotivo("");
    setDialog(next);
  };

  /** Posts to a native JSON endpoint; reloads like the native page on success. */
  const post = async (url: string, body: URLSearchParams, success: string, failure: string, inDialog: boolean) => {
    if (disabled) return;
    setPending(true); setAlert(null); setDialogError("");
    try {
      const response = await sendNative(url, "POST", body);
      let result: { success?: boolean; message?: string } = {};
      try { result = await response.json(); } catch { result = {}; }
      if (!response.ok || result.success === false) throw new Error(result.message || failure);
      setDialog(null);
      setAlert({ kind: "success", text: success });
      window.setTimeout(() => window.location.reload(), 700);
    } catch (cause) {
      // A transport failure after dispatch may have been committed: never retry.
      if (cause instanceof TypeError) {
        setUncertain(true);
        setAlert({ kind: "danger", text: "No se pudo confirmar el resultado. Recargue la página antes de volver a operar." });
        setDialog(null);
      } else {
        const text = cause instanceof Error ? cause.message : failure;
        if (inDialog) setDialogError(text); else setAlert({ kind: "danger", text });
      }
    } finally { setPending(false); }
  };

  const submitConfig = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (total.trim() === "" || !/^\d+$/.test(total.trim())) {
      setDialogError("Ingresá un valor de cupo válido (entero ≥ 0).");
      return;
    }
    void post(data.urls.config, new URLSearchParams({ accion: "config", total_asignado: total.trim() }),
      "Cupo actualizado correctamente.", "No se pudo guardar el cupo.", true);
  };

  const submitMotivo = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (dialog?.kind !== "suspender" && dialog?.kind !== "baja") return;
    if (!motivo.trim()) { setDialogError("Este campo es obligatorio."); return; }
    void post(dialog.url, new URLSearchParams({ motivo }), SUCCESS[dialog.kind], FAILURE[dialog.kind], true);
  };

  const onAction = (row: Legajo, action: Action) => {
    if (action.kind === "reactivar") {
      if (!window.confirm("¿Reactivar al titular suspendido?")) return;
      void post(action.url, new URLSearchParams(), SUCCESS.reactivar, FAILURE.reactivar, false);
      return;
    }
    open({ kind: action.kind, row, url: action.url });
  };

  const motivoField = dialog?.kind === "suspender" ? data.forms.suspender : data.forms.baja;
  const dialogAlert = dialogError ? <p role="alert" className="cc-alert cc-alert-danger">{dialogError}</p> : null;
  const confirmLabel = pending ? "Enviando…" : "Confirmar";

  return <main className="canonical-cupos">
    <style>{STYLE}</style>
    <nav aria-label="Ruta de navegación" className="cc-breadcrumb"><ol>
      <li><a href={internal(data.urls.dashboard)}>Cupos</a></li>
      <li aria-current="page">{data.provincia.nombre}</li>
    </ol></nav>
    <div className="cc-header">
      <h1>{data.provincia.nombre}</h1>
      <div className="cc-actions">
        <a className="cc-btn" href={internal(data.urls.dashboard)}>← Volver</a>
        <button type="button" className="cc-primary" onClick={() => open({ kind: "config" })} disabled={disabled}>Configurar cupo</button>
        <button type="button" onClick={() => open({ kind: "historico" })}>Historico</button>
        <a className="cc-btn cc-success" href={internal(data.urls.pagos)}>Ver expedientes de pago</a>
        <form action={internal(data.urls.crear_pago)} method="post">
          <input type="hidden" name="csrfmiddlewaretoken" value={data.csrf_token} />
          <button type="submit" className="cc-success" disabled={disabled}>Generar expediente de pago</button>
        </form>
      </div>
    </div>
    <DjangoMessages messages={data.messages} />
    {data.metrics ? <div className="cc-metrics">
      {([["Total asignado", data.metrics.total_asignado], ["Usados", data.metrics.usados], ["Disponibles", data.metrics.disponibles], ["Fuera de cupo", data.metrics.fuera]] as const).map(([label, value]) => (
        <div key={label} className="cc-metric"><div>{label}</div><div>{value}</div></div>
      ))}
    </div> : <div className="cc-alert cc-alert-warning">
      <span>La provincia no tiene cupo configurado.</span>
      <button type="button" className="cc-primary" onClick={() => open({ kind: "config" })} disabled={disabled}>Configurar ahora</button>
    </div>}
    <div aria-live="polite">{alert && <div role={alert.kind === "danger" ? "alert" : "status"} className={`cc-alert cc-alert-${alert.kind}`}>{alert.text}</div>}</div>
    <CupoTable title="Cupos ocupados (titulares activos)" filterLabel="Filtrar cupos ocupados" rows={data.ocupados}
      empty="No hay titulares ocupando cupo." config={{ revision: true, resultado: true, activo: true, actions: true }} disabled={disabled} onAction={onAction} />
    <CupoTable title="Suspendidos (cupo ocupado, no activos)" filterLabel="Filtrar suspendidos" rows={data.suspendidos}
      empty="No hay suspendidos." config={{ activo: true, actions: true }} disabled={disabled} onAction={onAction} />
    <CupoTable title="Lista de espera (Fuera de cupo)" filterLabel="Filtrar lista de espera" rows={data.lista_espera}
      empty="Sin lista de espera." config={{}} disabled={disabled} onAction={onAction} />

    {dialog?.kind === "config" && <Modal title={`Configurar cupo para ${data.provincia.nombre}`} onClose={() => setDialog(null)} onSubmit={submitConfig}
      footer={<><button type="button" onClick={() => setDialog(null)}>Cancelar</button><button type="submit" className="cc-primary" disabled={disabled}>{pending ? "Guardando…" : "Guardar"}</button></>}>
      {dialogAlert}
      <label htmlFor="cc-total-asignado">Total asignado</label>
      <input id="cc-total-asignado" name="total_asignado" type="number" min={0} step={1} required placeholder="Ej.: 500"
        value={total} onChange={(event) => setTotal(event.target.value)} />
    </Modal>}
    {dialog?.kind === "historico" && <Historico data={data} onClose={() => setDialog(null)} />}
    {(dialog?.kind === "suspender" || dialog?.kind === "baja") && <Modal
      title={dialog.kind === "suspender" ? "Suspender titular" : "Dar de baja titular"} onClose={() => setDialog(null)} onSubmit={submitMotivo}
      footer={<><button type="button" onClick={() => setDialog(null)}>Cancelar</button>
        <button type="submit" className={dialog.kind === "suspender" ? "cc-warning" : "cc-danger"} disabled={disabled}>{confirmLabel}</button></>}>
      {dialogAlert}
      <p className="cc-muted">{dialog.row.apellido}, {dialog.row.nombre} — CUIL {dialog.row.documento}</p>
      <label htmlFor="cc-motivo">{motivoField.label}</label>
      <textarea id="cc-motivo" name={motivoField.name} rows={2} required={motivoField.required}
        value={motivo} onChange={(event) => setMotivo(event.target.value)} />
    </Modal>}
  </main>;
}
