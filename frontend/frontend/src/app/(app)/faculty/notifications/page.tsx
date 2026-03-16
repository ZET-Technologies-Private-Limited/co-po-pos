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

function typeColor(type: FilterType) {
  if (type === "critical") return "text-red-400";
  if (type === "success") return "text-emerald-400";
  if (type === "reminder") return "text-amber-400";
  return "text-white/40";
}

export default function FacultyNotificationsPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await apiClient.getNotifications();
      const list = Array.isArray(res?.items) ? res.items
        : Array.isArray(res?.notifications) ? res.notifications
        : Array.isArray(res) ? res : [];
      setItems(list);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load notifications.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((n) => mapType(n?.type) === filter);
  }, [items, filter]);

  const unread = useMemo(() => items.filter((n) => !(n?.is_read ?? n?.read)).length, [items]);

  async function markAll() {
    const unreadIds = items.filter((n) => !(n?.is_read ?? n?.read)).map((n) => String(n.id)).filter(Boolean);
    if (!unreadIds.length) return;
    await apiClient.markNotificationsRead(unreadIds);
    await load();
  }

  async function openItem(n: any) {
    if (!(n?.is_read ?? n?.read) && n?.id) {
      try { await apiClient.markNotificationsRead([String(n.id)]); } catch { /* no-op */ }
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
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full px-6 lg:px-10 py-8 pb-20">
        {/* Header */}
        <motion.div variants={fadeSlideUp} className="border-b border-white/10 pb-6 mb-0 flex items-end justify-between">
          <div>
            <h1 className="text-3xl text-white font-display">Notification Centre</h1>
            <p className="text-white/40 text-sm mt-1 font-mono">
              {unread > 0 ? `${unread} unread` : "All caught up"}
            </p>
          </div>
          <button
            onClick={() => void markAll()}
            disabled={unread === 0}
            className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white border border-white/10 hover:border-white/30 px-3 py-2 transition-colors disabled:opacity-30"
          >
            <CheckCheck className="w-3 h-3" /> Mark All Read
          </button>
        </motion.div>

        {/* Filter Tabs */}
        <div className="flex border-b border-white/10">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setFilter(t.id)}
              className={`px-4 py-3 text-xs font-mono transition-colors ${
                filter === t.id
                  ? "text-brand border-b-2 border-brand"
                  : "text-white/30 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading && <p className="text-white/40 text-sm py-10 font-mono">Loading notifications...</p>}
        {error && <p className="text-red-400 text-sm py-10">{error}</p>}

        {!loading && !error && (
          <div className="divide-y divide-white/5">
            {filtered.map((n, idx) => {
              const isRead = Boolean(n?.is_read ?? n?.read);
              const type = mapType(n?.type);
              return (
                <button
                  key={n?.id || idx}
                  onClick={() => void openItem(n)}
                  className={`w-full text-left py-5 hover:bg-white/[0.02] transition-colors ${isRead ? "opacity-50" : ""}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 min-w-0">
                      <Bell className={`w-4 h-4 shrink-0 mt-0.5 ${typeColor(type)}`} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          {!isRead && <span className="w-1.5 h-1.5 rounded-full bg-brand shrink-0" />}
                          <p className="text-white text-sm font-medium truncate">{n?.title || "Notification"}</p>
                        </div>
                        {n?.message && (
                          <p className="text-white/50 text-xs mt-1">{n.message}</p>
                        )}
                        <p className="text-white/20 text-[10px] font-mono mt-1">
                          {n?.created_at || n?.timestamp || ""}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/20 shrink-0 mt-0.5" />
                  </div>
                </button>
              );
            })}
            {filtered.length === 0 && (
              <p className="text-white/30 text-sm italic py-10">No notifications in this category.</p>
            )}
          </div>
        )}
      </motion.div>
    </AccessGate>
  );
}
