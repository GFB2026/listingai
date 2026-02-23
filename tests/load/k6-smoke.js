/**
 * k6 load test — smoke / soak profiles for ListingAI.
 *
 * Usage:
 *   k6 run tests/load/k6-smoke.js                        # smoke (5 VUs, 1 min)
 *   k6 run -e PROFILE=load tests/load/k6-smoke.js        # load  (50 VUs ramp)
 *   k6 run -e PROFILE=stress tests/load/k6-smoke.js      # stress (100 VUs ramp)
 *
 * Environment variables:
 *   BASE_URL   — backend URL (default: http://localhost:8000)
 *   PROFILE    — smoke | load | stress (default: smoke)
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------- Custom metrics ----------
const errorRate = new Rate("errors");
const loginDuration = new Trend("login_duration", true);
const listingsDuration = new Trend("listings_duration", true);

// ---------- Configuration ----------
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const PROFILE = __ENV.PROFILE || "smoke";

const profiles = {
  smoke: {
    stages: [{ duration: "1m", target: 5 }],
    thresholds: {
      http_req_duration: ["p(95)<2000"],
      errors: ["rate<0.05"],
    },
  },
  load: {
    stages: [
      { duration: "2m", target: 20 },
      { duration: "5m", target: 50 },
      { duration: "2m", target: 0 },
    ],
    thresholds: {
      http_req_duration: ["p(95)<3000"],
      errors: ["rate<0.05"],
    },
  },
  stress: {
    stages: [
      { duration: "2m", target: 50 },
      { duration: "5m", target: 100 },
      { duration: "3m", target: 100 },
      { duration: "2m", target: 0 },
    ],
    thresholds: {
      http_req_duration: ["p(99)<5000"],
      errors: ["rate<0.10"],
    },
  },
};

const profile = profiles[PROFILE] || profiles.smoke;

export const options = {
  stages: profile.stages,
  thresholds: profile.thresholds,
};

// ---------- Helpers ----------
const headers = { "Content-Type": "application/json" };

function uniqueEmail() {
  return `loadtest+${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

// ---------- Scenarios ----------
export default function () {
  let accessToken = null;

  group("Health check", () => {
    const res = http.get(`${BASE_URL}/health/ready`);
    check(res, {
      "health 200": (r) => r.status === 200,
      "health has checks": (r) => r.json("status") !== undefined || r.json("checks") !== undefined,
    }) || errorRate.add(1);
  });

  group("Register", () => {
    const email = uniqueEmail();
    const payload = JSON.stringify({
      email: email,
      password: "K6Load@test1",
      full_name: "Load Test User",
      brokerage_name: `LoadTest ${Date.now()}`,
    });

    const res = http.post(`${BASE_URL}/api/v1/auth/register`, payload, { headers });
    const ok = check(res, {
      "register 201": (r) => r.status === 201,
      "register has token": (r) => {
        try {
          return r.json("access_token") !== undefined;
        } catch {
          return false;
        }
      },
    });
    if (!ok) {
      errorRate.add(1);
      return;
    }

    try {
      accessToken = res.json("access_token");
    } catch {
      errorRate.add(1);
      return;
    }
  });

  if (!accessToken) {
    sleep(1);
    return;
  }

  const authHeaders = {
    ...headers,
    Authorization: `Bearer ${accessToken}`,
  };

  group("Get current user", () => {
    const res = http.get(`${BASE_URL}/api/v1/auth/me`, { headers: authHeaders });
    check(res, {
      "me 200": (r) => r.status === 200,
      "me has email": (r) => {
        try {
          return r.json("email") !== undefined;
        } catch {
          return false;
        }
      },
    }) || errorRate.add(1);
  });

  group("List listings", () => {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/listings`, { headers: authHeaders });
    listingsDuration.add(Date.now() - start);
    check(res, {
      "listings 200": (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  group("List content", () => {
    const res = http.get(`${BASE_URL}/api/v1/content`, { headers: authHeaders });
    check(res, {
      "content 200": (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  group("List brand profiles", () => {
    const res = http.get(`${BASE_URL}/api/v1/brand-profiles`, { headers: authHeaders });
    check(res, {
      "brand profiles 200": (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  group("Logout", () => {
    const res = http.post(`${BASE_URL}/api/v1/auth/logout`, null, { headers: authHeaders });
    check(res, {
      "logout 200": (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  sleep(1);
}
