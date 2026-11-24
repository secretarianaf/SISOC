/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens, validators and the navigation seam live here with the route. */
import { useRef, useState, type FormEvent } from "react";
import { InsumosToastList } from "../InsumosToast";
import { Csrf, Crumbs, Frame, Hero, HEADING, ROOT, API, BASE, choices, int, messagesValid, navValid, texts, type Choice, type Message, type Nav } from "./admisionesTemplates";
import { postForm, record, renderMain, text, useMainResource } from "./MainFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * AD01.02 template create form (`comedores/configuracion/templates/crear/`, `form.html`).
 * `/api/web/comedores/admisiones/plantillas-informe/crear/` runs the native
 * `PlantillaInformeTecnicoCreateView`: GET returns what its form renders, POST runs the native
 * `post()` (form, `crear_plantilla`, message) and a 302 becomes `{ok, redirect}`; a rejected form
 * comes back as 400 with its bound payload. A POST is never retried.
 */
type Params = { page: "crear" };
type Field = { name: string; required: boolean; value: string; choices?: Choice[]; max_length?: number };
type CrearData = {
  fields: Field[]; errors: Record<string, string[]>; non_field_errors: string[];
  urls: Nav & { cancelar: string }; messages: Message[];
};
const NAMES = ["nombre", "descripcion", "tipo_admision", "tipo_convenio", "es_ex_pnud", "estado_convenio_pnud", "tipo_renovacion", "estado_financiamiento", "informe_complementario_modifica_prestaciones"];
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";

const fieldValid = (f: unknown): f is Field => record(f) && text(f.name) && typeof f.required === "boolean" && text(f.value) &&
  (f.choices === undefined || choices(f.choices)) && (f.max_length === undefined || int(f.max_length));
export const crearValid = (v: unknown): v is CrearData => record(v) && Array.isArray(v.fields) && v.fields.length === NAMES.length &&
  v.fields.every((f, i) => fieldValid(f) && f.name === NAMES[i]) &&
  record(v.errors) && Object.values(v.errors).every((e) => Array.isArray(e) && e.every(text)) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
  navValid(v.urls, ["cancelar"]) && texts(v.urls, ["cancelar"]) && messagesValid(v.messages);

/** Replaceable in tests: the confirmed redirect is a full-page navigation, like the native 302. */
export const templatesFormNavigation = { assign: (to: string) => window.location.assign(to) };

const initial = (data: CrearData) => Object.fromEntries(data.fields.map((f) => [f.name, f.value]));

function Errors({ items }: { items: string[] | undefined }) {
  return <>{(items ?? []).map((e, i) => <div key={i} className="invalid-feedback">{e}</div>)}</>;
}

function CrearPage({ data: first, endpoint }: { data: CrearData; endpoint: string }) {
  const [data, setData] = useState(first);
  const [values, setValues] = useState(() => initial(first));
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const field = (name: string) => data.fields.find((f) => f.name === name)!;
  // `form.html` script: the block of the other type is hidden and the PNUD state needs Ex PNUD = sí.
  const incorporacion = values.tipo_admision === "incorporacion";
  const pnud = incorporacion && values.es_ex_pnud === "si";
  const onChange = (name: string) => (e: { target: { value: string } }) => {
    const next = { ...values, [name]: e.target.value };
    if (!(next.tipo_admision === "incorporacion" && next.es_ex_pnud === "si")) next.estado_convenio_pnud = "";
    setValues(next);
  };
  const select = (name: string, required: boolean) => (
    <select name={name} className="form-select" id={`id_${name}`} required={required || undefined} value={values[name]} onChange={onChange(name)}>
      {(field(name).choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
    </select>
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams();
    for (const [name, value] of Object.entries(values)) body.append(name, value);
    const outcome = await postForm(endpoint, body);
    if (outcome.kind === "redirect") { templatesFormNavigation.assign(outcome.url); return; }
    if (outcome.kind === "invalid" && crearValid(outcome.data)) {
      setData(outcome.data); setValues(initial(outcome.data)); setRevision((r) => r + 1);
      resetAfterRejectedPost();
    } else setUncertain(true);
    busy.current = false; setPending(false);
  }

  return <Frame section="templates" urls={data.urls}>
    <InsumosToastList messages={data.messages} />
    <Hero eyebrow="Nuevo template" title="Definir una combinación">Las condiciones identifican una única combinación para seleccionar el modelo de informe técnico correspondiente.</Hero>
    <div className="row g-3">
      <div className="col-xl-8">
        <section className="card gt-card">
          <form method="post" className="gt-form" onSubmit={(e) => void submit(e)} key={revision}>
            <Csrf />
            <div className="card-header"><h2 className="card-title"><i className="fas fa-sliders-h" />Nueva plantilla lógica</h2></div>
            <div className="card-body">
              {data.non_field_errors.length > 0 && <div className="alert alert-danger"><ul className="errorlist nonfield">{data.non_field_errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
              <div className="row">
                <div className="col-md-8 form-group">
                  <label htmlFor="id_nombre">Nombre</label>
                  <input type="text" name="nombre" className="form-control" maxLength={field("nombre").max_length} required={field("nombre").required || undefined} id="id_nombre"
                    value={values.nombre} onChange={onChange("nombre")} />
                  <Errors items={data.errors.nombre} />
                </div>
                <div className="col-md-4 form-group">
                  <label htmlFor="id_tipo_admision">Tipo de admisión</label>
                  {select("tipo_admision", field("tipo_admision").required)}
                  <Errors items={data.errors.tipo_admision} />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="id_descripcion">Descripción</label>
                <textarea name="descripcion" cols={40} rows={3} className="form-control" id="id_descripcion" value={values.descripcion} onChange={onChange("descripcion")} />
              </div>
              <div className="form-group">
                <label htmlFor="id_tipo_convenio">Tipo de convenio</label>
                {select("tipo_convenio", field("tipo_convenio").required)}
                <div className="form-text">Esta condición toma el tipo de convenio registrado en la admisión. Asociación de hecho utiliza el valor existente Organización Base.</div>
                <Errors items={data.errors.tipo_convenio} />
              </div>
              <div id="condicionesIncorporacion" className="row" hidden={!incorporacion}>
                <div className="col-md-6 form-group">
                  <label htmlFor="id_es_ex_pnud">¿Es Ex PNUD?</label>
                  {select("es_ex_pnud", incorporacion)}
                  <Errors items={data.errors.es_ex_pnud} />
                </div>
                <div className="col-md-6 form-group" id="estadoPnudContainer" hidden={!pnud}>
                  <label htmlFor="id_estado_convenio_pnud">Estado del convenio PNUD</label>
                  {select("estado_convenio_pnud", pnud)}
                  <Errors items={data.errors.estado_convenio_pnud} />
                </div>
              </div>
              <div id="condicionesRenovacion" className="row" hidden={incorporacion}>
                <div className="col-md-6 form-group">
                  <label htmlFor="id_tipo_renovacion">Renovación que tramita</label>
                  {select("tipo_renovacion", !incorporacion)}
                  <Errors items={data.errors.tipo_renovacion} />
                </div>
                <div className="col-md-6 form-group">
                  <label htmlFor="id_estado_financiamiento">Estado del financiamiento</label>
                  {select("estado_financiamiento", !incorporacion)}
                  <Errors items={data.errors.estado_financiamiento} />
                </div>
                <div className="col-md-6 form-group">
                  <label htmlFor="id_informe_complementario_modifica_prestaciones">Informe Técnico Complementario - Modificación de Prestaciones</label>
                  {select("informe_complementario_modifica_prestaciones", !incorporacion)}
                  <Errors items={data.errors.informe_complementario_modifica_prestaciones} />
                </div>
              </div>
              {uncertain && <div className="alert alert-warning" role="alert">{UNCERTAIN}</div>}
            </div>
            <div className="card-footer gt-actions">
              <a href={data.urls.cancelar} className="btn btn-outline-secondary">Cancelar</a>
              <button type="submit" className="btn btn-primary" disabled={pending || uncertain || undefined}>Crear borrador</button>
            </div>
          </form>
        </section>
      </div>
      <aside className="col-xl-4">
        <div className="gt-help">
          <h2><i className="fas fa-lightbulb" /> Antes de crear</h2>
          <p>Las condiciones no se editan después de crear el template. Si necesitás resolver otra combinación, creá un template independiente.</p>
          <p className="mb-0">Después se genera una versión en borrador para cargar el contenido y, cuando esté validada, publicarla.</p>
        </div>
      </aside>
    </div>
  </Frame>;
}

function CrearRoute() {
  const endpoint = `${API}crear/`;
  const [state] = useMainResource(endpoint, crearValid);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: "Crear template", heading: HEADING, breadcrumb: <Crumbs items={[ROOT, ["Crear template", null]]} />, content: <CrearPage data={data} endpoint={endpoint} />,
  }));
}

export const admisionesTemplatesFormRoute: RouteDefinition<Params> = {
  name: "comedores-gestor-templates-form",
  match: (pathname) => (pathname === `${BASE}crear/` ? { page: "crear" } : null),
  render: () => <CrearRoute />,
};
