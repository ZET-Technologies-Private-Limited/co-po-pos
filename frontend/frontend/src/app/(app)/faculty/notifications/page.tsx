"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Bell, CheckCheck, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

type FilterType = "all" | "critical" | "success" | "reminder" | "system";

function mapType(value: string | undefined): FilterType {
  const v = (value || "").toLowerCase();
  if (v === "critical" || v === "success" || v === "reminder" || v === "system") return v;
  return "system";
}

export default function FacultyNotificationsPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getNotifications();
      const list = Array.isArray(res?.items) ? res.items : Array.isArray(res?.notifications) ? res.notifications : Array.isArray(res) ? res : [];
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

  const unread = useMemo(() => items.filter((n) => !(n?.is_read ?? n?.read)).length, [items]);

  async function markAll() {
    const unreadIds = items
      .filter((n) => !(n?.is_read ?? n?.read))
      .map((n) => String(n.id))
      .filter(Boolean);
    if (!unreadIds.length) return;
    await apiClient.markNotificationsRead(unreadIds);
    await load();
  }

  async function openItem(n: any) {
    if (!(n?.is_read ?? n?.read) && n?.id) {
      try {
        await apiClient.markNotificationsRead([String(n.id)]);
      } catch {
        // no-op
      }
    }
    router.push(n?.link || "/faculty/dashboard");
  }

  const tabs: { id: FilterType; label: string }[] = [
    { id: "all", label: `All (${items.length})` },
    { id: "critical", label: "Critical" },
    { id: "success", label: "Approved" },
    { id: "reminder", label: "Reminders" },
    { id: "system", label: "System" },
  ];

  return (
    <AccessGate feature="notifications" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-4xl mx-auto pb-20">
        <motion.div variants={fadeSlideUp} className="flex justify-between items-end pb-6 border-b border-white/10">
          <div>
            <h1 className="text-3xl text-white font-display">Notification Centre</h1>
            <p className="text-white/50 mt-1">{unread > 0 ? `${unread} unread notifications` : "All caught up"}</p>
          </div>
          <button onClick={() => void markAll()} className="text-xs border border-white/20 px-3 py-2 text-white/70 hover:text-white">
            <span className="inline-flex items-center gap-2"><CheckCheck className="w-3 h-3" /> Mark All Read</span>
          </button>
        </motion.div>

        <div className="flex border-b border-white/10 mt-4">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setFilter(t.id)}
              className={`px-4 py-3 text-xs ${filter === t.id ? "text-brand border-b-2 border-brand" : "text-white/40"}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? <p className="text-white/60 py-10">Loading notifications...</p> : null}
        {error ? <p className="text-alert py-10">{error}</p> : null}

        {!loading && !error ? (
          <div className="divide-y divide-white/10">
            {filtered.map((n, idx) => {
              const isRead = Boolean(n?.is_read ?? n?.read);
              return (
                <button
                  key={n?.id || idx}
                  onClick={() => void openItem(n)}
                  className={`w-full text-left py-4 px-2 hover:bg-white/[0.02] ${isRead ? "opacity-60" : "opacity-100"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <Bell className="w-4 h-4 text-brand shrink-0" />
                      <div className="min-w-0">
                        <p className="text-white text-sm truncate">{n?.title || "Notification"}</p>
                        <p className="text-white/50 text-xs mt-1">{n?.message || ""}</p>
                        <p className="text-white/30 text-[11px] mt-1">{n?.created_at || n?.timestamp || ""}</p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/30 shrink-0" />
                  </div>
                </button>
              );
            })}
            {filtered.length === 0 ? <p className="text-white/40 text-sm py-10">No notifications in this filter.</p> : null}
          </div>
        ) : null}
      </motion.div>
    </AccessGate>
  );
}
