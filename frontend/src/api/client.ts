import createClient from "openapi-fetch";
import type { paths } from "./schema";

// The whole frontend talks to the backend only through this client (typed from openapi/account.yaml).
export const api = createClient<paths>({ baseUrl: "/api/v1" });