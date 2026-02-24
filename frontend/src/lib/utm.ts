/**
 * UTM parameter capture and storage utilities.
 *
 * Flow:
 * 1. Page loads → captureUtmParams() reads from URL and stores in sessionStorage
 * 2. getStoredUtm() retrieves stored params for form submissions
 * 3. getOrCreateSessionId() provides a consistent session ID for visit/lead linking
 */

const UTM_STORAGE_KEY = "gor_utm";
const SESSION_KEY = "gor_session";

export interface UtmParams {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
  utm_term?: string;
}

const UTM_KEYS: (keyof UtmParams)[] = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
];

/**
 * Read UTM params from the current URL and store in sessionStorage.
 * Only overwrites if UTM params are present in the URL.
 */
export function captureUtmParams(): UtmParams {
  if (typeof window === "undefined") return {};

  const searchParams = new URLSearchParams(window.location.search);
  const params: UtmParams = {};
  let hasUtm = false;

  for (const key of UTM_KEYS) {
    const value = searchParams.get(key);
    if (value) {
      params[key] = value;
      hasUtm = true;
    }
  }

  if (hasUtm) {
    sessionStorage.setItem(UTM_STORAGE_KEY, JSON.stringify(params));
  }

  return hasUtm ? params : getStoredUtm();
}

/**
 * Get previously stored UTM params from sessionStorage.
 */
export function getStoredUtm(): UtmParams {
  if (typeof window === "undefined") return {};

  try {
    const stored = sessionStorage.getItem(UTM_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as UtmParams;
    }
  } catch {
    // Ignore parse errors
  }
  return {};
}

/**
 * Get or create a session ID for linking visits to leads.
 */
export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";

  let sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}
