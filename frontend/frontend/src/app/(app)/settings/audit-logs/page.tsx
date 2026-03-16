"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import { Clock, Activity, ShieldAlert, Cpu, UserCheck, CheckCircle2, Lock, Search, Filter, RefreshCw } from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/apiClient";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getAuditLog(100);
      setLogs(Array.isArray(data) ? data : []);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return logs;
    return logs.filter((l: any) =>
      (l.userId ?? l.user_id ?? "").toLowerCase().includes(q) ||
      (l.action ?? l.description ?? "").toLowerCase().includes(q) ||
      (l.type ?? "").toLowerCase().includes(q)
    );
  }, [logs, search]);

  const getIcon = (type: string) => {
    switch (type) {
      case "login":       return <UserCheck className="w-4 h-4 text-attain" />;
      case "login_fail":  return <ShieldAlert className="w-4 h-4 text-alert" />;
      case "co_generate": return <Cpu className="w-4 h-4 text-brand" />;
      case "approval":    return <CheckCircle2 className="w-4 h-4 text-attain" />;
      case "override":    return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case "ay_lock":     return <Lock className="w-4 h-4 text-aurora" />;
      default:            return <Activity className="w-4 h-4 text-white/40" />;
    }
  };

  return (
    <div className="w-full min-h-screen pb-24">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto px-6 pt-12">
        <motion.div variants={fadeSlideUp} className="flex items-end justify-between mb-12">
          <div>
            <div className="flex items-center gap-3 text-sm font-mono text-white/40 uppercase tracking-widest mb-4">
              <span className="w-8 h-[1px] bg-white/20" /> Institutional Governance
            </div>
            <h1 className="text-5xl font-display text-white">System Audit Logs</h1>
            <p className="text-white/40 font-light mt-2">{logs.length} events recorded</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => void load()} className="flex items-center gap-2 px-4 py-2 border border-white/10 text-white/40 hover:text-white text-xs font-mono uppercase tracking-widest transition-colors">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
            <Link href="/settings" className="px-6 py-3 border border-white/20 text-white font-medium text-sm hover:border-white transition-colors font-mono">
              Back to Settings
            </Link>
          </div>
        </motion.div>

        <motion.div variants={fadeSlideUp} className="flex items-center gap-8 mb-12 pb-8 border-b border-white/10">
          <div className="flex items-center gap-4 flex-1">
            <Search className="w-4 h-4 text-white/20" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by user, action, or event type..."
              className="bg-transparent text-white placeholder-white/20 outline-none w-full text-lg font-light"
            />
          </div>
        </motion.div>

        {loading ? (
          <div className="py-16 text-center text-white/40">Loading audit logs...</div>
        ) : (
          <div className="flex flex-col gap-0 border-t border-white/5">
            {filtered.length === 0 ? (
              <div className="py-16 text-center text-white/20 text-sm font-mono uppercase tracking-widest">
                {logs.length === 0 ? "No audit events recorded yet." : "No events match search."}
              </div>
            ) : filtered.map((log: any, idx: number) => (
              <motion.div
                key={log.id ?? idx}
                variants={fadeSlideUp}
                className="group flex flex-col md:flex-row items-start md:items-center py-8 border-b border-white/5 hover:bg-white/[0.01] transition-all relative overflow-hidden px-4"
              >
                <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-brand opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="w-16 shrink-0 mb-4 md:mb-0">
                  <div className="w-10 h-10 flex items-center justify-center border border-white/10 text-white/20">
                    {getIcon(log.type ?? log.action_type ?? "")}
                  </div>
                </div>

                <div className="flex-1 min-w-0 pr-8">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-white font-medium">{log.userId ?? log.user_id ?? log.user ?? "—"}</span>
                    {log.role && <span className="text-white/20 font-mono text-[10px] uppercase tracking-widest">{log.role}</span>}
                  </div>
                  <p className="text-white/50 text-sm font-light leading-relaxed">
                    {log.action ?? log.description ?? "—"}
                  </p>
                </div>

                <div className="flex items-center gap-8 mt-4 md:mt-0 shrink-0">
                  <div className="text-right">
                    <p className="text-white/60 font-mono text-xs">{log.timestamp ?? log.created_at ?? "—"}</p>
                    <p className="text-[10px] font-mono text-white/20 uppercase tracking-widest mt-1">{log.ip ?? ""}</p>
                  </div>
                  <div className="w-20 text-right">
                    <span className="px-2 py-0.5 border text-[9px] font-mono uppercase tracking-widest border-attain/30 text-attain bg-attain/5">
                      {log.type ?? "event"}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
