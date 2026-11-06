import { findRoute } from "./routes";
import "./shell.css";

// Public identity paths own their API bootstrap; every other path keeps the business shell.
export default function App() {
  const found = findRoute(window.location.pathname);
  return found ? found.route.render(found.params) : null;
}
