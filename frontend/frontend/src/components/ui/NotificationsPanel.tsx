"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useUIStore, NotifType } from "@/lib/uiStore";
import { useRouter } from "next/navigation";
import { X, Bell, CheckCircle2, AlertCircle, Info, Clock, ShieldAlert, Settings, ArrowRight } from "lucide-react";

const TYPE_ICON: Record<NotifType, any> = {
  co_alert: AlertCircle,
  marks: CheckCircle2,
  approval: ShieldAlert,
  deadline: Clock,
  system: Info,
};
const TYPE_COLOR: Record<NotifType, string> = {
  co_alert: "text-alert",
  marks: "text-attain",
  approval: "text-aurora",
  deadline: "text-brand",
  system: "text-white/40",
};
const TYPE_LABELS: Record<NotifType, string> = {
  co_alert: "CO Alerts",
  marks: "Marks",
  approval: "Approvals",
  deadline: "Deadlines",
  system: "System",
};

type FilterTab = "all" | "unread" | NotifType;

export function NotificationsPanel() {
  const { notifOpen, closeNotif, notifications, markAllRead, markRead } = useUIStore();
  const [tab, setTab] = useState<FilterTab>("all");
  const router = useRouter();
  const unread = notifications.filter(n => !n.read).length;

  const filtered = notifications.filter(n => {
    if (tab === "all") return true;
    if (tab === "unread") return !n.read;
    return n.type === tab;
  });

  const tabs: { key: FilterTab; label: string }[] = [
    { key: "all", label: "All" },
    { key: "unread", label: "Unread" },
    { key: "co_alert", label: "CO Alerts" },
    { key: "marks", label: "Marks" },
    { key: "approval", label: "Approvals" },
    { key: "deadline", label: "Deadlines" },
    { key: "system", label: "System" },
  ];

  function handleAction(href: string, id: string) {
    markRead(id);
    closeNotif();
    router.push(href);
  }

  return (
    <AnimatePresence>
      {notifOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={closeNotif}
            className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm"
            aria-hidden="true"
          />
          <motion.div
            role="dialog"
            aria-label="Notifications"
            aria-modal="true"
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 h-full w-full max-w-sm bg-[#0D1829] border-l border-white/10 z-[100] flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-white/60" aria-hidden="true" />
                <h2 className="text-white font-display text-lg">Notifications</h2>
                {unread > 0 && (
                  <span className="w-5 h-5 rounded-full bg-brand flex items-center justify-center text-[10px] text-white font-mono" aria-label={`${unread} unread`}>{unread}</span>
                )}
              </div>
              <div className="flex items-center gap-3">
                {unread > 0 && (
                  <button onClick={markAllRead} className="text-xs font-mono text-white/40 hover:text-white transition-colors uppercase tracking-widest">
                    Mark all read
                  </button>
                )}
                <button onClick={closeNotif} aria-label="Close notifications" className="text-white/30 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-brand rounded">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-0 overflow-x-auto border-b border-white/10 scrollbar-none">
              {tabs.map(t => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`shrink-0 px-4 py-3 text-[10px] font-mono uppercase tracking-widest transition-colors border-b-2 ${tab === t.key ? "border-brand text-white" : "border-transparent text-white/30 hover:text-white/60"}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto divide-y divide-white/5">
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-4 py-16 px-8 text-center">
                  <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                    <Bell className="w-7 h-7 text-white/20" />
                  </div>
                  <p className="text-white/50 font-medium">You are all caught up!</p>
                  <p className="text-white/25 text-sm font-light">No notifications in this category.</p>
                </div>
              ) : (
                filtered.map((n, i) => {
                  const Icon = TYPE_ICON[n.type];
                  return (
                    <motion.div
                      key={n.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className={`flex items-start gap-3 px-6 py-4 transition-colors ${!n.read ? "bg-white/[0.03]" : ""} hover:bg-white/[0.05]`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${TYPE_COLOR[n.type]}`} aria-hidden="true" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`font-medium text-sm leading-snug ${!n.read ? "text-white" : "text-white/50"}`}>{n.title}</p>
                          <div className="flex items-center gap-1.5 shrink-0">
                            {!n.read && (
                              <button
                                onClick={() => markRead(n.id)}
                                title="Mark as read"
                                className="w-2 h-2 rounded-full bg-brand hover:bg-brand/60 transition-colors focus:outline-none focus:ring-1 focus:ring-brand"
                                aria-label="Mark as read"
                              />
                            )}
                          </div>
                        </div>
                        <p className="text-white/40 text-xs font-light mt-0.5 leading-relaxed">{n.desc}</p>
                        <div className="flex items-center justify-between mt-2">
                          <p className="text-white/25 text-[10px] font-mono">{n.time}</p>
                          {n.actionLabel && n.actionHref && (
                            <button
                              onClick={() => handleAction(n.actionHref!, n.id)}
                              className="flex items-center gap-1 text-[10px] font-mono text-brand hover:text-aurora transition-colors uppercase tracking-widest focus:outline-none focus:underline"
                            >
                              {n.actionLabel} <ArrowRight className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between">
              <p className="text-white/20 text-[10px] font-mono uppercase tracking-widest">Nexus Engine</p>
              <button
                onClick={() => { closeNotif(); router.push("/profile"); }}
                className="flex items-center gap-1.5 text-[10px] font-mono text-white/30 hover:text-white transition-colors uppercase tracking-widest"
              >
                <Settings className="w-3 h-3" /> Notification Settings
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
