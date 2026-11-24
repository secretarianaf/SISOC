/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators live with the screen. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import type { RequiredPasswordPresentation } from "../RequiredPasswordChange";
import { safeInternalPath } from "../webAccess";
import { Control, type Api, type Choice, type Section, type UsuarioField, type Values } from "./usuariosControls";
import { CreatedUsersCard, MobileBody, TeamsBody, TerritorialComedorBody, type CreatedUser, type Operator } from "./usuariosMobile";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import Select2 from "./select2";
import { accepted, client, errorsValid, messagesValid, navigation, presentationValid, record, type FieldErrors, type JobMessage } from "./userImport";

/**
 * `user/user_form.html` (core cards): personal data, access, DataCalle, Inspecciones escolares,
 * groups, territorial scope and access administration. The server decides which cards exist, which
 * fields are disabled and every error; the browser only draws the native markup, repeats the
 * visibility rules of `user_mobile_access.js`/`usuarioprovincial.js` and posts the enabled
 * controls. A rejected post re-renders the form with the bound values.
 */
type Scope = { provincia_id: string | number | null; municipio_id?: string | number | null; localidad_id?: string | number | null };
export type { UsuarioField };
export type UsuarioFormData = {
  mode: "create" | "edit";
  title: string;
  object: { id: number; username: string } | null;
  sections: Section[];
  identity_present: string[];
  errors: FieldErrors;
  comedores: { sections: string[]; runtime_required: boolean; operator?: Operator | null; created_users?: CreatedUser[] };
  territorial: { initial: Scope[]; municipios_url: string; localidades_url: string };
  urls: { cancel: string };
  submit_text: string;
  credential: { temporary_password: string } | null;
  messages: JobMessage[];
  presentation: RequiredPasswordPresentation;
};

const KINDS = ["text", "email", "password", "boolean", "radio", "select", "multiselect", "hidden"];
const fieldValid = (f: unknown) => record(f) && typeof f.name === "string" && KINDS.includes(f.kind as string) && typeof f.label === "string" &&
  typeof f.required === "boolean" && typeof f.disabled === "boolean" && typeof f.help_text === "string" &&
  (f.max_length === null || typeof f.max_length === "number") &&
  (typeof f.value === "string" || typeof f.value === "boolean" || (Array.isArray(f.value) && f.value.every((v) => typeof v === "string"))) &&
  (f.choices === undefined || (Array.isArray(f.choices) && f.choices.every((c) => record(c) && typeof c.value === "string" && typeof c.label === "string")));

export function usuarioFormValid(v: unknown): v is UsuarioFormData {
  return record(v) && presentationValid(v.presentation) && (v.mode === "create" || v.mode === "edit") && typeof v.title === "string" &&
    typeof v.submit_text === "string" && Array.isArray(v.sections) &&
    v.sections.every((s) => record(s) && typeof s.key === "string" && Array.isArray(s.fields) && s.fields.every(fieldValid)) &&
    Array.isArray(v.identity_present) && v.identity_present.every((n) => typeof n === "string") && errorsValid(v.errors) &&
    record(v.comedores) && Array.isArray(v.comedores.sections) && record(v.territorial) && Array.isArray(v.territorial.initial) &&
    typeof v.territorial.municipios_url === "string" && typeof v.territorial.localidades_url === "string" &&
    record(v.urls) && safeInternalPath(v.urls.cancel) !== null && messagesValid(v.messages) &&
    (v.credential === null || (record(v.credential) && typeof v.credential.temporary_password === "string"));
}

/** Card levels of `user_form.css`: core data, a web module, or a mobile app (with the «Habilitado» badge). */
type Level = "principal" | "web" | "app";
const CARDS: Record<string, { id?: string; icon: string; title: string; description: string; level: Level }> = {
  personal: { icon: "fas fa-user", title: "Datos personales", description: "Nombre, documento, correo y tipo de usuario.", level: "principal" },
  access: { icon: "fas fa-key", title: "Datos de acceso", description: "Usuario y contraseña para ingresar.", level: "principal" },
  permissions: { id: "backoffice-permisos-card", icon: "fas fa-shield-alt", title: "Permisos y roles", description: "Grupos y rol que definen qué puede hacer.", level: "web" },
  territorial: { id: "backoffice-config-card", icon: "fas fa-map", title: "Alcance territorial", description: "Provincias, municipios o localidades en los que trabaja.", level: "web" },
  teams: { id: "backoffice-equipos-card", icon: "fas fa-users-cog", title: "Equipos técnicos (Comedores)", description: "Coordinación y duplas asignadas.", level: "web" },
  delegation: { id: "backoffice-admin-card", icon: "fas fa-user-shield", title: "Administración de accesos", description: "Permisos directos, accesos web/SIIS y qué puede delegar.", level: "web" },
  mobile: { id: "mobile-access-card", icon: "fas fa-mobile-alt", title: "Acceso a Espacios comunitarios", description: "SISOC - Mobile para espacios comunitarios y su alcance.", level: "app" },
  territorial_comedor: { id: "territorial-comedor-card", icon: "fas fa-map-marked-alt", title: "SISOC - Mobile Territorial comedor", description: "Acceso territorial a comedores por provincia.", level: "app" },
  datacalle: { id: "relevador-calle-card", icon: "fas fa-street-view", title: "SISOC - Mobile DataCalle", description: "Relevamiento en calle: rol y provincias.", level: "app" },
  inspecciones: { id: "inspecciones-escolares-card", icon: "fas fa-school", title: "Inspecciones escolares", description: "App de inspecciones escolares y su rol.", level: "app" },
};
const CARD_CLASS: Record<Level, string> = { principal: "card user-card user-card--principal", web: "card user-card user-card--modulo user-card--web", app: "card user-card user-card--modulo" };

/** The three numbered blocks of the template, with their cards in template order. */
const GROUPS = [
  { key: "datos", title: "Datos del usuario", description: "Identidad y credenciales de ingreso.", cards: ["personal", "access"] },
  { key: "web", id: "user-form-grupo-web", title: "Permisos en SISOC web", description: "Qué puede ver y hacer en el sistema y sobre qué territorio.", cards: ["permissions", "territorial", "teams", "delegation"] },
  { key: "mobile", title: "Aplicaciones mobile", description: "Activá solo las apps que la persona va a usar.", cards: ["mobile", "territorial_comedor", "datacalle", "inspecciones"] },
] as const;
const GROUPED: string[] = GROUPS.flatMap((g) => [...g.cards]);

function Credential({ credential }: { credential: UsuarioFormData["credential"] }) {
  if (!credential) return null;
  return (
    <div className="alert alert-warning" role="alert">
      <strong>Contraseña temporal vigente:</strong>{" "}
      <span className="ms-2">{credential.temporary_password}</span>
      <div className="small mt-2">Se mostrará aquí hasta que el usuario cambie su contraseña.</div>
    </div>
  );
}

/** QA-0017: the eye sits inside the field (`.user-form__password`), icon only, as the native script places it. */
function PasswordField({ spec, api, hidden = false }: { spec: UsuarioField; api: Api; hidden?: boolean }) {
  const [visible, setVisible] = useState(false);
  const action = visible ? "Ocultar la contraseña" : "Mostrar la contraseña";
  const eye = (
    <button type="button" id="toggle-password" className="btn user-form__ojo" aria-pressed={visible} aria-label={action} title={action} onClick={() => setVisible(!visible)}>
      <i className={`fas ${visible ? "fa-eye-slash" : "fa-eye"}`} aria-hidden="true" />
    </button>
  );
  return (
    <div className="col-md-6" id="password-field-wrapper" style={hidden ? { display: "none" } : undefined}>
      <Control spec={spec} api={api} extra={visible ? "visible" : undefined} wrap={{ className: "user-form__password", after: eye }} />
    </div>
  );
}

type Option = { id: string | number; nombre: string };
type Row = { key: number; provincia: string; municipio: string; localidad: string; municipios: Option[] | null; localidades: Option[] | null };
export const territorialTransport = {
  async options(url: string, key: string, id: string): Promise<Option[]> {
    const target = new URL(url, window.location.origin);
    target.searchParams.set(key, id);
    const response = await fetch(target.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" });
    return response.ok ? ((await response.json()) as Option[]) : [];
  },
};
const asId = (v: string | number | null | undefined) => (v === null || v === undefined ? "" : String(v));
const choicesOf = (options: Option[] | null, placeholder: string): Choice[] => [{ value: "", label: placeholder }, ...(options ?? []).map((o) => ({ value: String(o.id), label: o.nombre }))];

function ScopeRows({ rows, setRows, provinces, data, busy }: { rows: Row[]; setRows: (update: (rows: Row[]) => Row[]) => void; provinces: Choice[]; data: UsuarioFormData; busy: boolean }) {
  const patch = (key: number, change: Partial<Row>) => setRows((current) => current.map((r) => (r.key === key ? { ...r, ...change } : r)));
  async function province(row: Row, value: string) {
    patch(row.key, { provincia: value, municipio: "", localidad: "", municipios: null, localidades: null });
    if (value) patch(row.key, { municipios: await territorialTransport.options(data.territorial.municipios_url, "provincia_id", value) });
  }
  async function municipality(row: Row, value: string) {
    patch(row.key, { municipio: value, localidad: "", localidades: null });
    if (value) patch(row.key, { localidades: await territorialTransport.options(data.territorial.localidades_url, "municipio_id", value) });
  }
  return (
    <tbody id="territorial-scopes-list">
      {rows.map((row) => (
        <tr key={row.key}>
          <td><Select2 id={`scope-${row.key}-provincia`} name="" choices={[{ value: "", label: "Seleccione provincia" }, ...provinces]} value={[row.provincia]} onChange={(v) => void province(row, v[0] ?? "")} selectClassName="form-control form-control-sm" selectProps={{ "aria-label": "Provincia" }} noResults="No results found" disabled={busy} /></td>
          <td><Select2 id={`scope-${row.key}-municipio`} name="" choices={choicesOf(row.municipios, row.provincia ? "Todos los municipios" : "Seleccione provincia primero")} value={[row.municipio]} onChange={(v) => void municipality(row, v[0] ?? "")} selectClassName="form-control form-control-sm" selectProps={{ "aria-label": "Municipio" }} noResults="No results found" disabled={busy || !row.municipios?.length} /></td>
          <td><Select2 id={`scope-${row.key}-localidad`} name="" choices={choicesOf(row.localidades, row.municipio ? "Todas las localidades" : "Seleccione municipio primero")} value={[row.localidad]} onChange={(v) => patch(row.key, { localidad: v[0] ?? "" })} selectClassName="form-control form-control-sm" selectProps={{ "aria-label": "Localidad" }} noResults="No results found" disabled={busy || !row.localidades?.length} /></td>
          <td className="text-right">
            <button type="button" className="btn btn-outline-danger btn-sm" disabled={busy} onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}>
              <i className="fas fa-trash" aria-hidden="true" />{" "}<span className="sr-only">Quitar alcance</span>
            </button>
          </td>
        </tr>
      ))}
    </tbody>
  );
}

/** POST once; an unconfirmed outcome is reported, never resubmitted. The generated password (creation only) rides this answer. */
async function postForm(endpoint: string, body: URLSearchParams) {
  try {
    const { data, status } = await client.post(endpoint, body, { validateStatus: accepted });
    if (status === 403) return { kind: "forbidden" as const, data };
    if (record(data) && data.ok === true && typeof data.redirect === "string" && data.redirect === safeInternalPath(data.redirect) && data.redirect.startsWith("/usuarios/")) {
      const credential = record(data.credential) && typeof data.credential.temporary_password === "string" ? data.credential.temporary_password : null;
      return { kind: "redirect" as const, to: data.redirect, credential };
    }
    return { kind: "uncertain" as const };
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: unknown } }).response;
    if (response?.status === 400) return { kind: "invalid" as const, data: response.data };
    return { kind: "uncertain" as const };
  }
}

const serialize = (rows: Row[]) => JSON.stringify(rows.map((r) => ({ provincia_id: r.provincia || null, municipio_id: r.municipio || null, localidad_id: r.localidad || null })));
let rowKey = 0;
const blank = (scope: Scope): Row => ({ key: ++rowKey, provincia: asId(scope.provincia_id), municipio: asId(scope.municipio_id), localidad: asId(scope.localidad_id), municipios: null, localidades: null });

function initialValues(data: UsuarioFormData): Values {
  const values: Values = {};
  data.sections.forEach((s) => s.fields.forEach((f) => { values[f.name] = f.value; }));
  return values;
}

export function UsuarioFormContent({ data: initial, endpoint, onForbidden }: { data: UsuarioFormData; endpoint: string; onForbidden: (data: unknown) => void }) {
  const [data, setData] = useState(initial);
  const [values, setValues] = useState<Values>(() => initialValues(initial));
  const [errors, setErrors] = useState<FieldErrors>(initial.errors);
  const [rows, setRows] = useState<Row[]>(() => initial.territorial.initial.map(blank));
  const [revision, setRevision] = useState(0);
  const [created, setCreated] = useState<{ to: string; password: string } | null>(null);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const fields = data.sections.flatMap((s) => s.fields);
  const provinces = (fields.find((f) => f.name === "provincia")?.choices ?? []).filter((c) => c.value !== "");
  // The native script loads each row's options on start; the same here, once per initial row.
  useEffect(() => {
    let active = true;
    initial.territorial.initial.forEach((scope, index) => {
      void (async () => {
        if (!scope.provincia_id) return;
        const municipios = await territorialTransport.options(initial.territorial.municipios_url, "provincia_id", asId(scope.provincia_id));
        const localidades = scope.municipio_id ? await territorialTransport.options(initial.territorial.localidades_url, "municipio_id", asId(scope.municipio_id)) : null;
        if (active) setRows((current) => current.map((r, i) => (i === index && r.municipios === null ? { ...r, municipios, localidades } : r)));
      })();
    });
    return () => { active = false; };
  }, [initial]);
  const api: Api = { values, errors, busy: pending || uncertain, set: (name, value) => setValues((current) => ({ ...current, [name]: value })) };
  const provincial = values.es_usuario_provincial === true;
  const hasMobile = data.sections.some((s) => s.key === "mobile");
  // `user_mobile_access.js`: a mobile user hides the backoffice cards and the password (subusers are left alone).
  const mobileOn = hasMobile && !data.comedores.operator && values.es_representante_pwa === true;
  const detail = (name: string, flag: string) => ({ id: name, style: values[flag] === true ? undefined : { display: "none" } });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || uncertain) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams();
    fields.filter((f) => !f.disabled).forEach((f) => {
      const value = f.name === "territorial_scopes" ? (provincial ? serialize(rows) : "[]") : values[f.name];
      if (Array.isArray(value)) value.forEach((v) => body.append(f.name, v));
      else if (typeof value === "boolean") { if (value) body.append(f.name, "on"); }
      else if (value !== undefined && !(f.kind === "radio" && value === "")) body.append(f.name, value);
    });
    data.identity_present.forEach((name) => body.append("_identity_present", name));
    const result = await postForm(endpoint, body);
    if (!mounted.current) return;
    if (result.kind === "redirect") {
      if (result.credential) { setCreated({ to: result.to, password: result.credential }); setPending(false); resetAfterRejectedPost(); return; }
      navigation.assign(result.to);
      return;
    }
    busy.current = false;
    if (result.kind === "forbidden") onForbidden(result.data);
    else if (result.kind === "invalid" && usuarioFormValid(result.data) && Object.keys(result.data.errors).length) {
      const next = result.data;
      setData(next); setValues(initialValues(next)); setErrors(next.errors); setRows(next.territorial.initial.map(blank)); setRevision((n) => n + 1); setPending(false);
      resetAfterRejectedPost();
    } else { setUncertain(true); setPending(false); }
  }

  const render = (section: Section) => {
    const card = CARDS[section.key];
    // The template moved `email` (an access field in the API) to the personal card: look fields up form-wide.
    const by = (name: string) => section.fields.find((f) => f.name === name) ?? fields.find((f) => f.name === name)!;
    const field = (name: string) => <Control spec={by(name)} api={api} />;
    let body: ReactNode;
    if (section.key === "personal") {
      body = <><div className="row"><div className="col-md-6">{field("first_name")}</div><div className="col-md-6">{field("last_name")}</div></div><div className="row"><div className="col-md-6">{field("dni")}</div><div className="col-md-6">{field("cuil")}</div></div><div className="row"><div className="col-md-6">{field("email")}</div><div className="col-md-6">{field("tipo_usuario")}</div></div></>;
    } else if (section.key === "access") {
      body = <><Credential credential={data.credential} /><div className="row"><div className="col-md-6">{field("username")}</div><PasswordField spec={by("password")} api={api} hidden={mobileOn} /></div>{hasMobile && <div id="mobile-password-help" className="alert alert-info mt-2 mb-0" style={mobileOn ? undefined : { display: "none" }}>Para usuarios con acceso a Espacios comunitarios la contraseña se genera automáticamente y deberá cambiarse en el primer ingreso.</div>}</>;
    } else if (section.key === "mobile") {
      body = <MobileBody section={section} api={api} operator={data.comedores.operator ?? null} />;
    } else if (section.key === "territorial_comedor") {
      body = <TerritorialComedorBody section={section} api={api} />;
    } else if (section.key === "teams") {
      body = <TeamsBody section={section} api={api} />;
    } else if (section.key === "datacalle") {
      body = <><div id="relevador-calle-toggle-wrapper">{field("es_relevador_calle")}</div><div {...detail("relevador-calle-detalle-wrapper", "es_relevador_calle")}>{field("datacalle_rol")}{field("provincias_datacalle")}</div></>;
    } else if (section.key === "inspecciones") {
      body = <><div id="inspecciones-escolares-toggle-wrapper">{field("es_inspector_escolar")}</div><div {...detail("inspecciones-escolares-detalle-wrapper", "es_inspector_escolar")}>{field("inspecciones_rol")}</div></>;
    } else if (section.key === "permissions") {
      body = <>{field("groups")}{field("rol")}</>;
    } else if (section.key === "territorial") {
      body = (
        <>
          {field("es_usuario_provincial")}
          <div className="d-none" id="legacy-provincia-field">{field("provincia")}</div>
          <input type="hidden" name="territorial_scopes" id="id_territorial_scopes" value={provincial ? serialize(rows) : "[]"} readOnly />
          <div id="territorial-scopes-panel" className="mb-3" style={provincial ? undefined : { display: "none" }}>
            <label className="form-label d-block">Alcances territoriales</label>
            {(errors.territorial_scopes ?? []).length > 0 && <div className="invalid-feedback d-block mb-2">{errors.territorial_scopes.map((e) => e.message).join(" ")}</div>}
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-2">
                <thead><tr><th scope="col">Provincia</th><th scope="col">Municipio</th><th scope="col">Localidad</th><th scope="col" className="text-end">Acción</th></tr></thead>
                <ScopeRows rows={rows} setRows={setRows} provinces={provinces} data={data} busy={pending || uncertain} />
              </table>
            </div>
            <button type="button" className="btn btn-outline-primary btn-sm" id="add-territorial-scope" disabled={pending || uncertain} onClick={() => setRows((current) => [...current, blank({ provincia_id: null })])}><i className="fas fa-plus me-1" />Agregar alcance</button>
          </div>
        </>
      );
    } else {
      body = <>{section.fields.map((f) => <Control key={f.name} spec={f} api={api} />)}</>;
    }
    return (
      <div className={CARD_CLASS[card?.level ?? "web"]} id={card?.id} key={section.key} style={mobileOn && card?.level === "web" ? { display: "none" } : undefined}>
        <div className="card-header user-card__header">
          <span className="user-card__icono" aria-hidden="true"><i className={card?.icon} /></span>
          <div className="user-card__textos">
            <h5 className="user-card__titulo">{card?.title ?? section.key}</h5>
            {card && <p className="user-card__descripcion">{card.description}</p>}
          </div>
          {card?.level === "app" && <span className="user-card__estado">Habilitado</span>}
        </div>
        <div className="card-body">{body}</div>
      </div>
    );
  };
  const present = new Map(data.sections.map((s) => [s.key, s]));
  const group = (g: (typeof GROUPS)[number]) => {
    const cards = g.cards.flatMap((key) => (present.has(key) ? [render(present.get(key)!)] : []));
    if (!cards.length) return null;
    const titleId = `grupo-${g.key}-titulo`;
    // `user_mobile_access.js`: a mobile user hides the whole web block, so its header is not left empty.
    return (
      <section className="user-form-grupo" id={"id" in g ? g.id : undefined} aria-labelledby={titleId} key={g.key} style={g.key === "web" && mobileOn ? { display: "none" } : undefined}>
        <header className="user-form-grupo__encabezado">
          <span className="user-form-grupo__numero" aria-hidden="true" />
          <div>
            <h4 className="user-form-grupo__titulo" id={titleId}>{g.title}</h4>
            <p className="user-form-grupo__descripcion">{g.description}</p>
          </div>
        </header>
        {cards}
      </section>
    );
  };

  if (created) {
    return (
      <div className="row"><div className="col">
        <p>Usuario mobile creado correctamente.</p>
        <Credential credential={{ temporary_password: created.password }} />
        <a href={safeInternalPath(created.to) ?? "/usuarios/"} className="btn btn-primary mb-3">Continuar</a>
      </div></div>
    );
  }
  return (
    <>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css" />
      <link rel="stylesheet" href="/static/custom/css/select2_theme.css" />
      <link rel="stylesheet" href="/static/custom/css/user_form.css" />
      <NativeToasts messages={data.messages} />
      <div className="row">
        <div className="col">
          <form key={revision} className="needs-validation user-form" noValidate method="POST" autoComplete="off" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <p className="user-form__intro">
              {data.object && <>Editando a <strong>{data.object.username}</strong>.{" "}</>}
              Completá los datos del usuario y habilitá solo los accesos que necesita.
            </p>
            {GROUPS.map(group)}
            {data.sections.filter((s) => !GROUPED.includes(s.key)).map(render)}
            {hasMobile && (data.comedores.created_users ?? []).length > 0 && <CreatedUsersCard users={data.comedores.created_users ?? []} />}
            <div className="user-form__acciones">
              <div className="row">
                <div className="col-md-12">
                  <div className="form-group mb-0 mt-3 d-flex justify-content-between">
                    <a href={safeInternalPath(data.urls.cancel) ?? "/usuarios/"} className="btn btn-secondary mb-3">Cancelar</a>
                    <div><button type="submit" className="btn btn-primary mb-3" disabled={pending || uncertain}><i className="fas fa-save me-1" /> {data.submit_text}</button></div>
                  </div>
                </div>
              </div>
            </div>
            {uncertain && <p role="alert">No se pudo confirmar el resultado. Revise el listado antes de reintentar.</p>}
          </form>
        </div>
      </div>
    </>
  );
}
