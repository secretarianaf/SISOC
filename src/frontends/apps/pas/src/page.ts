export const CONFIRMATION_PATH = "/pas/ddjj/confirmacion";
export const FORM_PATH = /^\/pas\/ddjj\/formulario\/[0-9a-f-]{36}$/;

/** Document title and body class of each native template. */
export function documentFor(pathname: string) {
  return pathname === CONFIRMATION_PATH
    ? {
        title: "Declaración Jurada enviada · SISOC",
        bodyClass: "pas-ddjj-public pas-ddjj-success-page",
      }
    : { title: "Declaración Jurada PAS", bodyClass: "pas-ddjj-public" };
}
