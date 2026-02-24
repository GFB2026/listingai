import axios from "axios";
import { env } from "./env";

/**
 * Axios instance for public (unauthenticated) API calls.
 * No cookies, no CSRF, no auth interceptors.
 */
const publicApi = axios.create({
  baseURL: `${env.NEXT_PUBLIC_API_URL}/api/v1/public`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15_000,
});

export default publicApi;
