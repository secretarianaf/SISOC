import { createRoot } from "react-dom/client";
import App from "./App";
import { documentFor } from "./page";
import "./root.css";

const root = document.getElementById("root");
if (!root) throw new Error("Missing React root element.");

const { pathname } = window.location;
const page = documentFor(pathname);
document.title = page.title;
document.body.className = page.bodyClass;
createRoot(root).render(<App pathname={pathname} />);
