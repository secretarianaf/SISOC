import Select2, { type Choice } from "./select2";

/**
 * Técnicos selector of `dupla_form.html`: the markup of the native Select2 4.1
 * multiple (`duplas.js`: width 100%, placeholder, «Sin resultados»). The native
 * `<select multiple>` stays in the DOM and owns the form value; options come
 * from the server, never typed ids. Options of the shared `Select2`.
 */
export type { Choice };

export default function DuplasSelect2({ id, name, placeholder, choices, value, onChange, invalid, describedBy }: {
  id: string;
  name: string;
  placeholder: string;
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  invalid: boolean;
  describedBy: string;
}) {
  return <Select2 id={id} name={name} multiple placeholder={placeholder} selectClassName="form-control js-tecnico selectmultiple form-select" invalid={invalid}
    selectProps={{ "data-role": "select2", "data-placeholder": placeholder, "aria-label": placeholder, required: true, "aria-describedby": describedBy }}
    choices={choices} value={value} onChange={onChange} noResults="Sin resultados" focusMarker="none"
    termHandling="keep" enterOnSelected="close" removeOpensResults outsideClick="results" />;
}
