import { useEffect, useRef, useState } from "react";

// Existing Toastr defaults: 300 ms in, 5000 ms visible, 1000 ms out/extended.
// The markup/CSS stay legacy; React owns the single operation and its timers.
export default function InsumosToast({ message }: { message: string }) {
  const [phase, setPhase] = useState<"show" | "hiding" | "hidden">("show");
  const expiry = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const removal = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const hide = () => {
    clearTimeout(expiry.current);
    setPhase("hiding");
    clearTimeout(removal.current);
    removal.current = setTimeout(() => setPhase("hidden"), 1000);
  };
  useEffect(() => {
    expiry.current = setTimeout(() => {
      setPhase("hiding");
      removal.current = setTimeout(() => setPhase("hidden"), 1000);
    }, 5000);
    return () => { clearTimeout(expiry.current); clearTimeout(removal.current); };
  }, []);
  if (phase === "hidden") return null;
  return (
    <>
      <div id="toast-container" className="toast-bottom-right">
        <div
          className={`toast toast-success sisoc-operation-toast${phase === "hiding" ? " sisoc-toast-hiding" : ""}`}
          role="status"
          aria-live="polite"
          aria-atomic="true"
          onClick={hide}
          onMouseEnter={() => clearTimeout(expiry.current)}
          onMouseLeave={() => { if (phase === "show") expiry.current = setTimeout(hide, 1000); }}
        >
          <div className="toast-message">{message}</div>
        </div>
      </div>
    </>
  );
}
