"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

type FilterType = "all" | "critical" | "success" | "reminder" | "system";

function mapType(value: string | undefined): FilterType {
  const v = (value || "").toLowerCase();
  if (v === "critical" || v === "success" || v === "reminder" || v === "system") return v;
  return "system";
}

export default function LeadNotificationsPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterType>("all");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getNotifications();
      const list = Array.isArray(res?.items) ? res.items : Array.isArray(res) ? res : [];
      setItems(list);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((n) => mapType(n?.type) === filter);
  }, [items, filter]);

  async function mark(item: any) {
    if (item?.id) await apiClient.markNotificationsRead([String(item.id)]);
    router.push(item?.link || "/lead/dashboard");
  }

  return (
    <AccessGate feature="notifications" deny="lock">
      <div className="max-w-4xl mx-auto pb-24 space-y-4">
        <h1 className="text-3xl text-white font-display">Lead Notifications</h1>
        <div className="flex gap-2 text-xs">
          {(["all", "critical", "success", "reminder", "system"] as FilterType[]).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 border ${filter === f ? "text-brand border-brand" : "text-white/50 border-white/20"}`}>{f}</button>
          ))}
        </div>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? (
          <div className="space-y-2">
            {filtered.map((n, idx) => (
              <button key={n?.id || idx} onClick={() => void mark(n)} className="w-full text-left border border-white/10 rounded p-3">
                <p className="text-white text-sm">{n?.title || "Notification"}</p>
                <p className="text-white/60 text-xs mt-1">{n?.message || ""}</p>
              </button>
            ))}
            {filtered.length === 0 ? <p className="text-white/40 text-sm">No notifications.</p> : null}
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}
