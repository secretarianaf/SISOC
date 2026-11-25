import Select2, { type Choice } from "./select2";

/**
 * The two selects of the state-change modal as `pas.js` builds them with
 * Select2 4.1.0-beta.1: `width: "100%"`, `allowClear`, `minimumResultsForSearch: 0`,
 * placeholder «Seleccione una opcion» (single) or «Seleccione avisos» (multiple)
 * and `dropdownParent` = the modal. Options of the shared `Select2`.
 */
export type { Choice };

export default function PasSelect2({ id, name, multiple = false, choices, value, onChange, parent, invalid = false }: {
  id: string;
  name: string;
  multiple?: boolean;
  /** Single: the first choice is the empty option (Select2 shows the placeholder for it). */
  choices: Choice[];
  value: string[];
  onChange: (value: string[]) => void;
  /** `dropdownParent`: the dropdown is placed inside this element. */
  parent: HTMLElement | null;
  /** Server-side rejection of the field (`is-invalid` on the native select). */
  invalid?: boolean;
}) {
  return <Select2 id={id} name={name} multiple={multiple} placeholder={multiple ? "Seleccione avisos" : "Seleccione una opcion"}
    selectClassName={`form-select pas-select2${multiple ? " selectmultiple" : ""}`} selectProps={{ required: true }}
    choices={multiple ? choices.filter((c) => c.value !== "") : choices} hideEmptyChoice value={value} onChange={onChange} noResults="No results found" invalid={invalid}
    dropdownParent={parent} clearTrigger="mousedown" focusMarker="container" termHandling="reset" enterOnSelected="toggle" outsideClick="dropdown" />;
}
