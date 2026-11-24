/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { leerCookie } from "@sisoc/api";
import { InsumosToastList } from "../InsumosToast";
import { prerequisiteFromForbidden } from "../webAccess";
import { internal, postForm, record, renderMain, text, useMainResource, type MainState } from "./MainFrame";
import { ExpedientesListContent, expedientesNavigation, listValid, messagesValid, type Message } from "./expedientesPagosList";
import type { RouteDefinition } from "./types";
import { restartKeyboardFromTop } from "./userImport";

/**
 * EX01 payment files of a comedor (`/expedientespagos/expedientespagos/`):
 * list, detail, create, edit and logical delete with the native templates'
 * markup. Data and every write go through `/api/web/comedores/expedientespagos/`,
 * which runs the native views. React never computes totals: every amount is
 * the text the native page shows.
 */
type Mode = "list" | "detail" | "create" | "edit" | "delete";
type Params = { mode: Mode; id: string };
type Field = {
  name: string; label: string; type: "text" | "number" | "date" | "textarea"; required: boolean;
  max_length: string | null; step: string | null; value: string; errors: string[];
};
type FormData_ = { comedor_id: number; fields: Field[]; cancel_url: string };
const DETAIL_KEYS = [
  "expediente_pago", "expediente_convenio", "mes_pago", "mes_convenio", "ano", "organizacion_creacion", "anexo",
  "total_prestaciones", "gastos_accesorios", "total", "numero_orden_pago", "fecha_creacion", "fecha_pago_al_banco",
  "fecha_acreditacion", "observaciones",
  ...["desayuno", "almuerzo", "merienda", "cena"].flatMap((c) => [`prestaciones_mensuales_${c}`, `monto_mensual_${c}`]),
] as const;
type DetailData = {
  id: number; comedor_id: number | null; expediente: Record<(typeof DETAIL_KEYS)[number], string>;
  list_url: string; update_url: string; delete_url: string; messages: Message[];
};
type Cascade = {
  total_afectados: number; total_baja_logica: number; total_borrado_fisico: number;
  desglose_por_modelo: { modelo: string; cantidad: number; modo: string; ejemplos: string[] }[];
};
type DeleteData = { id: number; expediente_pago: string; breadcrumb_label: string; message: string; cascade_preview: Cascade | null; cancel_url: string };

const API = "web/comedores/expedientespagos/";
const BASE = "/expedientespagos/expedientespagos/";
const TYPES = ["text", "number", "date", "textarea"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const nullableText = (v: unknown) => v === null || text(v);

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && text(f.label) && TYPES.includes(f.type as string) &&
  typeof f.required === "boolean" && nullableText(f.max_length) && nullableText(f.step) && text(f.value) &&
  Array.isArray(f.errors) && f.errors.every(text);
export const formValid = (v: unknown): v is FormData_ => record(v) && int(v.comedor_id) && internal(v.cancel_url) &&
  Array.isArray(v.fields) && v.fields.length === 23 && v.fields.every(fieldValid);
export const detailValid = (v: unknown): v is DetailData => record(v) && int(v.id) && (v.comedor_id === null || int(v.comedor_id)) &&
  record(v.expediente) && DETAIL_KEYS.every((k) => text((v.expediente as Record<string, unknown>)[k])) &&
  internal(v.list_url) && internal(v.update_url) && internal(v.delete_url) && messagesValid(v.messages);
const cascadeValid = (v: unknown): v is Cascade => record(v) && int(v.total_afectados) && int(v.total_baja_logica) && int(v.total_borrado_fisico) &&
  Array.isArray(v.desglose_por_modelo) && v.desglose_por_modelo.every((d) => record(d) && text(d.modelo) && int(d.cantidad) && text(d.modo) &&
    Array.isArray(d.ejemplos) && d.ejemplos.every(text));
export const deleteValid = (v: unknown): v is DeleteData => record(v) && int(v.id) && text(v.expediente_pago) && text(v.breadcrumb_label) &&
  text(v.message) && (v.cascade_preview === null || cascadeValid(v.cascade_preview)) && internal(v.cancel_url);

/** `{% block app-header %}`: the template's row replaces the shell's empty header row (its classes and children). */
function AppHeader({ className, children }: { className: string; children: ReactNode }) {
  const [target, setTarget] = useState<Element | null>(null);
  useLayoutEffect(() => {
    const row = document.querySelector(".app-content-header > .container-fluid:last-child > .row");
    if (!row) return;
    const previous = row.className;
    row.className = className;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the portal target is a shell DOM node, known only once it is mounted.
    setTarget(row);
    return () => { row.className = previous; };
  }, [className]);
  return target ? createPortal(children, target) : null;
}

/** The detail's «Acciones» Bootstrap dropdown, opened and closed by React. */
function ActionsMenu({ data }: { data: DetailData }) {
  const [open, setOpen] = useState(false);
  const group = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent) => { if (!group.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("click", outside); document.removeEventListener("keydown", escape); };
  }, [open]);
  return <div className="col-12 col-lg d-flex flex-wrap justify-content-start justify-content-lg-end gap-2 align-items-center">
    <div ref={group} className="btn-group">
      <button className={`btn btn-md dropdown-toggle${open ? " show" : ""}`} type="button" data-bs-toggle="dropdown" aria-expanded={open}
        onClick={() => setOpen((v) => !v)}>
        <i className="bi bi-list me-1" />Acciones{" "}
      </button>
      <ul className={`dropdown-menu dropdown-menu-end${open ? " show" : ""}`} {...(open ? { "data-bs-popper": "static" } : {})}>
        <li><a className="dropdown-item" href={data.update_url}><i className="bi bi-pencil me-1" />Editar</a></li>
        <li><a className="dropdown-item text-danger" href={data.delete_url}><i className="bi bi-trash me-1" />Eliminar</a></li>
      </ul>
    </div>
    </div>;
}

/** A dark header cell with the template's `!important` inline colors. */
function DarkCell({ children, scope = "col", end = false }: { children: ReactNode; scope?: string; end?: boolean }) {
  const paint = useCallback((el: HTMLTableCellElement | null) => {
    if (!el) return;
    el.style.setProperty("background-color", "#3d4f63", "important");
    el.style.setProperty("border-bottom", "2px solid #e7ba61", "important");
  }, []);
  return <th ref={paint} scope={scope} className={end ? "text-end" : undefined}>{children}</th>;
}

function Item({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return <div className={wide ? "col-12" : "col-md-4"}>
    <small className="text-muted d-block">{label}</small>
    <span className="fw-semibold">{value}</span>
  </div>;
}

const Spacer = () => <div className="col-md-4 d-none d-md-block" />;
const Rule = () => <div className="col-12"><hr className="my-0" /></div>;
const MEALS: [string, string][] = [["desayuno", "Desayuno"], ["almuerzo", "Almuerzo"], ["merienda", "Merienda"], ["cena", "Cena"]];

function Detail({ data }: { data: DetailData }) {
  const e = data.expediente;
  return <>
    <InsumosToastList messages={data.messages} />
    <AppHeader className="row g-2 align-items-center"><ActionsMenu data={data} /></AppHeader>
    <div className="container-fluid">
      <div className="card mb-3">
        <div className="card-header"><h3 className="card-title">Información del Expediente</h3></div>
        <div className="card-body"><div className="row gy-3">
          <Item label="Expediente de Pago" value={e.expediente_pago} />
          <Item label="Expediente del Convenio" value={e.expediente_convenio} />
          <Spacer />
          <Item label="Mes de Pago" value={e.mes_pago} />
          <Item label="Mes de Convenio" value={e.mes_convenio} />
          <Item label="Año" value={e.ano} />
          <Item label="Organización" value={e.organizacion_creacion} />
          <Item label="Anexo" value={e.anexo} />
          <Spacer />
          <Rule />
          <Item label="Total Prestaciones" value={e.total_prestaciones} />
          <Item label="Gastos Accesorios 6%" value={e.gastos_accesorios} />
          <Item label="Total" value={e.total} />
          <Rule />
          <Item label="Número de Orden de Pago" value={e.numero_orden_pago} />
          <Item label="Fecha de Creación" value={e.fecha_creacion} />
          <Spacer />
          <Item label="Fecha de Pago al Banco" value={e.fecha_pago_al_banco} />
          <Item label="Fecha de Acreditación" value={e.fecha_acreditacion} />
          <Spacer />
          {e.observaciones && <Item label="Observaciones" value={e.observaciones} wide />}
        </div></div>
      </div>
      <div className="card mb-3">
        <div className="card-header"><h3 className="card-title">Prestaciones Mensuales</h3></div>
        <div className="card-body p-0">
          <table className="table table-bordered table-sm mb-0">
            <thead><tr><DarkCell>Tipo</DarkCell><DarkCell end>Prestaciones</DarkCell><DarkCell end>Monto Mensual</DarkCell></tr></thead>
            <tbody>
              {MEALS.map(([key, label]) => <tr key={key}>
                <td>{label}</td>
                <td className="text-end">{e[`prestaciones_mensuales_${key}` as keyof typeof e]}</td>
                <td className="text-end">{e[`monto_mensual_${key}` as keyof typeof e]}</td>
              </tr>)}
            </tbody>
            <tfoot><tr><DarkCell scope="row">Total</DarkCell><DarkCell end>—</DarkCell><DarkCell end>{e.total}</DarkCell></tr></tfoot>
          </table>
        </div>
      </div>
    </div>
  </>;
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function Uncertain({ back }: { back: string }) {
  return <p role="alert">No se pudo confirmar el resultado. Revise los expedientes antes de volver a intentar. <a href={back}>Volver</a></p>;
}

const CLASSES: Record<Field["type"], string> = {
  text: "textinput form-control", number: "numberinput form-control", date: "form-control dateinput", textarea: "textarea form-control",
};

/** One crispy-forms (Bootstrap 5) field, as `as_crispy_field` renders it. */
function FormField({ field }: { field: Field }) {
  const id = `id_${field.name}`;
  const invalid = field.errors.length > 0;
  const common = {
    name: field.name, id, defaultValue: field.value, required: field.required || undefined,
    className: `${CLASSES[field.type]}${invalid ? " is-invalid" : ""}`,
    ...(invalid ? { "aria-invalid": true, "aria-describedby": `${id}_error` } : {}),
  };
  const control = field.type === "textarea"
    ? <textarea cols={40} rows={10} {...common} />
    : <input type={field.type} maxLength={field.max_length ? Number(field.max_length) : undefined} step={field.step ?? undefined} {...common} />;
  return <div className="form-group"><div id={`div_${id}`} className="mb-3">
    <label htmlFor={id} className={`form-label${field.required ? " requiredField" : ""}`}>{field.label}{field.required && <span className="asteriskField">*</span>}</label>{" "}
    {control}
    {invalid && <>{" "}<div id={`${id}_error`} className="invalid-feedback">{field.errors.map((m, i) => <p key={i} id={`error_${i + 1}_${id}`}><strong>{m}</strong></p>)}</div></>}
  </div></div>;
}

function ExpedienteForm({ data: initial, endpoint, mode, forbidden }: { data: FormData_; endpoint: string; mode: "create" | "edit"; forbidden: (d: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [revision, setRevision] = useState(0);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const values = new FormData(event.currentTarget);
    const body = new URLSearchParams();
    for (const f of data.fields) body.append(f.name, String(values.get(f.name) ?? ""));
    const result = await postForm(endpoint, body);
    busy.current = false;
    if (result.kind === "redirect" && result.url.startsWith(BASE)) expedientesNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else if (result.kind === "invalid" && formValid(result.data)) {
      // The native view re-renders the page: create with an empty form, edit with the bound one.
      setData(result.data); setRevision((n) => n + 1);
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      restartKeyboardFromTop();
    } else setUncertain(true);
  }
  return <div className="container mt-4">
    <h1>{mode === "create" ? "Crear Expediente de Pago" : "Editar Expediente de Pago"}</h1>
    <form key={revision} method="POST" encType="multipart/form-data" onSubmit={(e) => void submit(e)}>
      <CsrfInput />
      {uncertain && <Uncertain back={data.cancel_url} />}
      <div className="row"><div className="col-md-8">
        {data.fields.map((f) => <FormField key={f.name} field={f} />)}
      </div></div>
      <div className="row"><div className="col-md-12">
        <div className="form-group mb-0 mt-3 d-flex justify-content-center">
          <a href={data.cancel_url} className="btn btn-secondary mb-3">Cancelar</a>
          <div className="d-flex justify-content-center">
            <button type="submit" className="btn btn-primary mb-3"><i className="fas fa-save me-1" /> Guardar</button>
          </div>
        </div>
      </div></div>
    </form>
  </div>;
}

function DeleteConfirm({ data, endpoint, forbidden }: { data: DeleteData; endpoint: string; forbidden: (d: unknown) => void }) {
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true;
    const result = await postForm(endpoint, new URLSearchParams());
    busy.current = false;
    if (result.kind === "redirect") expedientesNavigation.assign(result.url);
    else if (result.kind === "forbidden") forbidden(result.data);
    else setUncertain(true);
  }
  const preview = data.cascade_preview;
  // components/delete_confirm.html with the template's texts.
  return <div className="error-page mt-5 px-3"><div className="error-content">
    <h3><i className="fas fa-exclamation-triangle text-danger px-2" /> Dar de baja Expediente</h3>
    <p>{data.message} <span className="font-weight-bold">{data.expediente_pago}</span>?</p>
    {preview && <>
      <div className="alert alert-info">
        <div><strong>Total de registros afectados:</strong> {preview.total_afectados}</div>
        {preview.total_baja_logica > 0 && <div>Bajas lógicas: {preview.total_baja_logica}</div>}
        {preview.total_borrado_fisico > 0 && <div>Borrados físicos técnicos: {preview.total_borrado_fisico}</div>}
      </div>
      <div className="table-responsive mb-3"><table className="table table-sm table-striped mb-0">
        <thead><tr><th>Modelo</th><th>Cantidad</th><th>Acción</th><th>Ejemplos</th></tr></thead>
        <tbody>{preview.desglose_por_modelo.map((d, i) => <tr key={i}>
          <td>{d.modelo}</td><td>{d.cantidad}</td>
          <td>{d.modo === "baja_logica" ? "Baja lógica" : "Borrado físico técnico"}</td>
          <td>{d.ejemplos.length ? d.ejemplos.join(", ") : "-"}</td>
        </tr>)}</tbody>
      </table></div>
    </>}
    <div className="text-left">
      <form method="post" action="" onSubmit={(e) => void submit(e)}>
        <CsrfInput />
        {uncertain && <Uncertain back={data.cancel_url} />}
        <button type="submit" className="btn btn-danger btn-sm">Dar de baja</button>{" "}
        <a href={data.cancel_url} className="btn btn-secondary btn-sm">Cancelar</a>
      </form>
    </div>
  </div></div>;
}

function useForbidden<T>(setState: (s: MainState<T>) => void) {
  return (d: unknown) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) });
}

function ListPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}comedores/${id}/${window.location.search}`, listValid);
  return renderMain(state, "Cargando expedientes…", (data) => ({
    title: "Listado de Expedientes de pagos",
    breadcrumb: <ol className="breadcrumb float-sm-right"><div className="breadcrumb-item active"><a href={data.breadcrumb_url}>Expedientes de pagos</a></div></ol>,
    content: <ExpedientesListContent data={data} />,
  }));
}

function DetailPage({ id }: { id: string }) {
  const [state] = useMainResource(`${API}${id}/`, detailValid);
  return renderMain(state, "Cargando expediente…", (data) => ({
    title: "Expediente de Pago",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={data.list_url}>Expedientes de pagos</a></li>
      <li className="breadcrumb-item active">Detalle</li>
    </ol>,
    content: <Detail data={data} />,
  }));
}

function FormPage({ mode, id }: { mode: "create" | "edit"; id: string }) {
  const endpoint = mode === "create" ? `${API}comedores/${id}/crear/` : `${API}${id}/editar/`;
  const [state, setState] = useMainResource(endpoint, formValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    // The template's `title` block does not distinguish create from edit.
    title: "Crear Expediente de Pago",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <li className="breadcrumb-item"><a href={`${BASE}${data.comedor_id}/`}>Expedientes de pagos</a></li>
      <li className="breadcrumb-item active">{mode === "create" ? "Crear Expediente de Pago" : "Editar Expediente de Pago"}</li>
    </ol>,
    content: <ExpedienteForm data={data} endpoint={endpoint} mode={mode} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, deleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Acciones",
    breadcrumb: <ol className="breadcrumb float-sm-right">
      {/* The native first item links to the page itself (`href=""`). */}
      <li className="breadcrumb-item"><a href="" title="Ver listado de admisiones">Expedientes de pagos</a></li>
      <li className="breadcrumb-item "><a href={data.cancel_url} title="Ver ciudadano">{data.breadcrumb_label}</a></li>
      <li className="breadcrumb-item active">Eliminar</li>
    </ol>,
    content: <DeleteConfirm data={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

// Native URLs of `expedientespagos/urls.py` under the runtime's `expedientespagos/` include.
const PATH = /^\/expedientespagos\/expedientespagos\/([0-9]+)\/(?:(detalle|nuevo|editar|eliminar)\/)?$/;
const MODES: Record<string, Mode> = { detalle: "detail", nuevo: "create", editar: "edit", eliminar: "delete" };

export const expedientesPagosRoute: RouteDefinition<Params> = {
  name: "comedores-expedientes-pagos",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return { mode: m[2] ? MODES[m[2]] : "list", id: m[1] };
  },
  render({ mode, id }) {
    const key = `${mode}:${id}`;
    if (mode === "list") return <ListPage key={key} id={id} />;
    if (mode === "detail") return <DetailPage key={key} id={id} />;
    if (mode === "delete") return <DeletePage key={key} id={id} />;
    return <FormPage key={key} mode={mode} id={id} />;
  },
};
