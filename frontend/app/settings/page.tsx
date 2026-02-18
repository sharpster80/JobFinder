"use client";
import { useEffect, useState } from "react";
import { getScrapeRuns } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [subscribed, setSubscribed] = useState(false);

  useEffect(() => {
    getScrapeRuns().then(setRuns);
  }, []);

  async function subscribePush() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      alert("Push notifications not supported in this browser.");
      return;
    }
    const reg = await navigator.serviceWorker.ready;
    const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidKey,
    });
    await fetch(`${API_URL}/api/notifications/subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: sub.endpoint, subscription_json: sub.toJSON() }),
    });
    setSubscribed(true);
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <section className="mb-8">
        <h2 className="font-semibold mb-3">Browser Notifications</h2>
        {subscribed
          ? <p className="text-green-600 text-sm">✓ Subscribed to push notifications</p>
          : <button onClick={subscribePush} className="px-4 py-2 bg-blue-600 text-white rounded text-sm">
              Enable Push Notifications
            </button>
        }
      </section>

      <section>
        <h2 className="font-semibold mb-3">Scrape History</h2>
        <table className="w-full text-sm border rounded">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left">Source</th>
              <th className="px-4 py-2 text-left">Time</th>
              <th className="px-4 py-2 text-right">Found</th>
              <th className="px-4 py-2 text-right">New</th>
              <th className="px-4 py-2 text-left">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {runs.map(r => (
              <tr key={r.id} className={r.error ? "bg-red-50" : ""}>
                <td className="px-4 py-2">{r.source}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(r.started_at).toLocaleString()}</td>
                <td className="px-4 py-2 text-right">{r.jobs_found}</td>
                <td className="px-4 py-2 text-right font-medium">{r.jobs_new}</td>
                <td className="px-4 py-2 text-red-500 text-xs">{r.error || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
