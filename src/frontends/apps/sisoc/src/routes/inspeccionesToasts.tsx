import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/**
 * Django messages as `includes/scripts/toastr_messages.html` shows them on the
 * light layout: toastr defaults (bottom right, 5000 ms visible, 1000 ms after
 * hover, 1000 ms fade out, click closes). The light frame does not load the
 * app stylesheet, so the toast carries toastr's own inline `display: block`.
 * Like toastr, the container is the last child of `<body>`.
 */
export type InspMessage = { message: string; level: "success" | "error" | "warning" | "info" };

function Toast({ message, level }: InspMessage) {
  const [phase, setPhase] = useState<"show" | "hiding" | "hidden">("show");
  const expiry = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const removal = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const hide = () => {
    clearTimeout(expiry.current);
    clearTimeout(removal.current);
    setPhase("hiding");
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
    <div
      className={`toast toast-${level}`}
      aria-live={level === "success" || level === "info" ? "polite" : "assertive"}
      style={phase === "hiding" ? { display: "block", opacity: 0, transition: "opacity 1000ms" } : { display: "block" }}
      onClick={hide}
      onMouseEnter={() => { if (phase === "show") clearTimeout(expiry.current); }}
      onMouseLeave={() => { if (phase === "show") expiry.current = setTimeout(hide, 1000); }}
    >
      <div className="toast-message">{message}</div>
    </div>
  );
}

export default function InspToasts({ messages }: { messages: InspMessage[] }) {
  if (!messages.length) return null;
  // toastr's `newestOnTop`: the last queued message is the first one.
  return createPortal(
    <div id="toast-container" className="toast-bottom-right">
      {[...messages].reverse().map((message, index) => <Toast key={index} {...message} />)}
    </div>,
    document.body,
  );
}
