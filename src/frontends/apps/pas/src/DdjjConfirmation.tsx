/** Generic confirmation: no declaration identifier, counter or automatic redirect. */
export default function DdjjConfirmation() {
  return (
    <main className="pas-ddjj-modal-card is-success">
      <span className="pas-ddjj-success-icon" aria-hidden="true">
        ✓
      </span>
      <div>
        <h1>Declaración Jurada enviada con éxito</h1>
        <p>
          Guardamos tu DDJJ con fecha y hora. Te vamos a avisar por correo si necesitamos algo
          más.
        </p>
      </div>
      <button className="pas-ddjj-button" type="button">
        OK
      </button>
    </main>
  );
}
