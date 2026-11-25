/** The API client base is `/api`: the `urls.cursos` of the payload (`/api/web/...`) is made relative before it is requested. */
export const cursosPanelEndpoint = (url: string) => url.replace(/^\/api\//, "");
/** Same rule for every `/api/web/...` URL of the payload (forms, saves and deletes of the page actions). */
export const apiPath = cursosPanelEndpoint;
