import { useRef, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { NativeModal, NativeToasts, resetAfterRejectedPost, useModalTabTrap } from "./nativeParity";

afterEach(() => { cleanup(); document.body.className = ""; document.body.removeAttribute("style"); });

describe("NativeToasts", () => {
  it("renders the toasts at the end of <body>, outside the screen container", () => {
    const { container } = render(<div><NativeToasts messages={[{ message: "Guardado", level: "success" }]} /></div>);
    const toast = screen.getByText("Guardado");
    expect(container.contains(toast)).toBe(false);
    expect(document.body.lastElementChild?.contains(toast)).toBe(true);
  });
});

describe("resetAfterRejectedPost", () => {
  it("scrolls to the top and leaves nothing focused, with no marker left behind", () => {
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    render(<button>uno</button>);
    screen.getByText("uno").focus();
    const before = document.body.children.length;
    resetAfterRejectedPost();
    expect(scroll).toHaveBeenCalledWith(0, 0);
    expect(document.activeElement).toBe(document.body);
    expect(document.body.children.length).toBe(before);
    scroll.mockRestore();
  });
});

function Trap({ close, busy }: { close: () => void; busy?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useModalTabTrap(ref, close, { busy });
  return <div ref={ref} tabIndex={-1} data-testid="dialog"><button>primero</button><button>ultimo</button></div>;
}

describe("useModalTabTrap", () => {
  it("focuses the dialog, cycles Tab inside, closes on Escape and restores the body and the focus", () => {
    const close = vi.fn();
    const outside = document.createElement("button");
    document.body.append(outside);
    outside.focus();
    const view = render(<Trap close={close} />);
    expect(document.body.classList.contains("modal-open")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.activeElement).toBe(screen.getByTestId("dialog"));
    screen.getByText("ultimo").focus();
    const forward = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    document.dispatchEvent(forward);
    expect(forward.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(screen.getByText("primero"));
    const backward = new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true, cancelable: true });
    document.dispatchEvent(backward);
    expect(document.activeElement).toBe(screen.getByText("ultimo"));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(close).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(document.body.classList.contains("modal-open")).toBe(false);
    expect(document.body.style.overflow).toBe("");
    expect(document.activeElement).toBe(outside);
    outside.remove();
  });

  it("does not close on Escape while busy", () => {
    const close = vi.fn();
    render(<Trap close={close} busy />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(close).not.toHaveBeenCalled();
  });
});

describe("NativeModal", () => {
  it("renders the backdrop and the dialog in place and closes on a backdrop click unless busy", () => {
    const close = vi.fn();
    function Screen({ busy }: { busy: boolean }) {
      const [n] = useState(0);
      return <section data-testid="host">{n}<NativeModal id="m" title="Titulo" close={close} busy={busy} size=" modal-lg"><div className="modal-content"><button>ok</button></div></NativeModal></section>;
    }
    const view = render(<Screen busy={false} />);
    const dialog = view.container.querySelector("#m") as HTMLElement;
    expect(screen.getByTestId("host").contains(dialog)).toBe(true);
    expect(dialog.className).toBe("modal fade show d-block");
    expect(dialog.getAttribute("aria-labelledby")).toBe("m-label");
    expect(dialog.querySelector(".modal-dialog")?.className).toBe("modal-dialog modal-lg");
    expect(view.container.querySelector(".modal-backdrop.fade.show")).not.toBeNull();
    expect(document.body.style.overflow).toBe("");
    fireEvent.click(screen.getByText("ok"));
    expect(close).not.toHaveBeenCalled();
    fireEvent.click(dialog);
    expect(close).toHaveBeenCalledTimes(1);
    view.rerender(<Screen busy />);
    fireEvent.click(view.container.querySelector("#m")!);
    expect(close).toHaveBeenCalledTimes(1);
  });
});
