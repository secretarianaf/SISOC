import DdjjConfirmation from "./DdjjConfirmation";
import DdjjForm from "./DdjjForm";
import { CONFIRMATION_PATH, FORM_PATH } from "./page";

export default function App({ pathname }: { pathname: string }) {
  if (pathname === CONFIRMATION_PATH) return <DdjjConfirmation />;
  if (FORM_PATH.test(pathname)) return <DdjjForm pathname={pathname} />;
  return null;
}
