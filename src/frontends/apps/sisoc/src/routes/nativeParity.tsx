/* eslint-disable react-refresh/only-export-components -- shared parity module: components plus the helpers and hooks that go with them. */
import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { InsumosToastList } from "../InsumosToast";

/**
 * Mechanics the React screens share to look like the native (Django) page:
 * toasts at the end of `<body>`, the Bootstrap modal rendered in place with its Tab trap,
 * and the reset a rejected POST implies (the native flow reloads the page).
 */

type Message = Parameters<typeof InsumosToastList>[0]["messages"][number];

/** Toastr appends its container to the end of `<body>`: the toasts go to the same place. */
export function NativeToasts({ messages }: { messages: Message[] }) {
  return createPortal(<InsumosToastList messages={messages} />, document.body);
}

/**
 * The native page reloaded after a rejected POST: the view starts at the top and keyboard focus
 * at the start of the document (a marker prepended to `<body>` takes the focus and goes away).
 */
export function resetAfterRejectedPost() {
  window.scrollTo(0, 0);
  const marker = document.createElement("span");
  marker.tabIndex = -1;
  document.body.prepend(marker);
  marker.focus({ preventScroll: true });
  marker.remove();
}

type ModalTrapOptions = {
  /** Focusable controls the Tab key cycles through. */
  controls?: string;
  /** While busy Escape does not close; a ref is read at key time, a boolean re-runs the effect. */
  busy?: boolean | RefObject<boolean>;
  /** `overflow: hidden` on `<body>` while open (restored on close). */
  lockScroll?: boolean;
};

/**
 * Bootstrap modal opened in place: `modal-open` on `<body>`, focus on the dialog, Tab and Shift+Tab
 * cycle between the first and last control, Escape closes (unless busy) and focus goes back to the
 * element that had it.
 */
export function useModalTabTrap(modal: RefObject<HTMLDivElement | null>, close: () => void,
  { controls = "button:not([disabled]),input:not([disabled])", busy = false, lockScroll = true }: ModalTrapOptions = {}) {
  const busyValue = typeof busy === "boolean" ? busy : undefined;
  const busyRef = typeof busy === "boolean" ? undefined : busy;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const before = document.body.style.overflow;
    document.body.classList.add("modal-open");
    if (lockScroll) document.body.style.overflow = "hidden";
    modal.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !(busyRef ? busyRef.current : busyValue)) close();
      if (e.key !== "Tab") return;
      const items = Array.from(modal.current?.querySelectorAll<HTMLElement>(controls) ?? []);
      const first = items[0], last = items.at(-1);
      if (e.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      document.body.classList.remove("modal-open");
      if (lockScroll) document.body.style.overflow = before;
      previous?.focus();
    };
  }, [modal, close, controls, busyRef, busyValue, lockScroll]);
}

/** The native `modal fade show` + backdrop, rendered where it is declared (not portaled) with the Tab trap. */
export function NativeModal({ id, title, close, busy = false, size = "", controls, children }: {
  id: string;
  title: string;
  close: () => void;
  busy?: boolean;
  /** Extra classes of `.modal-dialog`, with a leading space (` modal-lg`). */
  size?: string;
  controls?: string;
  children: ReactNode;
}) {
  const modal = useRef<HTMLDivElement>(null);
  useModalTabTrap(modal, close, { busy, lockScroll: false, controls });
  return (
    <>
      <div className="modal-backdrop fade show" />
      <div ref={modal} className="modal fade show d-block" id={id} tabIndex={-1} role="dialog" aria-modal="true"
        aria-labelledby={`${id}-label`} onClick={(e) => { if (e.target === e.currentTarget && !busy) close(); }}>
        <div className={`modal-dialog${size}`}>{children}<span hidden id={`${id}-label`}>{title}</span></div>
      </div>
    </>
  );
}
