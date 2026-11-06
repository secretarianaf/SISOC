import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ANSWER_FIELDS,
  FIELD_STEP,
  answersAfterServerError,
  loadDeclaration,
  submitDeclaration,
  submittedValue,
  type AnswerField,
  type DdjjPayload,
  type Option,
  type TextField,
} from "./ddjj";
import { navigateTo, replaceWith } from "./navigation";

const TOTAL_STEPS = 5;
const LEGAL_TEXT =
  "El suscripto declara conocer que la falsedad u omisión de la información consignada precedentemente podrá dar lugar a la suspensión y/o egreso, sin perjuicio de las acciones administrativas y/o judiciales que pudieran corresponder. Asimismo, declara que los datos de contacto consignados en la presente Declaración Jurada son veraces y se encuentran vigentes, y presta expresa conformidad para que todas las notificaciones, comunicaciones, requerimientos, intimaciones y demás actos vinculados con mi participación en el Programa sean cursados a través de dichos medios, considerándose válidas y plenamente eficaces desde su remisión. La presente DECLARACIÓN JURADA tendrá tal carácter y se formula en cumplimiento de las corresponsabilidades e incompatibilidades exigidas por la normativa vigente, aplicable al Programa de Acompañamiento Social (PAS).";
const SUMMARY_ANSWERS: [AnswerField, string][] = [
  ["embarazada", "Embarazo"],
  ["controles_embarazo_cumplidos", "Controles de embarazo"],
  ["hijos_menores_a_cargo", "Menores de 18 años a cargo"],
  ["vacunacion_cumplida", "Plan Nacional de Vacunación"],
  ["regularidad_escolar_acreditada", "Regularidad escolar"],
  ["gastos_bajo_limite_smvm", "Gastos sobre 1 SMVM"],
  ["no_accedio_mercado_cambios", "Compra de divisas"],
];
const REQUIRED_ANSWERS = new Set<AnswerField>([
  "embarazada",
  "hijos_menores_a_cargo",
  "gastos_bajo_limite_smvm",
  "no_accedio_mercado_cambios",
]);

type Texts = Record<TextField, string>;
type Answers = Record<AnswerField, string>;
type MunicipalityList = { placeholder: string; options: Option[] };

function ErrorList({ id, messages }: { id: string; messages?: string[] }) {
  if (!messages?.length) return null;
  return (
    <ul className="errorlist" id={id}>
      {messages.map((message) => (
        <li key={message}>{message}</li>
      ))}
    </ul>
  );
}

export default function DdjjForm({ pathname }: { pathname: string }) {
  const [payload, setPayload] = useState<DdjjPayload | null>(null);
  const [texts, setTexts] = useState<Texts | null>(null);
  const [answers, setAnswers] = useState<Answers | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [municipalities, setMunicipalities] = useState<MunicipalityList | null>(null);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [current, setCurrent] = useState(0);
  const [legalOpen, setLegalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [scrollTick, setScrollTick] = useState(0);
  // "smooth" mirrors show() between steps; "instant" mirrors the fresh page after a 400.
  const scrollOnShow = useRef<ScrollBehavior | null>(null);
  const submitting = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);
  const stepRefs = useRef<(HTMLElement | null)[]>([]);
  const legalRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLDivElement>(null);

  const apply = (data: DdjjPayload, restoreAfterError: boolean) => {
    setPayload(data);
    setTexts(
      Object.fromEntries(
        (Object.keys(data.existing) as TextField[]).map((f) => [f, data.values[f]]),
      ) as Texts,
    );
    setAnswers(
      restoreAfterError
        ? answersAfterServerError(data.values)
        : (Object.fromEntries(ANSWER_FIELDS.map((f) => [f, data.values[f]])) as Answers),
    );
    setAccepted(data.values.acepto_declaracion);
    setMunicipalities({ placeholder: data.empty_label, options: data.municipalities });
    const errorMap = data.errors ?? {};
    setErrors(errorMap);
    const steps = Object.keys(errorMap)
      .map((field) => FIELD_STEP[field])
      .filter((step) => step !== undefined);
    scrollOnShow.current = restoreAfterError ? "instant" : null;
    setCurrent(steps.length ? Math.min(...steps) : 0);
    if (restoreAfterError) setScrollTick((tick) => tick + 1);
  };

  useEffect(() => {
    let active = true;
    void loadDeclaration(`${pathname}/datos`).then((result) => {
      if (!active) return;
      if (result === "reload") replaceWith(pathname);
      else if (result !== "error") apply(result, false);
    });
    return () => {
      active = false;
    };
  }, [pathname]);

  useEffect(() => {
    const behavior = scrollOnShow.current;
    if (!behavior) return;
    scrollOnShow.current = null;
    document.querySelector(".pas-ddjj-shell")?.scrollTo?.({ top: 0, behavior });
    window.scrollTo?.({ top: 0, behavior });
  }, [current, scrollTick]);

  useEffect(() => {
    if (legalOpen) legalRef.current?.querySelector("button")?.focus();
  }, [legalOpen]);
  useEffect(() => {
    if (confirmOpen) confirmRef.current?.querySelector("button")?.focus();
  }, [confirmOpen]);

  if (!payload || !texts || !answers || !municipalities) return null;

  const pregnancy = answers.embarazada === "si";
  const children = answers.hijos_menores_a_cargo === "si";
  const disabledAnswer = (field: AnswerField) =>
    (!pregnancy && field === "controles_embarazo_cumplidos") ||
    (!children &&
      (field === "vacunacion_cumplida" || field === "regularidad_escolar_acreditada"));

  const goTo = (step: number) => {
    scrollOnShow.current = "smooth";
    setCurrent(step);
  };

  /** Same per-step browser validation as pas_ddjj.js `validate()`. */
  const validate = () => {
    const step = stepRefs.current[current];
    if (!step) return false;
    const controls = [
      ...step.querySelectorAll<HTMLInputElement | HTMLSelectElement>("input,select"),
    ].filter((el) => !el.disabled);
    const radioNames = [
      ...new Set(controls.filter((el) => el.type === "radio").map((el) => el.name)),
    ];
    for (const name of radioNames) {
      const group = controls.filter((el) => el.name === name) as HTMLInputElement[];
      if (!group.some((el) => el.checked)) {
        group[0].setCustomValidity("Elegí una respuesta para continuar.");
        group[0].reportValidity();
        group[0].setCustomValidity("");
        return false;
      }
    }
    return controls.every((el) => el.reportValidity());
  };

  const changeProvince = async (value: string) => {
    setTexts((prev) => ({ ...prev!, provincia: value, municipio: "" }));
    setMunicipalities({ placeholder: "Cargando municipios...", options: [] });
    const url = new URL(payload.urls.municipalities, window.location.origin);
    url.searchParams.set("provincia_id", value);
    try {
      const response = await fetch(url);
      const items = (await response.json()) as { id: number; nombre: string }[];
      if (!Array.isArray(items)) throw new TypeError("items.forEach is not a function");
      setMunicipalities({
        placeholder: "Seleccioná un municipio",
        options: items.map(({ id, nombre }) => ({ id: String(id), label: nombre })),
      });
    } catch {
      setMunicipalities({ placeholder: "No se pudieron cargar los municipios", options: [] });
    }
  };

  const send = async () => {
    setConfirmOpen(false);
    if (submitting.current || !formRef.current) return;
    submitting.current = true;
    const body = new URLSearchParams();
    for (const [key, value] of new FormData(formRef.current)) body.append(key, String(value));
    const outcome = await submitDeclaration(payload.urls.submit, body);
    if (outcome.kind === "confirmed") {
      navigateTo(outcome.redirect);
      return;
    }
    if (outcome.kind === "invalid") {
      submitting.current = false;
      setLegalOpen(false);
      apply(outcome.payload, true);
      return;
    }
    navigateTo(pathname);
  };

  const fieldError = (field: string) => errors[field];
  const errorAttrs = (field: string, describedBy = true) =>
    fieldError(field)
      ? {
          "aria-invalid": true as const,
          ...(describedBy ? { "aria-describedby": `id_${field}_error` } : {}),
        }
      : {};

  const textInput = (
    field: Exclude<TextField, "provincia" | "municipio">,
    props: { type: string; placeholder: string; maxLength: number; inputMode?: "tel" },
  ) => (
    <input
      type={props.type}
      name={field}
      value={texts[field]}
      className="form-control"
      {...(props.inputMode ? { inputMode: props.inputMode } : {})}
      placeholder={props.placeholder}
      maxLength={props.maxLength}
      data-pas-existente={payload.existing[field] ? "true" : "false"}
      {...errorAttrs(field)}
      id={`id_${field}`}
      onChange={(event) => {
        const value = event.target.value;
        setTexts((prev) => ({ ...prev!, [field]: value }));
      }}
    />
  );

  const select = (field: "provincia" | "municipio", list: MunicipalityList) => (
    <select
      name={field}
      className="form-select"
      data-pas-existente={payload.existing[field] ? "true" : "false"}
      {...errorAttrs(field)}
      id={`id_${field}`}
      value={texts[field]}
      onChange={(event) => {
        const value = event.target.value;
        if (field === "provincia") void changeProvince(value);
        else setTexts((prev) => ({ ...prev!, municipio: value }));
      }}
    >
      <option value="">{list.placeholder}</option>
      {list.options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.label}
        </option>
      ))}
    </select>
  );

  const field = (name: TextField, label: string, control: ReactNode) => (
    <div className="pas-ddjj-field">
      <label htmlFor={`id_${name}`}>{label}</label>
      <div className="pas-ddjj-control">{control}</div>
      <ErrorList id={`id_${name}_error`} messages={fieldError(name)} />
    </div>
  );

  const radios = (name: AnswerField) => {
    const inverted = submittedValue(name, "si") === "no";
    return (
      <div className={`pas-ddjj-options${inverted ? " pas-ddjj-options-inverted" : ""}`}>
        <div id={`id_${name}`}>
          {(["si", "no"] as const).map((visible, index) => {
            const value = submittedValue(name, visible);
            return (
              <div key={visible}>
                <label htmlFor={`id_${name}_${index}`}>
                  <input
                    type="radio"
                    name={name}
                    value={value}
                    required={REQUIRED_ANSWERS.has(name)}
                    {...errorAttrs(name, false)}
                    id={`id_${name}_${index}`}
                    checked={answers[name] === value}
                    disabled={disabledAnswer(name)}
                    onChange={() => setAnswers((prev) => ({ ...prev!, [name]: value }))}
                  />
                  {visible === "si" ? "\n Sí" : "\n No"}
                </label>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const question = (name: AnswerField, title: ReactNode, extra?: ReactNode, className = "") => (
    <div className={`pas-ddjj-question${className}`}>
      <h3>{title}</h3>
      {extra}
      {radios(name)}
      <ErrorList id={`id_${name}_error`} messages={fieldError(name)} />
    </div>
  );

  const stepStyle = (index: number) => ({ display: index === current ? "block" : "none" });
  const stepRef = (index: number) => (element: HTMLElement | null) => {
    stepRefs.current[index] = element;
  };
  const index = current + 1;

  const optionLabel = (list: Option[], placeholder: string, value: string) =>
    value === "" ? placeholder : (list.find((option) => option.id === value)?.label ?? "");
  const summary: [string, string][] = [
    ["Domicilio", [texts.calle, texts.altura].filter(Boolean).join(" ")],
    ["Provincia", optionLabel(payload.provinces, payload.empty_label, texts.provincia)],
    [
      "Municipio",
      optionLabel(municipalities.options, municipalities.placeholder, texts.municipio),
    ],
    ...SUMMARY_ANSWERS.filter(([name]) => answers[name] && !disabledAnswer(name)).map(
      ([name, label]): [string, string] => [
        label,
        submittedValue(name, "si") === answers[name] ? "Sí" : "No",
      ],
    ),
  ];

  return (
    <>
      <header className="pas-ddjj-public-brand">
        <div className="pas-ddjj-logo">
          <img
            className="pas-ddjj-logo-mark"
            src="/static/custom/img/formando_capital_humano_marca.png"
            alt=""
          />
          <span>
            FORMANDO <strong>CAPITAL HUMANO</strong>
          </span>
        </div>
        <span>Mesa de ayuda</span>
      </header>
      <main className="pas-ddjj-shell">
        <h1>Declaración Jurada</h1>
        <div className="pas-ddjj-card">
          <header className="pas-ddjj-header">
            <div className="pas-ddjj-progress-copy">
              <strong id="ddjj-progress-text">{`Paso ${index} de ${TOTAL_STEPS}`}</strong>
              <strong id="ddjj-progress-percent">{`${Math.round((index / TOTAL_STEPS) * 100)}%`}</strong>
            </div>
            <div className="pas-ddjj-progress">
              {Array.from({ length: TOTAL_STEPS }, (_, segment) => (
                <span
                  key={segment}
                  className={
                    segment < index - 1 ? "is-complete" : segment === index - 1 ? "is-current" : undefined
                  }
                />
              ))}
            </div>
          </header>
          <form
            method="post"
            id="pas-ddjj-form"
            data-data-step=""
            data-municipios-url={payload.urls.municipalities}
            noValidate
            ref={formRef}
            onSubmit={(event) => event.preventDefault()}
          >
            <input type="hidden" name="datos_mi_argentina_confirmados" value="no" />
            {errors.__all__?.length ? (
              <div className="pas-ddjj-errors">
                <ul className="errorlist nonfield">
                  {errors.__all__.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <section className="pas-ddjj-step" data-step-index="1" style={stepStyle(0)} ref={stepRef(0)}>
              <h2>Tus datos de contacto</h2>
              <p className="pas-ddjj-help">Revisá que esta información esté al día</p>
              <aside className="pas-ddjj-notice">
                Es importante mantener estos datos actualizados: revisalos cada 6 meses para
                mantenerte activo en el Programa y evitar la suspensión.
              </aside>
              <div className="pas-ddjj-fields-grid">
                {field(
                  "calle",
                  payload.labels.calle,
                  textInput("calle", { type: "text", placeholder: "Calle", maxLength: 255 }),
                )}
                {field(
                  "altura",
                  "Número",
                  textInput("altura", { type: "text", placeholder: "Número o S/N", maxLength: 10 }),
                )}
                {field(
                  "provincia",
                  payload.labels.provincia,
                  select("provincia", { placeholder: payload.empty_label, options: payload.provinces }),
                )}
                {field("municipio", payload.labels.municipio, select("municipio", municipalities))}
                {field(
                  "correo_electronico",
                  payload.labels.correo_electronico,
                  textInput("correo_electronico", {
                    type: "email",
                    placeholder: "nombre@correo.com",
                    maxLength: 320,
                  }),
                )}
                {field(
                  "telefono_celular",
                  payload.labels.telefono_celular,
                  textInput("telefono_celular", {
                    type: "text",
                    inputMode: "tel",
                    placeholder: "11 66 435632",
                    maxLength: 30,
                  }),
                )}
              </div>
            </section>
            <section className="pas-ddjj-step" data-step-index="2" style={stepStyle(1)} ref={stepRef(1)}>
              <p className="pas-ddjj-eyebrow">Antes de continuar</p>
              <h2>Tu situación</h2>
              <p className="pas-ddjj-help">
                Estas preguntas nos permiten adaptar el formulario: solo vamos a pedirte la
                información que corresponda a tu situación.
              </p>
              {question("embarazada", payload.labels.embarazada)}
              <div className="pas-ddjj-conditional" data-condition="embarazada" hidden={!pregnancy}>
                {question(
                  "controles_embarazo_cumplidos",
                  "¿Diste cumplimiento a los controles de salud correspondientes a tu embarazo?",
                )}
              </div>
            </section>
            <section className="pas-ddjj-step" data-step-index="3" style={stepStyle(2)} ref={stepRef(2)}>
              <p className="pas-ddjj-eyebrow">Controles de salud y escolaridad</p>
              <h2>Menores de 18 años a cargo</h2>
              {question("hijos_menores_a_cargo", "¿Tenés menores de 18 años a cargo?")}
              <div
                className="pas-ddjj-conditional"
                data-condition="hijos_menores_a_cargo"
                hidden={!children}
              >
                {question(
                  "vacunacion_cumplida",
                  "¿Diste cumplimiento al Plan Nacional de Vacunación respecto de los menores a cargo?",
                )}
                {question(
                  "regularidad_escolar_acreditada",
                  "¿Acreditaste la regularidad escolar de los menores a cargo?",
                )}
              </div>
            </section>
            <section className="pas-ddjj-step" data-step-index="4" style={stepStyle(3)} ref={stepRef(3)}>
              <p className="pas-ddjj-eyebrow">Gastos y consumos</p>
              <h2>Tarjetas y compra de divisas</h2>
              {question(
                "gastos_bajo_limite_smvm",
                "En los últimos 6 meses, ¿tus gastos con tarjeta de crédito, débito o billetera virtual superaron en promedio mensual un Salario Mínimo Vital y Móvil?",
                <aside className="pas-ddjj-notice">
                  El Salario Mínimo Vital y Móvil (SMVM) es un monto que fija el Estado y se
                  actualiza periódicamente. Consultá el valor vigente.
                </aside>,
              )}
              {question(
                "no_accedio_mercado_cambios",
                "¿Accediste al Mercado de Cambios para la compra de divisas con fines de ahorro?",
                undefined,
                " pas-ddjj-market-question",
              )}
            </section>
            <section className="pas-ddjj-step" data-step-index="5" style={stepStyle(4)} ref={stepRef(4)}>
              <p className="pas-ddjj-eyebrow">Último paso</p>
              <h2>Resumen de tu declaración</h2>
              <p className="pas-ddjj-help">Esto es lo que vas a declarar bajo juramento.</p>
              <div id="ddjj-summary" className="pas-ddjj-summary">
                {current === 4
                  ? summary.map(([label, value]) => (
                      <div key={label}>
                        <strong>{label}</strong>
                        <span>{value}</span>
                      </div>
                    ))
                  : null}
              </div>
              <label className="pas-ddjj-accept pas-ddjj-contact-accept">
                <input
                  type="checkbox"
                  name="acepto_declaracion"
                  required
                  {...errorAttrs("acepto_declaracion")}
                  id="id_acepto_declaracion"
                  checked={accepted}
                  onChange={(event) => setAccepted(event.target.checked)}
                />{" "}
                <span>{payload.labels.acepto_declaracion}</span>
              </label>
              <ErrorList id="id_acepto_declaracion_error" messages={fieldError("acepto_declaracion")} />
              <button
                type="button"
                className="pas-ddjj-legal-link"
                id="ddjj-legal-open"
                onClick={() => setLegalOpen(true)}
              >
                Ver términos legales
              </button>
            </section>
            <footer className="pas-ddjj-actions">
              <button
                type="button"
                className="pas-ddjj-button is-secondary"
                id="ddjj-back"
                hidden={current === 0}
                onClick={() => goTo(Math.max(0, current - 1))}
              >
                Atrás
              </button>
              <button
                type="button"
                className="pas-ddjj-button"
                id="ddjj-next"
                hidden={index === TOTAL_STEPS}
                onClick={() => {
                  if (validate()) goTo(current + 1);
                }}
              >
                {index === 1 ? "Confirmar y continuar" : "Continuar"}
              </button>
              <button
                type="button"
                className="pas-ddjj-button"
                id="ddjj-submit"
                hidden={index !== TOTAL_STEPS}
                onClick={() => {
                  if (validate()) setConfirmOpen(true);
                }}
              >
                Confirmar
              </button>
            </footer>
          </form>
        </div>
      </main>
      <footer className="pas-ddjj-footer">
        SiSoc Conecta - Mesa de ayuda de Formando Capital Humano
      </footer>
      <div
        className="pas-ddjj-modal"
        id="ddjj-legal-modal"
        hidden={!legalOpen}
        role="dialog"
        aria-modal="true"
        ref={legalRef}
      >
        <div className="pas-ddjj-modal-card is-legal">
          <button
            type="button"
            className="pas-ddjj-modal-close"
            data-modal-close=""
            aria-label="Cerrar"
            onClick={() => setLegalOpen(false)}
          >
            ×
          </button>
          <h2>Términos Legales</h2>
          <p>{LEGAL_TEXT}</p>
        </div>
      </div>
      <div
        className="pas-ddjj-modal"
        id="ddjj-confirm-modal"
        hidden={!confirmOpen}
        role="dialog"
        aria-modal="true"
        ref={confirmRef}
      >
        <div className="pas-ddjj-modal-card is-warning">
          <span className="pas-ddjj-info-icon">i</span>
          <h2>¡Atención!</h2>
          <strong>¿Confirmás el envío de la declaración jurada?</strong>
          <p>
            Al confirmar, estás declarando bajo juramento que los datos ingresados son verídicos,
            exactos y completos. Una vez enviada, la información no podrá ser modificada de forma
            directa.
          </p>
          <div className="pas-ddjj-modal-actions">
            <button
              type="button"
              className="pas-ddjj-button is-secondary"
              data-modal-close=""
              onClick={() => setConfirmOpen(false)}
            >
              Atrás
            </button>
            <button
              type="button"
              className="pas-ddjj-button"
              id="ddjj-confirm-send"
              onClick={() => void send()}
            >
              Confirmar y enviar
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
