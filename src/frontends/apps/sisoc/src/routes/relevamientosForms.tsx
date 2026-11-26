/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useState, type FormEvent, type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import { Tree, arr, bool, csrf, integer, messagesValid, nodeValid, path, useCardCollapse, type TreeNode } from "./relevamientos";
import { UNCERTAIN, postApi, relevamientosNavigation, restartFromTop, setFlash, useToasts, type Message } from "./relevamientosApi";
import { CSS } from "./relevamientosShared";
import type { RouteDefinition } from "./types";

/**
 * R03.02 `seguimiento_form.html` and R02.02 `acta_complementaria_form.html`.
 * The API projects the native editors (`SeguimientoEditor`,
 * `ActaComplementariaEditor`): every field arrives as its real widget markup
 * with its bound errors, and the POST carries the native names (`seg-*`,
 * `<bloque>-*`, `acta-*`, `prestaciones-*`). A 400 re-renders the page with the
 * errors; a lost answer is never resent.
 */
export type Field = { name: string; label: string; id: string; hidden: boolean; help_text: string; errors: string[]; nodes: TreeNode[] };
type Form = { fields: Field[]; non_field_errors: string[] };
type Formset = { management: Field[]; forms: { hidden: Field[]; fields: Field[] }[]; non_form_errors: string[] };
export type SeguimientoFormData = {
  seguimiento: { id: number; tipo_display: string; numero_orden: number }; relevamiento: { id: number; fecha_visita: string }; comedor: { id: number; nombre: string };
  root: Form; bloques: { key: string; label: string; existe: boolean; form: Form }[]; prestaciones: Formset;
  urls: { comedores: string; comedor: string; relevamiento: string; detalle: string }; messages: Message[];
};
export type ActaFormData = {
  acta_id: number | null; comedor: { id: number; nombre: string }; form: Form; prestaciones: Formset;
  urls: { comedores: string; comedor: string; listado: string }; messages: Message[];
};

const API = "web/comedores/relevamientos/";
const fieldValid = (f: unknown) => record(f) && text(f.name) && text(f.label) && text(f.id) && bool(f.hidden) && text(f.help_text) && arr(f.errors, text) && arr(f.nodes, nodeValid);
const formValid = (f: unknown) => record(f) && arr(f.fields, fieldValid) && arr(f.non_field_errors, text);
const formsetValid = (f: unknown) => record(f) && arr(f.management, fieldValid) && arr(f.forms, (r) => record(r) && arr(r.hidden, fieldValid) && arr(r.fields, fieldValid)) && arr(f.non_form_errors, text);

export function seguimientoFormValid(v: unknown): v is SeguimientoFormData {
  if (!record(v) || !record(v.seguimiento) || !record(v.relevamiento) || !record(v.comedor) || !record(v.urls)) return false;
  const urls = v.urls;
  return integer(v.seguimiento.id) && text(v.seguimiento.tipo_display) && integer(v.seguimiento.numero_orden) && integer(v.relevamiento.id) && text(v.relevamiento.fecha_visita) &&
    integer(v.comedor.id) && text(v.comedor.nombre) && formValid(v.root) &&
    arr(v.bloques, (b) => record(b) && text(b.key) && text(b.label) && bool(b.existe) && formValid(b.form)) && formsetValid(v.prestaciones) &&
    ["comedores", "comedor", "relevamiento", "detalle"].every((k) => internal(urls[k])) && messagesValid(v.messages);
}

export function actaFormValid(v: unknown): v is ActaFormData {
  if (!record(v) || !record(v.comedor) || !record(v.urls)) return false;
  const urls = v.urls;
  return (v.acta_id === null || integer(v.acta_id)) && integer(v.comedor.id) && text(v.comedor.nombre) && formValid(v.form) && formsetValid(v.prestaciones) &&
    ["comedores", "comedor", "listado"].every((k) => internal(urls[k])) && messagesValid(v.messages);
}

/** `{{ errors }}`: Django's `<ul class="errorlist">`. */
const ErrorList = ({ errors, nonfield = false }: { errors: string[]; nonfield?: boolean }) => (
  <ul className={`errorlist${nonfield ? " nonfield" : ""}`}>{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
);

/** `{{ field }}` with its label, help text and errors, in the markup of the native loops. */
function FieldBox({ field, cls }: { field: Field; cls: string }) {
  return (
    <div className={cls}>
      <label htmlFor={field.id} className="form-label">{field.label}</label>
      <Tree nodes={field.nodes} />
      {field.help_text && <small className="form-text text-muted">{field.help_text}</small>}
      {field.errors.map((e, i) => <div className="text-danger small" key={i}>{e}</div>)}
    </div>
  );
}

function Prestaciones({ formset, head, title, tail }: { formset: Formset; head: string[]; title: string; tail: ReactNode }) {
  return (
    <div className="card mb-3" id="bloque-prestaciones">
      <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">{title}</h3></div>
      <div className="card-body p-0">
        {formset.management.map((f) => <Tree key={f.name} nodes={f.nodes} />)}
        {formset.non_form_errors.length > 0 && <div className="alert alert-danger m-3"><ErrorList errors={formset.non_form_errors} nonfield /></div>}
        <div className="table-responsive">
          <table className="table table-striped mb-0">
            <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {formset.forms.map((row, i) => (
                <tr key={i}>
                  {row.hidden.map((f) => <Tree key={f.name} nodes={f.nodes} />)}
                  {row.fields.map((f) => <td key={f.name}><Tree nodes={f.nodes} />{f.errors.map((e, j) => <div className="text-danger small" key={j}>{e}</div>)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {tail}
      </div>
    </div>
  );
}

const PRESTACIONES_HELP = <p className="text-muted small m-3 mb-2">La última fila vacía permite agregar una prestación. Guarde y vuelva a editar para agregar más.</p>;

type Saver<T> = { data: T; version: number; pending: boolean; uncertain: boolean; submit: (event: FormEvent<HTMLFormElement>) => void };

/** The POST of a native form: ok flashes and goes on, a 400 re-renders the bound form, a lost answer is never resent. */
function useFormSave<T>(initial: T, endpoint: string, push: (m: Message) => void, validate?: (data: unknown) => data is T): Saver<T> {
  const [state, setState] = useState({ data: initial, version: 0 });
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const result = await postApi(endpoint, new URLSearchParams(new FormData(event.currentTarget) as unknown as Record<string, string>));
    if (result.kind === "ok") {
      setFlash([{ message: result.message, level: "success" }]);
      relevamientosNavigation.assign(result.redirect);
      return;
    }
    if (result.kind === "invalid") {
      if (validate && !validate(result.body)) {
        push({ message: String(result.body.detail), level: "error" });
        setPending(false);
        return;
      }
      setState((s) => ({ data: { ...s.data, ...(result.body as Partial<T>) }, version: s.version + 1 }));
      push({ message: String(result.body.detail), level: "error" });
      window.setTimeout(restartFromTop, 0);
    } else if (result.kind === "error") push({ message: result.message, level: "error" });
    else setUncertain(true);
    setPending(false);
  }
  return { data: state.data, version: state.version, pending, uncertain, submit };
}

const Uncertain = () => (
  <div role="alert" className="alert alert-warning">{UNCERTAIN}{" "}
    <button type="button" className="btn btn-link p-0 align-baseline" onClick={() => relevamientosNavigation.assign(window.location.pathname)}>Recargar</button></div>
);

const Footer = ({ cancel, saver }: { cancel: string; saver: { pending: boolean; uncertain: boolean } }) => (
  <>
    {saver.uncertain && <Uncertain />}
    <div className="d-flex justify-content-end gap-2 mb-4">
      <a href={path(cancel)} className="btn btn-secondary">Cancelar</a>
      <button type="submit" className="btn btn-primary" disabled={saver.pending || saver.uncertain}>Guardar</button>
    </div>
  </>
);

// --- Seguimiento -------------------------------------------------------------

export function SeguimientoFormContent({ initial }: { initial: SeguimientoFormData }) {
  useCardCollapse();
  const { toasts, push } = useToasts(initial.messages);
  const { seguimiento: s } = initial;
  const saver = useFormSave(initial, `${API}${initial.comedor.id}/relevamiento/${initial.relevamiento.id}/seguimientos/${s.id}/editar/`, push);
  const data = saver.data;
  return <>
    {toasts}
    {CSS}
    <form method="post" noValidate key={saver.version} onSubmit={saver.submit}>
      {csrf()}
      {data.root.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={data.root.non_field_errors} nonfield /></div>}
      <div className="card mb-3">
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Datos de la instancia</h3></div>
        <div className="card-body"><div className="row">{data.root.fields.map((f) => <FieldBox key={f.name} field={f} cls="col-md-6 mb-3" />)}</div></div>
      </div>
      {data.bloques.map((b) => (
        <div className="card mb-3" id={`bloque-${b.key}`} key={b.key}>
          <div className="card-header d-flex align-items-center">
            <h3 className="card-title font-weight-bold mr-3 pt-1 mb-0">{b.label}</h3>
            {!b.existe && <>{" "}<span className="badge bg-secondary ml-2" title="Se crea solo si se completa algún campo">Sin cargar</span></>}
            <div className="card-tools ml-auto"><button type="button" className="btn btn-tool" data-card-widget="collapse"><i className="fas fa-minus" /></button></div>
          </div>
          <div className="card-body">
            {b.form.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={b.form.non_field_errors} nonfield /></div>}
            <div className="row">{b.form.fields.map((f) => <FieldBox key={f.name} field={f} cls="col-md-4 col-sm-6 mb-3" />)}</div>
          </div>
        </div>
      ))}
      <Prestaciones formset={data.prestaciones} title="Prestaciones" tail={PRESTACIONES_HELP}
        head={["Días", "Tipo", "AP presencial", "AP vianda", "AP total", "DE presencial", "DE vianda", "Eliminar"]} />
      <Footer cancel={data.urls.detalle} saver={saver} />
    </form>
  </>;
}

function SeguimientoFormPage({ comedor, relevamiento, id }: { comedor: string; relevamiento: string; id: string }) {
  const [state] = useMainResource(`${API}${comedor}/relevamiento/${relevamiento}/seguimientos/${id}/editar/`, seguimientoFormValid);
  return renderMain(state, "Cargando seguimiento…", (data) => {
    const s = data.seguimiento;
    const tipo = s.tipo_display.toLowerCase();
    return {
      title: `Editar ${tipo} - Comedor: ${data.comedor.nombre}`,
      heading: <>{data.comedor.nombre}{" "}<span className="ml-2 h5">| Editar {tipo} #{s.numero_orden}</span></> as unknown as string,
      breadcrumb: <>
        <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{data.comedor.nombre}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.relevamiento)}>Acompañamiento Territorial {data.relevamiento.fecha_visita}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.detalle)}>{s.tipo_display}</a></div>
        <div className="breadcrumb-item active">Editar</div>
      </>,
      content: <SeguimientoFormContent initial={data} />,
    };
  });
}

// --- Acta ----------------------------------------------------------------------

export function ActaFormContent({ initial }: { initial: ActaFormData }) {
  const { toasts, push } = useToasts(initial.messages);
  const endpoint = `${API}${initial.comedor.id}/actas/${initial.acta_id === null ? "crear" : `${initial.acta_id}/editar`}/`;
  const saver = useFormSave(initial, endpoint, push);
  const data = saver.data;
  return <>
    {toasts}
    {CSS}
    <form method="post" noValidate key={saver.version} onSubmit={saver.submit}>
      {csrf()}
      <div className="card mb-3">
        <div className="card-header"><h3 className="card-title font-weight-bold mr-3 pt-1">Datos del acta</h3></div>
        <div className="card-body">
          <p className="text-muted">Registra, fuera del ciclo de visitas, un cambio en la prestación del comedor.</p>
          {data.form.non_field_errors.length > 0 && <div className="alert alert-danger"><ErrorList errors={data.form.non_field_errors} nonfield /></div>}
          <div className="row">{data.form.fields.map((f) => <FieldBox key={f.name} field={f} cls={`${f.name === "acta-observaciones" ? "col-12" : "col-md-6"} mb-3`} />)}</div>
        </div>
      </div>
      <Prestaciones formset={data.prestaciones} title="Prestaciones (día × tipo)" tail={PRESTACIONES_HELP} head={["Días", "Tipo", "Cantidad actual", "Cantidad en espera", "Eliminar"]} />
      <Footer cancel={data.urls.listado} saver={saver} />
    </form>
  </>;
}

function ActaFormPage({ comedor, id }: { comedor: string; id?: string }) {
  const [state] = useMainResource(`${API}${comedor}/actas/${id ? `${id}/editar` : "crear"}/`, actaFormValid);
  return renderMain(state, "Cargando acta…", (data) => {
    const prefijo = id ? "Editar" : "Nueva";
    return {
      title: `${prefijo} acta complementaria - Comedor: ${data.comedor.nombre}`,
      heading: <>{data.comedor.nombre}{" "}<span className="ml-2 h5">| {prefijo} acta complementaria extraordinaria</span></> as unknown as string,
      breadcrumb: <>
        <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{data.comedor.nombre}</a></div>
        <div className="breadcrumb-item"><a href={path(data.urls.listado)}>Acompañamiento Territorial</a></div>
        <div className="breadcrumb-item active">Acta complementaria</div>
      </>,
      content: <ActaFormContent initial={data} />,
    };
  });
}

type EditorField = Field & { required?: boolean };
type EditorData = {
  comedor: { id: number; nombre: string };
  relevamiento: { id: number; fecha_visita: string } | null;
  forms: Record<string, { fields: EditorField[]; non_field_errors: string[] }>;
  tiene_referente: boolean;
  responsable_congelado: boolean;
  urls: { comedores: string; comedor: string; detalle: string | null; cancelar: string };
};

function editorValid(value: unknown): value is EditorData {
  if (!record(value) || !record(value.comedor) || !record(value.urls) || !record(value.forms)) return false;
  const { comedor, relevamiento, urls, forms } = value;
  return integer(comedor.id) && text(comedor.nombre) &&
    (relevamiento === null || (record(relevamiento) && integer(relevamiento.id) && text(relevamiento.fecha_visita))) &&
    internal(urls.comedores) && internal(urls.comedor) && internal(urls.cancelar) &&
    (urls.detalle === null || internal(urls.detalle)) &&
    bool(value.tiene_referente) && bool(value.responsable_congelado) &&
    formValid(forms.root) && Object.values(forms).every(formValid);
}

type FieldGroup = { title: string; form?: string; fields?: string; column?: number };
const SECTION_LAYOUT: { heading: string; groups: FieldGroup[] }[] = [
  { heading: "1- Datos del Comedor/Merendero", groups: [
    { title: "1.1 Datos del Comedor/Merendero", fields: "fecha_visita_ui comedor comienzo modalidad_prestacion servicio_por_turnos cantidad_turnos", column: 4 },
    { title: "1.2 Domicilio del Comedor/Merendero", fields: "calle numero entre_calle_1 entre_calle_2 barrio codigo_postal localidad municipio partido provincia", column: 4 },
    { title: "1.3 Datos del responsable del acompañamiento territorial", fields: "responsable_es_referente nombre apellido mail celular documento funcion", column: 4 },
  ] },
  { heading: "2- Datos sobre el espacio físico donde funciona el Comedor/Merendero", groups: [
    { title: "2.1 Espacio donde funciona", form: "espacio_form" },
    { title: "2.2 Espacio donde se cocina y almacenamiento de alimentos", form: "espacio_cocina_form" },
    { title: "2.3 Espacio donde se brinda la prestación del Comedor/Merendero", form: "espacio_prestacion_form" },
  ] },
  { heading: "3- Datos sobre las personas que realizan tareas en el Comedor/Merendero", groups: [
    { title: "3.1 Personas que realizan tareas en el Comedor/Merendero", form: "colaboradores_form" },
  ] },
  { heading: "4- Datos sobre recursos del Comedor/Merendero", groups: [
    { title: "4.1 Origen y tipo de recursos", fields: [
      "donaciones_particulares", "estado_nacional", "estado_provincial", "estado_municipal", "otros",
    ].flatMap((source) => [`recibe_${source}`, `frecuencia_${source}`, `recursos_${source}`]).join(" "), column: 4 },
  ] },
  { heading: "5- Datos sobre la realización de compras para abastecer el Comedor/Merendero", groups: [
    { title: "5.1 Lugares donde suele realizar las compras para abastecer el Comedor/Merendero", form: "compras_form" },
  ] },
];

const DAYS = [
  ["lunes", "Lunes"], ["martes", "Martes"], ["miercoles", "Miércoles"], ["jueves", "Jueves"],
  ["viernes", "Viernes"], ["sabado", "Sábado"], ["domingo", "Domingo"],
] as const;
const MEALS = ["Desayuno", "Almuerzo", "Merienda", "Cena"] as const;
const AVAILABILITY = [["actual", "Personas actuales"], ["espera", "Personas en espera"]] as const;

type Rule = { source: string; targets: string[]; when: "yes" | "other" };
const optionalRules: Rule[] = [
  { source: "servicio_por_turnos", targets: ["cantidad_turnos"], when: "yes" },
  { source: "tipo_espacio_fisico", targets: ["espacio_fisico_otro"], when: "other" },
  { source: "abastecimiento_agua", targets: ["abastecimiento_agua_otro"], when: "other" },
  { source: "gestion_quejas", targets: ["gestion_quejas_otro"], when: "other" },
  { source: "tiene_sanitarios", targets: ["desague_hinodoro"], when: "yes" },
  ...["donaciones_particulares", "estado_nacional", "estado_provincial", "estado_municipal", "otros"].map((source): Rule => ({
    source: `recibe_${source}`, targets: [`frecuencia_${source}`, `recursos_${source}`], when: "yes",
  })),
  { source: "comedor_merendero", targets: ["insumos_organizacion", "tipo_insumo", "frecuencia_insumo", "veces_recibio_insumos_2024",
    "tecnologia", "servicio_internet", "acceso_comedor", "distancia_transporte", "zona_inundable", "actividades_jardin_maternal",
    "actividades_jardin_infantes", "apoyo_escolar", "alfabetizacion_terminalidad", "capacitaciones_talleres", "promocion_salud",
    "actividades_discapacidad", "necesidades_alimentarias", "actividades_recreativas", "actividades_culturales",
    "emprendimientos_productivos", "actividades_religiosas", "actividades_huerta", "espacio_huerta", "otras_actividades",
    "cuales_otras_actividades"], when: "yes" },
  { source: "insumos_organizacion", targets: ["tipo_insumo", "frecuencia_insumo", "veces_recibio_insumos_2024"], when: "yes" },
  { source: "actividades_huerta", targets: ["espacio_huerta"], when: "yes" },
  { source: "otras_actividades", targets: ["cuales_otras_actividades"], when: "yes" },
];
const dependencyFields = new Set(optionalRules.flatMap(({ targets }) => targets));

function updateOptionalFields(form: HTMLFormElement | null, data: Pick<EditorData, "tiene_referente" | "responsable_congelado">) {
  if (!form) return;
  const hidden = new Set<string>();
  for (const { source, targets, when } of optionalRules) {
    const select = form.elements.namedItem(source);
    if (!(select instanceof HTMLSelectElement)) continue;
    const active = when === "other" ? select.selectedOptions[0]?.text === "Otro" : select.value === "True";
    if (!active) targets.forEach((name) => hidden.add(name));
  }
  for (const name of dependencyFields) {
    const control = form.elements.namedItem(name);
    if (!(control instanceof HTMLInputElement || control instanceof HTMLSelectElement || control instanceof HTMLTextAreaElement)) continue;
    // Legacy JS disabled some required questions, preventing a valid POST. Keep
    // them answerable instead of synthesizing domain answers in the browser.
    if (control.required) continue;
    control.disabled = hidden.has(name);
    if (control.disabled) {
      if (control instanceof HTMLSelectElement && control.multiple) {
        for (const option of control.options) option.selected = false;
      } else if (control instanceof HTMLInputElement && control.type === "checkbox") {
        control.checked = false;
      } else {
        control.value = "";
      }
    }
  }
  const responsable = form.elements.namedItem("responsable_es_referente");
  const referente = data.tiene_referente && responsable instanceof HTMLSelectElement && responsable.value === "True";
  const linked = referente || data.responsable_congelado;
  for (const name of ["nombre", "apellido", "mail", "celular", "documento", "funcion"]) {
    const control = form.elements.namedItem(name);
    if (control instanceof HTMLInputElement) control.disabled = linked;
  }
  const note = form.querySelector<HTMLElement>("[data-responsable-note]");
  if (note && !data.responsable_congelado) note.hidden = !referente;
}

function editorControlNodes(field: EditorField, label?: string): TreeNode[] {
  return field.nodes.map((node) => {
    if (typeof node === "string" || !["input", "select", "textarea"].includes(node.t)) return node;
    const className = node.t === "select" ? "form-select" : node.a.type === "checkbox" ? "form-check-input" : "form-control";
    return { ...node, a: { ...node.a, class: `${node.a.class ?? ""} ${className}`,
      ...(field.required ? { required: "" } : {}),
      ...(field.errors.length > 0 ? { "aria-invalid": "true", "aria-describedby": `${field.id}-errors` } : {}),
      ...(label ? { "aria-label": label } : {}),
    } };
  });
}

function EditorControl({ field, label }: { field: EditorField; label?: string }) {
  if (field.hidden) return <Tree nodes={field.nodes} />;
  return <div className="mb-3">
    {!label && <label htmlFor={field.id} className="form-label">{field.label}{field.required && <span aria-hidden="true">*</span>}</label>}
    <Tree nodes={editorControlNodes(field, label)} />
    {field.help_text && <small className="form-text text-muted">{field.help_text}</small>}
    {field.errors.length > 0 && <div id={`${field.id}-errors`} className="text-danger small">{field.errors.join(" ")}</div>}
  </div>;
}

function EditorGrid({ fields, column = 6 }: { fields: EditorField[]; column?: number }) {
  return <div className="row align-items-end px-3">
    {fields.map((f) => <div key={f.name} className={`col-12 col-md-${column}`}><EditorControl field={f} /></div>)}
  </div>;
}

function RelevamientoEditor({ initial, endpoint }: { initial: EditorData; endpoint: string }) {
  const { toasts, push } = useToasts([]);
  const saver = useFormSave(initial, endpoint, push, editorValid);
  const { forms, urls } = saver.data;
  const fields = new Map(Object.values(forms).flatMap(({ fields: values }) => values.map((f) => [f.name, f] as const)));
  const fromNames = (names: string) => names.split(" ").flatMap((name) => {
    const field = fields.get(name);
    return field ? [field] : [];
  });

  return <>
    {toasts}
    {CSS}
    <section className="card card-primary card-outline">
      <div className="card-header mb-3"><h2 className="card-title">{initial.relevamiento ? "Editar Comedor/Merendero" : "Agregar Comedor/Merendero"}</h2></div>
      <div className="card-body">
        <form method="post" key={saver.version} noValidate onSubmit={saver.submit} ref={(form) => updateOptionalFields(form, saver.data)}
          onChange={(event) => { if (event.target instanceof HTMLSelectElement) updateOptionalFields(event.currentTarget, saver.data); }}>
          {csrf()}
          {Object.entries(forms).map(([name, { non_field_errors: errors }]) => errors.length > 0 &&
            <div key={name} role="alert" className="alert alert-danger"><ErrorList errors={errors} nonfield /></div>)}
          {SECTION_LAYOUT.map(({ heading, groups }) => <section key={heading}>
            <h1>{heading}</h1>
            {groups.map((group) => <div className="px-3" key={group.title}>
              <h3 className="mt-5">{group.title}</h3>
              {group.fields?.startsWith("responsable_es_referente ") &&
                <p className="form-text" data-responsable-note hidden={!saver.data.responsable_congelado}>
                  {saver.data.responsable_congelado ? "El responsable forma parte del registro histórico del comedor." : "Se usará el referente del comedor."}
                </p>}
              <EditorGrid column={group.column} fields={group.form ? forms[group.form]?.fields ?? [] : fromNames(group.fields ?? "")} />
            </div>)}
          </section>)}
          <section>
            <h1>6- Datos sobre la prestación alimentaria</h1>
            <div className="px-3">
              <h3 className="mt-5">6.1 Resumen de prestaciones actuales y en lista de espera informadas por el Comedor/Merendero</h3>
              <div className="table-responsive">
                <table className="table table-bordered">
                  <thead>
                    <tr><th rowSpan={2}>Prestación</th>{DAYS.map(([id, day]) => <th key={id} scope="colgroup" colSpan={2} className="text-center">{day}</th>)}</tr>
                    <tr>{DAYS.flatMap(([id]) => AVAILABILITY.map(([key, label]) => <th key={`${id}-${key}`} scope="col">{label}</th>))}</tr>
                  </thead>
                  <tbody>{MEALS.map((meal) => <tr key={meal}>
                    <th scope="row">{meal.toUpperCase()}</th>
                    {DAYS.flatMap(([id, day]) => AVAILABILITY.map(([key, label]) => {
                      const field = fields.get(`${id}_${meal.toLowerCase()}_${key}`);
                      return <td key={`${id}-${key}`}>{field && <EditorControl field={field} label={`${day} · ${meal} · ${label}`} />}</td>;
                    }))}
                  </tr>)}</tbody>
                </table>
              </div>
            </div>
          </section>
          <section>
            <h1>Anexo</h1>
            <div className="px-3">
              <h3 className="mt-5">Información sobre el anexo</h3>
              <EditorGrid column={4} fields={forms.anexo_form?.fields ?? []} />
              <h3 className="mt-5">Punto de entrega de alimentos</h3>
              <EditorGrid column={4} fields={forms.punto_entregas_form?.fields ?? []} />
            </div>
          </section>
          <section><h1>7- Observación</h1><EditorGrid column={12} fields={fromNames("observacion")} /></section>
          {saver.uncertain && <Uncertain />}
          <div className="my-3 d-flex gap-2">
            <button className="btn btn-primary" type="submit" disabled={saver.pending || saver.uncertain}>Confirmar</button>
            <button className="btn btn-secondary d-none d-sm-inline" type="button" onClick={() => window.print()}>Imprimir</button>
            <a href={path(urls.cancelar)} className="btn btn-secondary">Cancelar</a>
          </div>
        </form>
      </div>
    </section>
  </>;
}

function RelevamientoEditorPage({ comedor, id }: { comedor: string; id?: string }) {
  const endpoint = `${API}${comedor}/relevamiento/${id ? `${id}/editar` : "crear"}/`;
  const [state] = useMainResource(endpoint, editorValid);
  return renderMain(state, "Cargando acompañamiento territorial…", (data) => ({
    title: "Comedores - Acompañamiento Territorial",
    heading: `Acompañamiento Territorial - Comedores: ${data.comedor.nombre}`,
    breadcrumb: <>
      <div className="breadcrumb-item"><a href={path(data.urls.comedores)}>Comedores</a></div>
      <div className="breadcrumb-item"><a href={path(data.urls.comedor)}>{data.comedor.nombre}</a></div>
      {data.relevamiento && data.urls.detalle && <div className="breadcrumb-item"><a href={path(data.urls.detalle)}>
        Acompañamiento Territorial {data.relevamiento.fecha_visita}
      </a></div>}
      <div className="breadcrumb-item active">{data.relevamiento ? "Editar" : "Agregar"}</div>
    </>,
    content: <RelevamientoEditor initial={data} endpoint={endpoint} />,
  }));
}

type Params = { comedor: string; relevamiento?: string; id?: string; acta?: boolean; editor?: boolean };
const SEGUIMIENTO = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)\/seguimiento\/([0-9]+)\/editar$/;
const RELEVAMIENTO_CREAR = /^\/comedores\/([0-9]+)\/relevamiento\/crear$/;
const RELEVAMIENTO_EDITAR = /^\/comedores\/([0-9]+)\/relevamiento\/([0-9]+)\/editar$/;
const ACTA_NUEVA = /^\/comedores\/([0-9]+)\/acta-complementaria\/crear$/;
const ACTA_EDITAR = /^\/comedores\/([0-9]+)\/acta-complementaria\/([0-9]+)\/editar$/;

export const relevamientosFormsRoute: RouteDefinition<Params> = {
  name: "comedores-relevamientos-formularios",
  match(pathname) {
    const crear = RELEVAMIENTO_CREAR.exec(pathname);
    if (crear) return { comedor: crear[1], editor: true };
    const editar = RELEVAMIENTO_EDITAR.exec(pathname);
    if (editar) return { comedor: editar[1], id: editar[2], editor: true };
    const s = SEGUIMIENTO.exec(pathname);
    if (s) return { comedor: s[1], relevamiento: s[2], id: s[3] };
    const n = ACTA_NUEVA.exec(pathname);
    if (n) return { comedor: n[1], acta: true };
    const e = ACTA_EDITAR.exec(pathname);
    return e ? { comedor: e[1], id: e[2], acta: true } : null;
  },
  render({ comedor, relevamiento, id, acta, editor }) {
    if (editor) return <RelevamientoEditorPage comedor={comedor} id={id} />;
    return acta ? <ActaFormPage comedor={comedor} id={id} /> : <SeguimientoFormPage comedor={comedor} relevamiento={relevamiento!} id={id!} />;
  },
};
