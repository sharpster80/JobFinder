// Server-side uses Docker service name, client-side uses localhost
function getApiUrl() {
  // If running in browser (client-side), always use localhost
  if (typeof window !== 'undefined') {
    return "http://localhost:8000";
  }
  // Server-side: use Docker service name
  return process.env.API_URL || "http://api:8000";
}

const API_URL = getApiUrl();

export async function getJobs(params: {
  status?: string;
  min_score?: number;
  criteria_id?: string;
} = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.min_score) query.set("min_score", String(params.min_score));
  if (params.criteria_id) query.set("criteria_id", params.criteria_id);
  const res = await fetch(`${API_URL}/api/jobs?${query}`, { cache: "no-store" });
  return res.json();
}

export async function updateJobStatus(matchId: string, status: string) {
  const res = await fetch(`${API_URL}/api/jobs/${matchId}/status?status=${status}`, {
    method: "PATCH",
  });
  return res.json();
}

export async function getCriteria() {
  const res = await fetch(`${API_URL}/api/criteria`, { cache: "no-store" });
  return res.json();
}

export async function triggerScrape(source?: string) {
  const query = source ? `?source=${source}` : "";
  const res = await fetch(`${API_URL}/api/scrapes/trigger${query}`, { method: "POST" });
  return res.json();
}

export async function getScrapeRuns() {
  const res = await fetch(`${API_URL}/api/scrapes`, { cache: "no-store" });
  return res.json();
}
