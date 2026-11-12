import Select2, { type Choice } from "./select2";

/**
 * The `select.select2` of `relevamiento_form.html` as `custom.js`
 * (`initSelect2Elements`) builds them with Select2 4.1.0-beta.1: `width: 100%`,
 * the empty option's text as placeholder with `allowClear` on single selects,
 * no placeholder on multiple ones, default English texts and the dropdown on
 * `<body>`. Options of the shared `Select2`.
 */
export type { Choice };

export default function DatacalleSelect2({ id, name, className, multiple = false, choices, value, onChange, disabled = false, required = false, invalid = false, describedBy }: {
  id: string;
  name: string;
  /** Classes of the hidden native select (crispy: `select2 form-select`, `select2 selectmultiple form-select`). */
  className: string;
  multiple?: boolean;
  /** Single: the first choice with an empty value gives the placeholder (`buildSelect2Options`). */
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
}) {
  const placeholder = multiple ? undefined : choices.find((c) => c.value === "")?.label;
  return <Select2 id={id} name={name} multiple={multiple} placeholder={placeholder} selectClassName={className} invalid={invalid} disabled={disabled}
    selectProps={{ required: required || undefined, "aria-describedby": describedBy }}
    choices={choices} hideEmptyChoice={placeholder !== undefined} value={value} onChange={onChange} noResults="No results found"
    clearTrigger={!multiple && placeholder !== undefined ? "mousedown" : "none"} focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />;
}
