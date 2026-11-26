/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators are exported for the tests. */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import Select2 from "./select2";
import { bool, integer } from "./vatShared";
import { ConfirmDelete, Control, CsrfInput, Err, Select2Links, fieldValid, ICON, useForbidden, useWriteForm, type Field } from "./vatFormShared";
import { UncertainNotice } from "./vatCentrosListaShared";
import type { RouteDefinition } from "./types";

/**
 * V06.01 ubicación forms: `institucion/ubicacion_form.html` (alta y edición, with the Departamento -> Localidad
 * cascade of its inline script) and `ubicacion_confirm_delete.html`. Fields, widget attributes and errors come from
 * `/api/web/vat/institucion/ubicaciones/`, which runs the native ModelForm and views; the POST persists through their
 * `form_valid`/`post`. The cascade asks the same native AJAX endpoints as the template (departamentos of the centro,
 * localidades of the departamento). A `?centro=` query locks the centro and travels with the POST like `action=""`.
 */
export type UbicacionFormData = { editing: boolean; fields: Field[]; non_field_errors: string[]; urls: { list: string; municipios: string; localidades: string } };
export type UbicacionDeleteData = { rol: string; localidad: string; centro: string; urls: { detail: string } };

const API = "web/vat/institucion/ubicaciones/";
// Only the widgets the native template draws (the form also has `nombre_ubicacion`, which the template leaves out).
const FIELDS = ["centro", "departamento", "localidad", "rol_ubicacion", "domicilio", "es_principal", "observaciones"];

export const ubicacionFormValid = (v: unknown): v is UbicacionFormData => record(v) && bool(v.editing) && Array.isArray(v.fields) &&
  v.fields.length === FIELDS.length && v.fields.every(fieldValid) && (v.fields as Field[]).every((f, n) => f.name === FIELDS[n]) &&
  Array.isArray(v.non_field_errors) && v.non_field_errors.every(text) && record(v.urls) && internal(v.urls.list) && internal(v.urls.municipios) && internal(v.urls.localidades);
export const ubicacionDeleteValid = (v: unknown): v is UbicacionDeleteData => record(v) && ["rol", "localidad", "centro"].every((k) => text(v[k])) &&
  record(v.urls) && internal(v.urls.detail);

type Choice = { value: string; label: string };
type Geo = { id: number; nombre: string };
const geoValid = (v: unknown): v is Geo[] => Array.isArray(v) && v.every((g) => record(g) && integer(g.id) && text(g.nombre));
const municipiosValid = (v: unknown): v is { municipios: Geo[] } => record(v) && geoValid(v.municipios);

/** The native AJAX endpoints of the cascade (same session, `X-Requested-With` like the inline script); replaceable in tests. */
export const vatGeography = {
  load: (url: string): Promise<unknown> => fetch(url, { credentials: "same-origin", headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" } }).then((r) => r.json()),
};

const EMPTY: Choice = { value: "", label: "" };
const toChoices = (rows: Geo[]): Choice[] => [EMPTY, ...rows.map((g) => ({ value: String(g.id), label: g.nombre }))];

const Group = ({ icon, children }: { icon: string; children: ReactNode }) => <div className="input-group">
  <span className="input-group-text bg-light border-0"><i className={icon} style={ICON} /></span>{children}
</div>;

/** A Select2 field as `Control` draws it, with the choices and the disabled state the cascade controls. */
function CascadeSelect({ f, choices, value, onChange, disabled }: { f: Field; choices: Choice[]; value: string; onChange: (v: string) => void; disabled: boolean }) {
  return <Select2 id={f.id} name={f.name} choices={choices} value={[value]} onChange={(v) => onChange(v[0] ?? "")} disabled={disabled}
    placeholder={f.attrs["data-placeholder"] ?? choices.find((c) => c.value === "")?.label}
    selectClassName={f.attrs.class ?? ""} selectProps={{ required: f.attrs.required !== undefined ? true : undefined, "data-width": f.attrs["data-width"] }}
    hideEmptyChoice noResults="No results found" clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />;
}

function UbicacionForm({ initial, endpoint, forbidden }: { initial: UbicacionFormData; endpoint: string; forbidden: (d: unknown) => void }) {
  const { data, state, set, uncertain, submit } = useWriteForm({ initial, endpoint, forbidden, valid: ubicacionFormValid });
  const [centro, departamento, localidad, rol, domicilio, principal, observaciones] = data.fields;
  const [departamentos, setDepartamentos] = useState<Choice[]>(departamento.choices);
  const [localidades, setLocalidades] = useState<Choice[]>(localidad.choices);
  const [localidadBloqueada, setLocalidadBloqueada] = useState(false);
  const ticket = useRef(0);

  /** `cargarLocalidades`: the options of the departamento, choosing the current one when it is among them. */
  async function cargarLocalidades(municipio: string | null, seleccionada: string | null, mine: number) {
    set("localidad", "");
    if (!municipio) {
      setLocalidades([EMPTY]);
      setLocalidadBloqueada(true);
      return;
    }
    setLocalidadBloqueada(true);
    setLocalidades([{ value: "", label: "Cargando..." }]);
    let rows: Geo[] | null;
    try {
      const result = await vatGeography.load(`${data.urls.localidades}?municipio_id=${encodeURIComponent(municipio)}`);
      rows = geoValid(result) ? result : null;
    } catch {
      rows = null;
    }
    if (mine !== ticket.current) return;
    if (!rows) {
      setLocalidades([EMPTY]);
      return;
    }
    const options = toChoices(rows);
    setLocalidades(options);
    setLocalidadBloqueada(false);
    if (seleccionada && options.some((o) => o.value === seleccionada)) set("localidad", seleccionada);
  }

  /** `cargarDepartamentos`: the departamentos of the centro; a single one is chosen by itself. */
  async function cargarDepartamentos(centroId: string) {
    const mine = ++ticket.current;
    set("departamento", "");
    if (!centroId) {
      setDepartamentos([EMPTY]);
      void cargarLocalidades(null, null, mine);
      return;
    }
    let rows: Geo[] | null;
    try {
      const result = await vatGeography.load(`${data.urls.municipios}?centro_id=${encodeURIComponent(centroId)}`);
      rows = municipiosValid(result) ? result.municipios : null;
    } catch {
      rows = null;
    }
    if (!rows || mine !== ticket.current) return;
    setDepartamentos(toChoices(rows));
    const unico = rows.length === 1 ? String(rows[0].id) : "";
    set("departamento", unico);
    void cargarLocalidades(unico || null, null, mine);
  }

  // The inline script of the template, on page load: with a centro, the localidades of the initial departamento.
  useEffect(() => {
    const mine = ++ticket.current;
    setDepartamentos(departamento.choices);
    setLocalidades(localidad.choices);
    setLocalidadBloqueada(false);
    if (!String(centro.value)) return;
    let inicial = String(departamento.value);
    if (!inicial) {
      const opciones = departamento.choices.filter((o) => o.value);
      if (opciones.length === 1) {
        inicial = opciones[0].value;
        set("departamento", inicial);
      }
    }
    void cargarLocalidades(inicial || null, String(localidad.value) || null, mine);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const label = (f: Field, required = false) => <label htmlFor={f.id} className="form-label fw-600">{f.label}{required ? <>{" "}<span className="text-danger">*</span></> : null}</label>;
  const control = (f: Field, icon: string) => <Group icon={icon}><Control f={f} state={state} set={set} /></Group>;
  const bloqueado = centro.attrs.disabled !== undefined;
  return <>
    <Select2Links />
    <link rel="stylesheet" href="/static/custom/css/vat_design.css" />
    <div className="vat-ui container-fluid py-4">
      <div className="vp-hero"><h1>{data.editing ? "Editar Ubicación" : "Nueva Ubicación"}</h1></div>
      <div className="row">
        <div className="col-lg-8"><div className="card border-0 shadow-sm">
          <div className="card-header"><h5 className="mb-0"><i className="bi bi-file-earmark-text me-2" />Información General</h5></div>
          <div className="card-body p-4">
            <form method="post" noValidate onSubmit={(e) => void submit(e)}>
              <CsrfInput />
              <UncertainNotice show={uncertain} />
              <div className="row mb-4">
                <div className="col-md-6">{label(centro, true)}
                  <Group icon="bi-building"><CascadeSelect f={centro} choices={centro.choices} value={String(state.centro ?? "")} disabled={bloqueado}
                    onChange={(v) => { set("centro", v); void cargarDepartamentos(v); }} /></Group>
                  <Err f={centro} /></div>
                <div className="col-md-6">{label(departamento)}
                  <Group icon="bi-map"><CascadeSelect f={departamento} choices={departamentos} value={String(state.departamento ?? "")} disabled={false}
                    onChange={(v) => { set("departamento", v); const mine = ++ticket.current; void cargarLocalidades(v || null, null, mine); }} /></Group>
                  <Err f={departamento} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(localidad, true)}
                  <Group icon="bi-geo"><CascadeSelect f={localidad} choices={localidades} value={String(state.localidad ?? "")} disabled={localidadBloqueada}
                    onChange={(v) => set("localidad", v)} /></Group>
                  <Err f={localidad} /></div>
                <div className="col-md-6">{label(rol, true)}{control(rol, "bi-diagram-3")}<Err f={rol} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">{label(domicilio)}{control(domicilio, "bi-signpost")}<Err f={domicilio} /></div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6"><div className="form-check form-switch">
                  <Control f={principal} state={state} set={set} />{" "}<label className="form-check-label fw-600" htmlFor={principal.id}>{principal.label}</label>
                </div></div>
              </div>
              <div className="row mb-4"><div className="col-md-12">
                {label(observaciones)}<Control f={observaciones} state={state} set={set} /><Err f={observaciones} />
              </div></div>
              <hr className="my-4" />
              <div className="d-flex gap-2 justify-content-end">
                <a href={data.urls.list} className="btn btn-outline-secondary"><i className="bi bi-x-lg me-2" />Cancelar</a>
                <button type="submit" className="btn btn-primary"><i className="bi bi-check-lg me-2" />{" "}{data.editing ? "Actualizar" : "Crear"}</button>
              </div>
            </form>
          </div>
        </div></div>
        <div className="col-lg-4"><div className="card border-0 shadow-sm bg-light"><div className="card-body">
          <h6 className="card-title fw-600"><i className="bi bi-info-circle me-2" />Información</h6>
          <div className="small text-muted"><p>Sede Principal, Anexo, Dependencia o Punto de Atención.</p></div>
        </div></div></div>
      </div>
    </div>
  </>;
}

function FormPage({ id }: { id?: string }) {
  const endpoint = `${id ? `${API}${id}/editar/` : `${API}nuevo/`}${window.location.search}`;
  const [state, setState] = useMainResource(endpoint, ubicacionFormValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando formulario…", (data) => ({
    title: data.editing ? "Editar Ubicación" : "Nueva Ubicación", breadcrumb: null,
    content: <UbicacionForm initial={data} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

function DeletePage({ id }: { id: string }) {
  const endpoint = `${API}${id}/eliminar/`;
  const [state, setState] = useMainResource(endpoint, ubicacionDeleteValid);
  const forbidden = useForbidden(setState);
  return renderMain(state, "Cargando confirmación…", (data) => ({
    title: "Eliminar Ubicación", breadcrumb: null,
    content: <ConfirmDelete title={data.rol} subtitle={`${data.localidad} • ${data.centro}`} cancel={data.urls.detail} endpoint={endpoint} forbidden={forbidden} />,
  }));
}

type Params = { mode: "nuevo" | "editar" | "eliminar"; id?: string };

// Native URLs of `VAT/urls.py`.
const PATH = /^\/vat\/institucion\/ubicaciones\/(?:(nuevo)|([0-9]+)\/(editar|eliminar))\/$/;

export const vatUbicacionesFormRoute: RouteDefinition<Params> = {
  name: "vat-ubicaciones-form",
  match(pathname) {
    const m = pathname.match(PATH);
    if (!m) return null;
    return m[1] ? { mode: "nuevo" } : { mode: m[3] as "editar" | "eliminar", id: m[2] };
  },
  render({ mode, id }) {
    if (mode === "eliminar") return <DeletePage key={id} id={id!} />;
    return <FormPage key={`${mode}:${id ?? ""}`} id={id} />;
  },
};
