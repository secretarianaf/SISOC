/* eslint-disable react-refresh/only-export-components -- the route object is registered with the CDI screens. */
import { useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { NativeToasts } from "./nativeParity";
import { client, internal, messagesValid, navigation, record, renderCdi, text, useCdiPage, type CdiMessage } from "./cdiFrame";
import type { RouteDefinition } from "./types";

type Centro = { id: number; nombre: string; url: string };
type PageData = { centro: Centro; messages: CdiMessage[] };
type History = PageData & {
  cargar_url: string | null;
  borrador_modificado: string | null;
  rows: { id: number; fecha_envio: string; enviado_por: string; url: string }[];
  page: { number: number; previous: number | null; next: number | null };
};
type Detail = PageData & {
  id: number; historial_url: string; fecha_envio: string; enviado_por: string;
  jurisdiccion: string; departamento: string;
  secciones: { id: string; titulo: string; respuestas: {
    numero: number; texto: string; subtitulo: string; valor: string | null;
    filas: { etiqueta: string; valor: string }[]; especificar: string | null;
  }[] }[];
};
type Value = string | boolean;
type Field = { nombre: string; valor: Value; opciones: [string, string][] };
type Condition = { nombre: string; valores: string[]; negar: boolean };
type Question = {
  numero: number; texto: string; subtitulo: string; nota: string; error: string | null;
  tipo: "radio" | "numero" | "checkbox" | "matriz_numerica" | "grilla";
  control: Condition | null;
  filas: { etiqueta: string; campo: Field }[];
  especificar: { etiqueta: string; control: string; valor: string; campo: Field } | null;
};
type Form = PageData & {
  codigo: string; cartel: string; es_borrador_existente: boolean;
  errores: Record<string, string>;
  secciones: { id: string; titulo: string; preguntas: Question[] }[];
};
type Values = Record<string, Value>;
type Params = { centro: string; screen: "history" | "form" | "detail"; formId?: string };

const nullableText = (v: unknown) => v === null || text(v);
const nullableNumber = (v: unknown) => v === null || Number.isInteger(v);
const arrayOf = (v: unknown, check: (item: unknown) => boolean) => Array.isArray(v) && v.every(check);

function pageValid(v: unknown): v is PageData & Record<string, unknown> {
  return record(v) && record(v.centro) && Number.isInteger(v.centro.id) &&
    text(v.centro.nombre) && internal(v.centro.url) && messagesValid(v.messages);
}
function historyValid(v: unknown): v is History {
  return pageValid(v) && (v.cargar_url === null || internal(v.cargar_url)) && nullableText(v.borrador_modificado) &&
    record(v.page) && Number.isInteger(v.page.number) && nullableNumber(v.page.previous) && nullableNumber(v.page.next) &&
    arrayOf(v.rows, (r) => record(r) && Number.isInteger(r.id) && text(r.fecha_envio) && text(r.enviado_por) && internal(r.url));
}
function detailValid(v: unknown): v is Detail {
  return pageValid(v) && Number.isInteger(v.id) && internal(v.historial_url) &&
    text(v.fecha_envio) && text(v.enviado_por) && text(v.jurisdiccion) && text(v.departamento) &&
    arrayOf(v.secciones, (s) => record(s) && text(s.id) && text(s.titulo) &&
      arrayOf(s.respuestas, (r) => record(r) && Number.isInteger(r.numero) && text(r.texto) && text(r.subtitulo) &&
        nullableText(r.valor) && nullableText(r.especificar) &&
        arrayOf(r.filas, (f) => record(f) && text(f.etiqueta) && text(f.valor))));
}
function fieldValid(v: unknown): v is Field {
  return record(v) && text(v.nombre) && (text(v.valor) || typeof v.valor === "boolean") &&
    arrayOf(v.opciones, (o) => Array.isArray(o) && o.length === 2 && o.every(text));
}
function questionValid(q: unknown): q is Question {
  if (!record(q)) return false;
  const { control, especificar } = q;
  return Number.isInteger(q.numero) && text(q.texto) && text(q.subtitulo) && text(q.nota) &&
    nullableText(q.error) && ["radio", "numero", "checkbox", "matriz_numerica", "grilla"].includes(String(q.tipo)) &&
    arrayOf(q.filas, (f) => record(f) && text(f.etiqueta) && fieldValid(f.campo)) &&
    (control === null || (record(control) && text(control.nombre) && arrayOf(control.valores, text) && typeof control.negar === "boolean")) &&
    (especificar === null || (record(especificar) && text(especificar.etiqueta) && text(especificar.control) &&
      text(especificar.valor) && fieldValid(especificar.campo)));
}
function formValid(v: unknown): v is Form {
  return pageValid(v) && text(v.codigo) && text(v.cartel) && typeof v.es_borrador_existente === "boolean" &&
    record(v.errores) && Object.values(v.errores).every(text) &&
    arrayOf(v.secciones, (s) => record(s) && text(s.id) && text(s.titulo) && arrayOf(s.preguntas, questionValid));
}

function HistoryPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, historyValid);
  return renderCdi(state, (data) => ({
    title: "Formularios de Calidad", heading: "Formularios de Calidad",
    content: <div className="container-fluid">
      <div className="d-flex flex-wrap justify-content-between gap-2 mb-3">
        <a className="btn btn-outline-secondary" href={data.centro.url}>Volver al centro</a>
        {data.cargar_url && <a className="btn btn-primary" href={data.cargar_url}>
          {data.borrador_modificado ? "Continuar borrador" : "Nuevo formulario"}
        </a>}
      </div>
      <div className="card"><div className="card-body">
        <h2 className="h4">{data.centro.nombre}</h2>
        <p className="mb-0">Historial de formularios de calidad enviados por el centro.</p>
        {data.borrador_modificado && <p className="text-warning mt-2 mb-0">Hay un borrador sin enviar, guardado el {data.borrador_modificado}.</p>}
      </div></div>
      <div className="table-responsive">
        <table className="table table-bordered table-striped">
          <thead><tr>{["ID", "Fecha de envío", "Enviado por", "Acciones"].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
          <tbody>{data.rows.map((row) => <tr key={row.id}>
            <td>{row.id}</td><td>{row.fecha_envio}</td><td>{row.enviado_por}</td>
            <td><a className="btn btn-sm btn-primary" aria-label={`Ver formulario ${row.id}`} href={row.url}>Ver</a></td>
          </tr>)}
          {!data.rows.length && <tr><td colSpan={4}>Todavía no hay formularios de calidad enviados para este centro.</td></tr>}</tbody>
        </table>
      </div>
      {(data.page.previous || data.page.next) && <nav aria-label="Paginación" className="d-flex gap-3">
        {data.page.previous && <a href={`?page=${data.page.previous}`}>Anterior</a>}
        <span>Página {data.page.number}</span>
        {data.page.next && <a href={`?page=${data.page.next}`}>Siguiente</a>}
      </nav>}
    </div>,
  }));
}

function DetailPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, detailValid);
  return renderCdi(state, (data) => {
    const title = `Formulario de Calidad #${data.id}`;
    return {
      title, heading: title,
      content: <div className="container-fluid">
        <a className="btn btn-outline-secondary mb-3" href={data.historial_url}>Ver historial</a>
        <div className="card"><div className="card-body">
          <h2 className="h4">{data.centro.nombre}</h2>
          <p>Jurisdicción {data.jurisdiccion} · Departamento {data.departamento}</p>
          <p>Enviado el {data.fecha_envio}{data.enviado_por !== "-" && ` por ${data.enviado_por}`}.</p>
          <p className="mb-0">Envío inmutable: para corregirlo, cargá un formulario nuevo.</p>
        </div></div>
        {data.secciones.map((s) => <section className="card" key={s.id}>
          <h2 className="h5 card-header bg-primary text-white">{s.titulo}</h2>
          <div className="card-body">
            {s.respuestas.map((r) => <div key={r.numero} className="mb-3">
              {r.subtitulo && <h3 className="h6 text-primary">{r.subtitulo}</h3>}
              <div className="text-muted small">{r.numero}. {r.texto}</div>
              {r.filas.length > 0 ? <dl className="mb-0">
                {r.filas.map((f) => <div className="d-flex flex-wrap gap-2" key={f.etiqueta}><dt>{f.etiqueta}:</dt><dd className="mb-0">{f.valor}</dd></div>)}
              </dl> : <div>{r.valor}{r.especificar && ` — ${r.especificar}`}</div>}
            </div>)}
          </div>
        </section>)}
      </div>,
    };
  });
}

function isVisible(condition: Condition | null, values: Values) {
  if (!condition) return true;
  const value = values[condition.nombre];
  return text(value) && value !== "" && condition.valores.includes(value) !== condition.negar;
}
function showSpecification(spec: NonNullable<Question["especificar"]>, values: Values) {
  const selected = values[spec.control];
  return selected === true || selected === spec.valor;
}
function withoutHidden(values: Values, data: Form): Values {
  const next = { ...values };
  for (const section of data.secciones) {
    for (const question of section.preguntas) {
      const visible = isVisible(question.control, next);
      if (!visible) for (const { campo } of question.filas) delete next[campo.nombre];
      if (question.especificar && (!visible || !showSpecification(question.especificar, next))) {
        delete next[question.especificar.campo.nombre];
      }
    }
  }
  return next;
}
function initialValues(data: Form) {
  const values: Values = {};
  for (const s of data.secciones) for (const q of s.preguntas) {
    for (const { campo } of q.filas) values[campo.nombre] = campo.valor;
    if (q.especificar) values[q.especificar.campo.nombre] = q.especificar.campo.valor;
  }
  return withoutHidden(values, data);
}

type FieldProps = { question: Question; values: Values; change: (name: string, value: Value) => void };

function Choice({ field, option, label, values, change }: {
  field: Field; option: string; label: string; values: Values; change: FieldProps["change"];
}) {
  return <input className="form-check-input" type="radio" name={field.nombre} value={option}
    aria-label={label} checked={values[field.nombre] === option} onChange={() => change(field.nombre, option)} />;
}

function NumericField({ field, matrix, values, change }: {
  field: Field; matrix: boolean; values: Values; change: FieldProps["change"];
}) {
  const value = values[field.nombre];
  return <input className="form-control" id={field.nombre} name={field.nombre} type="number"
    value={text(value) ? value : ""} min="0" step={matrix ? "0.01" : "1"}
    onChange={(e) => change(field.nombre, e.target.value)} />;
}

function QuestionRows({ question: q, values, change }: FieldProps) {
  if (q.tipo === "matriz_numerica") {
    return <div className="table-responsive"><table className="table table-sm table-bordered align-middle">
      <thead><tr><th scope="col">Sala</th><th scope="col">Superficie (m²)</th></tr></thead>
      <tbody>{q.filas.map(({ etiqueta, campo }) => <tr key={campo.nombre}>
        <th scope="row"><label htmlFor={campo.nombre}>{etiqueta}</label></th>
        <td><NumericField field={campo} matrix values={values} change={change} /></td>
      </tr>)}</tbody>
    </table></div>;
  }
  if (q.tipo === "grilla") {
    return <div className="table-responsive"><table className="table table-sm table-bordered align-middle">
      <thead><tr><th scope="col"><span className="visually-hidden">Ítem</span></th>
        {q.filas[0]?.campo.opciones.map(([key, label]) => <th scope="col" key={key}>{label}</th>)}
      </tr></thead>
      <tbody>{q.filas.map(({ etiqueta, campo }) => <tr key={campo.nombre}>
        <th scope="row">{etiqueta}</th>
        {campo.opciones.map(([key, label]) => <td key={key} className="text-center">
          <Choice field={campo} option={key} label={`${etiqueta}: ${label}`} values={values} change={change} />
        </td>)}
      </tr>)}</tbody>
    </table></div>;
  }
  return q.filas.map(({ etiqueta, campo }) => {
    if (q.tipo === "checkbox") {
      return <label className="form-check" key={campo.nombre}>
        <input className="form-check-input" type="checkbox" name={campo.nombre}
          checked={values[campo.nombre] === true} onChange={(e) => change(campo.nombre, e.target.checked)} /> {etiqueta}
      </label>;
    }
    if (q.tipo === "radio") {
      return <div key={campo.nombre}>{campo.opciones.map(([key, label]) => <label className="form-check" key={key}>
        <Choice field={campo} option={key} label={label} values={values} change={change} /> {label}
      </label>)}</div>;
    }
    return <div className="col-md-3" key={campo.nombre}>
      <label className="visually-hidden" htmlFor={campo.nombre}>{q.texto}</label>
      <NumericField field={campo} matrix={false} values={values} change={change} />
    </div>;
  });
}

function QuestionFields({ question: q, values, change }: FieldProps) {
  if (!isVisible(q.control, values)) return null;
  return <fieldset className={`mb-4 p-2 rounded${q.error ? " border border-danger" : ""}`}
    aria-describedby={q.error ? `calidad-error-${q.numero}` : undefined}>
    <legend className="float-none w-auto fs-6 fw-semibold mb-1">{q.numero}. {q.texto}</legend>
    {q.nota && <p className="text-muted small">{q.nota}</p>}
    {q.error && <p id={`calidad-error-${q.numero}`} className="text-danger small">{q.error}</p>}
    <QuestionRows question={q} values={values} change={change} />
    {q.especificar && showSpecification(q.especificar, values) && <label className="d-block">
      {q.especificar.etiqueta}
      <input className="form-control" name={q.especificar.campo.nombre} maxLength={255}
        value={String(values[q.especificar.campo.nombre] ?? "")} onChange={(e) => change(e.target.name, e.target.value)} />
    </label>}
  </fieldset>;
}

function QualityForm({ initial, endpoint }: { initial: Form; endpoint: string }) {
  const [data, setData] = useState(initial);
  const [values, setValues] = useState(() => initialValues(initial));
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const posting = useRef(false);
  const dialog = useRef<HTMLDialogElement>(null);

  const change = (name: string, value: Value) => setValues((prev) => withoutHidden({ ...prev, [name]: value }, data));
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (posting.current) return;
    const action = (event.nativeEvent as SubmitEvent).submitter;
    if (!(action instanceof HTMLButtonElement) || (action.value !== "guardar" && action.value !== "enviar")) return;
    if (dialog.current?.open) dialog.current.close();
    posting.current = true;
    setBusy(true);
    setFailed(false);
    const body = new URLSearchParams({ accion: action.value });
    for (const [field, value] of Object.entries(withoutHidden(values, data))) {
      if (value !== false) body.set(field, value === true ? "on" : value);
    }
    try {
      const response = await client.post<unknown>(endpoint, body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": leerCookie("csrftoken") ?? "" },
        validateStatus: (status) => [200, 400, 403].includes(status),
      });
      if (response.status === 403) {
        setForbidden({ prerequisite: prerequisiteFromForbidden(response.data) });
      } else if (response.status === 400 && formValid(response.data)) {
        setData(response.data);
        setValues(initialValues(response.data));
      } else if (response.status === 200 && record(response.data) && response.data.ok === true && internal(response.data.redirect)) {
        navigation.assign(response.data.redirect);
        return;
      } else setFailed(true);
    } catch {
      setFailed(true);
    }
    posting.current = false;
    setBusy(false);
  };
  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  const incompleteSections = data.secciones.filter((s) => s.preguntas.some((q) => Object.hasOwn(data.errores, q.numero)));
  return <div className="container-fluid">
    {data !== initial && <NativeToasts messages={data.messages} />}
    <div className="card"><div className="card-body">
      <h2 className="h4">{data.centro.nombre}</h2>
      <p>Centro #{data.centro.id} ({data.codigo}){data.es_borrador_existente && " — continuando borrador guardado"}</p>
      <p className="alert alert-info mb-0">{data.cartel}</p>
    </div></div>
    {incompleteSections.length > 0 && <div role="alert" className="alert alert-danger">
      Faltan completar preguntas obligatorias:
      <ul className="mb-0">{incompleteSections.map((s) => <li key={s.id}><a href={`#seccion-${s.id}`}>{s.titulo}</a></li>)}</ul>
    </div>}
    {failed && <p className="alert alert-danger" role="alert">No se pudo completar la operación. Verificá el historial o el borrador antes de volver a intentar.</p>}
    <form noValidate onSubmit={submit} onKeyDown={(e) => {
      if (e.key === "Enter" && e.target instanceof HTMLInputElement) e.preventDefault();
    }}>
      {data.secciones.map((s) => <section className="card mb-3" key={s.id} id={`seccion-${s.id}`}>
        <h2 className="h5 card-header bg-primary text-white">{s.titulo}</h2>
        <div className="card-body">
          {s.preguntas.map((q) => <div key={q.numero}>
            {q.subtitulo && <h3 className="h6 text-primary">{q.subtitulo}</h3>}
            <QuestionFields question={q} values={values} change={change} />
          </div>)}
        </div>
      </section>)}
      <div className="card sticky-bottom shadow"><div className="card-body d-flex flex-wrap gap-2 justify-content-end">
        <a className="btn btn-outline-secondary" href={data.centro.url}>Cancelar</a>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => dialog.current?.showModal()}>Guardar</button>
        <button type="submit" name="accion" value="enviar" className="btn btn-primary" disabled={busy}>Enviar</button>
      </div></div>
      <dialog ref={dialog} aria-labelledby="calidad-dialog-title" className="rounded p-3" style={{ maxWidth: "min(32rem, calc(100vw - 2rem))" }}>
        <h2 id="calidad-dialog-title" className="h5">Guardar formulario parcial</h2>
        <p>Podés completar el formulario luego. Para enviarlo, seleccioná «Enviar».</p>
        <div className="d-flex flex-wrap gap-2 justify-content-end">
          <button type="button" className="btn btn-outline-secondary" onClick={() => dialog.current?.close()}>Cancelar</button>
          <button type="submit" name="accion" value="guardar" className="btn btn-primary" disabled={busy}>Aceptar</button>
        </div>
      </dialog>
    </form>
  </div>;
}

function FormPage({ endpoint }: { endpoint: string }) {
  const [state] = useCdiPage(endpoint, formValid);
  return renderCdi(state, (data) => ({
    title: "Formulario de Calidad", heading: "Formulario de Calidad",
    content: <QualityForm initial={data} endpoint={endpoint} />,
  }));
}

function QualityPage({ params }: { params: Params }) {
  const base = `web/cdi/centros/${params.centro}/calidad/`;
  if (params.screen === "form") return <FormPage key={base} endpoint={base + "cargar/"} />;
  if (params.screen === "detail") return <DetailPage endpoint={`${base}${params.formId}/`} />;
  return <HistoryPage endpoint={base + window.location.search} />;
}

const PATH = /^\/centrodeinfancia\/(\d+)\/calidad\/(?:(cargar|\d+)\/)?$/;
export const cdiFormularioCalidadRoute: RouteDefinition<Params> = {
  name: "cdi-formulario-calidad",
  match: (path) => {
    const match = PATH.exec(path);
    if (!match) return null;
    const [, centro, formId] = match;
    return { centro, formId, screen: formId === "cargar" ? "form" : formId ? "detail" : "history" };
  },
  render: (params) => <QualityPage params={params} />,
};
