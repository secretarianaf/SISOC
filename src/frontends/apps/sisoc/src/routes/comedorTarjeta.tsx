/* eslint-disable react-refresh/only-export-components -- route module: the validators and the navigation seam are exported for the tests. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { resetAfterRejectedPost } from "./nativeParity";
import Select2, { type Choice } from "./select2";
import type { RouteDefinition } from "./types";

/**
 * CO07.03 `responsable_tarjeta_form.html`: the card holder of a comedor. The page reads and saves through
 * `/api/web/comedores/comedores/<id>/responsable-tarjeta/`, which runs the native
 * `ResponsableTarjetaComedorUpdateView` (route permission, exact `Tecnico Comedor` group, program and
 * object scope; `ResponsableTarjetaComedorForm` with its Provincia > Municipio > Localidad chain). React
 * lays out the nine fields the server projected; the chain reloads its options like `ubicacionSelects.js`.
 */
export type TarjetaField = {
  name: string; label: string; type: string; required: boolean; help: string; value: string; options: Choice[] | null; errors: string[];
  attrs: Record<string, string>;
};
export type TarjetaForm = {
  comedor_id: number; fields: TarjetaField[]; non_field_errors: string[];
  urls: { ficha: string; municipios: string; localidades: string };
};

const NAMES = ["nombre", "mail", "dni", "cuit", "telefono", "domicilio", "provincia", "municipio", "localidad"].map((n) => `responsable_tarjeta_${n}`);
const PLACEHOLDER = { provincia: "Seleccione una provincia", municipio: "Seleccione un municipio", localidad: "Seleccione una localidad" };
const UNCERTAIN = "No se pudo confirmar el resultado. Recargue la página antes de reintentar.";

const optionValid = (o: unknown): o is Choice => record(o) && text(o.value) && text(o.label);
const fieldValid = (f: unknown): f is TarjetaField => record(f) && text(f.name) && text(f.label) && text(f.type) && typeof f.required === "boolean" && text(f.help) &&
  text(f.value) && (f.options === null || (Array.isArray(f.options) && f.options.every(optionValid))) && Array.isArray(f.errors) && f.errors.every(text) &&
  record(f.attrs) && Object.values(f.attrs).every(text);

export function tarjetaValid(v: unknown): v is TarjetaForm {
  return record(v) && typeof v.comedor_id === "number" && Array.isArray(v.fields) && v.fields.length === NAMES.length && v.fields.every(fieldValid) &&
    NAMES.every((n, i) => (v.fields as TarjetaField[])[i].name === n) && Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) &&
    record(v.urls) && internal(v.urls.ficha) && text(v.urls.municipios) && text(v.urls.localidades);
}

const payloadValid = (v: unknown): v is { form: TarjetaForm } => record(v) && tarjetaValid(v.form);

/** Full-page navigation and the AJAX loader of the chain; replaceable in tests. */
export const comedorTarjetaNavigation = {
  assign: (to: string) => window.location.assign(to),
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then((r) => r.json()),
};

type Values = Record<string, string>;
const valuesOf = (form: TarjetaForm): Values => Object.fromEntries(form.fields.map((f) => [f.name, f.value]));
const optionsOf = (form: TarjetaForm, name: string): Choice[] => form.fields.find((f) => f.name === name)?.options ?? [];
const blank = (key: "municipio" | "localidad"): Choice[] => [{ value: "", label: PLACEHOLDER[key] }];

function TarjetaContent({ form: inicial }: { form: TarjetaForm }) {
  const [form, setForm] = useState(inicial);
  const [values, setValues] = useState<Values>(() => valuesOf(inicial));
  const [municipios, setMunicipios] = useState<Choice[]>(() => optionsOf(inicial, "responsable_tarjeta_municipio"));
  const [localidades, setLocalidades] = useState<Choice[]>(() => optionsOf(inicial, "responsable_tarjeta_localidad"));
  const [loading, setLoading] = useState({ municipio: false, localidad: false });
  const [parents, setParents] = useState<Record<string, HTMLElement | null>>({});
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState("");
  const busy = useRef(false);
  const by = new Map(form.fields.map((f) => [f.name, f]));
  const set = (name: string, v: string) => setValues((cur) => ({ ...cur, [name]: v }));
  const setParent = (key: string, el: HTMLElement | null) => { if (el && parents[key] !== el) setParents((cur) => (cur[key] === el ? cur : { ...cur, [key]: el })); };

  async function cargar(url: string): Promise<Choice[]> {
    try {
      const rows = await comedorTarjetaNavigation.load(url);
      return Array.isArray(rows) ? rows.filter((g) => record(g) && Number.isSafeInteger(g.id) && text(g.nombre)).map((g) => ({ value: String((g as { id: number }).id), label: String((g as { nombre: string }).nombre) })) : [];
    } catch { return []; }
  }
  async function onProvincia(valor: string) {
    setValues((cur) => ({ ...cur, responsable_tarjeta_municipio: "", responsable_tarjeta_localidad: "" }));
    setMunicipios(blank("municipio")); setLocalidades(blank("localidad"));
    if (!valor) return;
    setLoading((c) => ({ ...c, municipio: true }));
    const rows = await cargar(`${form.urls.municipios}?provincia_id=${encodeURIComponent(valor)}`);
    setMunicipios([...blank("municipio"), ...rows]);
    setLoading((c) => ({ ...c, municipio: false }));
  }
  async function onMunicipio(valor: string) {
    setValues((cur) => ({ ...cur, responsable_tarjeta_localidad: "" }));
    setLocalidades(blank("localidad"));
    if (!valor) return;
    setLoading((c) => ({ ...c, localidad: true }));
    const rows = await cargar(`${form.urls.localidades}?municipio_id=${encodeURIComponent(valor)}`);
    setLocalidades([...blank("localidad"), ...rows]);
    setLoading((c) => ({ ...c, localidad: false }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams();
    for (const name of NAMES) body.set(name, values[name] ?? "");
    let message = UNCERTAIN;
    try {
      const { data, status } = await webClient.post(`web/comedores/comedores/${form.comedor_id}/responsable-tarjeta/`, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 });
      if (status === 400 && record(data) && tarjetaValid(data.form)) {
        setForm(data.form); setValues(valuesOf(data.form));
        setMunicipios(optionsOf(data.form, "responsable_tarjeta_municipio")); setLocalidades(optionsOf(data.form, "responsable_tarjeta_localidad"));
        busy.current = false; setPending(false); resetAfterRejectedPost();
        return;
      }
      if (status < 300 && record(data) && internal(data.redirect)) { comedorTarjetaNavigation.assign(data.redirect); return; }
      if (status === 403 && record(data) && text(data.detail)) message = data.detail;
    } catch {
      // Network error or timeout after sending: the result is unknown, nothing is retried.
    }
    busy.current = false; setPending(false); setUncertain(message);
  }

  /** `{{ form.x|as_crispy_field }}` with its label, asterisk and errors. */
  const campo = (name: string, control: (f: TarjetaField, id: string, cls: string) => ReactNode) => {
    const f = by.get(name)!;
    const id = `id_${name}`;
    const invalid = f.errors.length > 0;
    const widget = f.type === "select" ? "select form-select" : `${f.type === "email" ? "emailinput" : "textinput"} form-control`;
    return (
      <div id={`div_${id}`} className="mb-3">
        <label htmlFor={id} className={`form-label${f.required ? " requiredField" : ""}`}>{f.label}{f.required && <span className="asteriskField">*</span>}</label>
        {control(f, id, `${widget}${invalid ? " is-invalid" : ""}`)}
        {f.errors.map((e, i) => <p key={e} id={`error_${i + 1}_${id}`} className="invalid-feedback"><strong>{e}</strong></p>)}
        {f.help && <div id={`hint_${id}`} className="form-text">{f.help}</div>}
      </div>
    );
  };
  const textField = (name: string) => campo(name, (f, id, cls) => (
    <input type={f.type} name={f.name} id={id} className={cls} value={values[f.name] ?? ""} required={f.required || undefined} maxLength={f.attrs.maxlength ? Number(f.attrs.maxlength) : undefined}
      aria-describedby={f.errors.length ? `error_1_${id}` : undefined} onChange={(e) => set(f.name, e.target.value)} />
  ));
  const select = (key: "provincia" | "municipio" | "localidad", choices: Choice[]) => campo(`responsable_tarjeta_${key}`, (f, id) => (
    <Select2 id={id} name={f.name} choices={choices} value={[values[f.name] ?? ""]} invalid={f.errors.length > 0} placeholder={PLACEHOLDER[key]}
      selectClassName="select form-select" selectProps={{ "aria-describedby": f.errors.length ? `error_1_${id}` : undefined }} noResults="No se encontraron resultados"
      hideEmptyChoice clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown"
      dropdownParent={key === "provincia" ? undefined : parents[key] ?? null}
      onChange={(v) => { const next = v[0] ?? ""; set(f.name, next); if (key === "provincia") void onProvincia(next); if (key === "municipio") void onMunicipio(next); }} />
  ));
  const ubicacion = (key: "municipio" | "localidad", choices: Choice[]) => (
    <div className="col-md-4">
      <div id={`responsable-tarjeta-${key}-loader`} className={`skeleton-loader${loading[key] ? "" : " d-none"}`} />
      <div id={`responsable-tarjeta-${key}-field`} ref={(el) => setParent(key, el)} style={loading[key] ? { opacity: "0.3" } : undefined}>{select(key, choices)}</div>
    </div>
  );

  return (
    <>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
    <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
    <div className="card">
      <div className="card-header">
        <h3>Responsable de la Tarjeta</h3>
      </div>
      <div className="card-body">
        <form method="post" id="responsableTarjetaForm" onSubmit={submit}>
          <div className="row">
            <div className="col-md-6">{textField("responsable_tarjeta_nombre")}</div>
            <div className="col-md-6">{textField("responsable_tarjeta_mail")}</div>
            <div className="col-md-6">{textField("responsable_tarjeta_dni")}</div>
            <div className="col-md-6">{textField("responsable_tarjeta_cuit")}</div>
            <div className="col-md-6">{textField("responsable_tarjeta_telefono")}</div>
            <div className="col-md-6">{textField("responsable_tarjeta_domicilio")}</div>
            <div className="col-md-4">{select("provincia", optionsOf(form, "responsable_tarjeta_provincia"))}</div>
            {ubicacion("municipio", municipios)}
            {ubicacion("localidad", localidades)}
          </div>
          <button className="btn btn-primary" type="submit" disabled={pending || !!uncertain}>Guardar</button>
          {" "}<a className="btn btn-secondary" href={form.urls.ficha}>Cancelar</a>
          {uncertain && <p role="alert" className="mb-0 mt-2">{uncertain}</p>}
        </form>
      </div>
    </div>
    </>
  );
}

function TarjetaPage({ id }: { id: string }) {
  const endpoint = `web/comedores/comedores/${id}/responsable-tarjeta/`;
  const [state] = useMainResource(endpoint, payloadValid);
  return renderMain(state, "Cargando responsable de la tarjeta…", (data) => ({
    title: "",
    heading: "",
    breadcrumb: <></>,
    content: <TarjetaContent key={endpoint} form={data.form} />,
  }));
}

export const comedorTarjetaRoute: RouteDefinition<{ id: string }> = {
  name: "comedores-responsable-tarjeta",
  match(pathname) {
    const m = pathname.match(/^\/comedores\/([0-9]+)\/responsable-tarjeta\/editar$/);
    return m ? { id: m[1] } : null;
  },
  render(params) {
    return <TarjetaPage key={params.id} id={params.id} />;
  },
};
