"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, Search, ShieldAlert, Cpu, Lock,
  UserCheck, RefreshCw, Download, CheckCircle2
} from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useUIStore } from "@/lib/uiStore";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";

export default function AdminAuditLogPage() {
  const [auditLog, setAuditLog] = useState<{ id: string; timestamp: string; type: string; userId: string; action: string; ip: string; role?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useUIStore();
  const { user } = useAuthStore();

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getAuditLog(200);
      setAuditLog(Array.isArray(data) ? data.map((d: any) => ({ ...d, role: d.role ?? "—" })) : []);
    } catch (e: any) {
      setError(e?.message || "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredData = useMemo(() =>
    auditLog.filter(d =>
      (typeFilter === "all" || (d.type ?? "").toLowerCase() === typeFilter) &&
      (roleFilter === "all" || (d.role ?? "").toLowerCase() === roleFilter) &&
      ((d.userId ?? "").toLowerCase().includes(search.toLowerCase()) ||
       (d.action ?? "").toLowerCase().includes(search.toLowerCase()) ||
       (d.ip ?? "").includes(search))
    ), [auditLog, search, typeFilter, roleFilter]);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "login":       return <UserCheck  className="w-3.5 h-3.5 text-attain" />;
      case "login_fail":  return <ShieldAlert className="w-3.5 h-3.5 text-alert" />;
      case "co_generate": return <Cpu        className="w-3.5 h-3.5 text-brand" />;
      case "approval":    return <CheckCircle2 className="w-3.5 h-3.5 text-attain" />;
      case "override":    return <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />;
      case "system":      return <Lock       className="w-3.5 h-3.5 text-insight" />;
      case "user":        return <UserCheck  className="w-3.5 h-3.5 text-brand" />;
      case "ay_lock":     return <Lock       className="w-3.5 h-3.5 text-aurora" />;
      default:            return <Activity   className="w-3.5 h-3.5 text-white/40" />;
    }
  };

  const handleForceSync = () => {
    void load();
    addToast("Audit log refreshed.", "success");
  };

  const handleExportCSV = () => {
    const headers = ["ID", "Timestamp", "Type", "User ID", "Role", "Action", "IP"];
    const rows = filteredData.map(log =>
      [log.id, log.timestamp, log.type, log.userId, log.role, `"${log.action.replace(/"/g, '""')}"`, log.ip].join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `audit_log_${new Date().toISOString().split("T")[0]}.csv`;
    a.click(); URL.revokeObjectURL(url);
    addToast(`Exported ${filteredData.length} audit entries as CSV.`, "success");
  };

  const handleExportXLSX = async () => {
    const XLSX = await import("xlsx");
    const data = filteredData.map(log => ({
      ID: log.id, Timestamp: log.timestamp, Type: log.type,
      "User ID": log.userId, Role: log.role, Action: log.action, IP: log.ip,
    }));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(data), "Audit Log");
    XLSX.writeFile(wb, `audit_log_${new Date().toISOString().split("T")[0]}.xlsx`);
    addToast(`Exported ${filteredData.length} entries as Excel.`, "success");
  };

  const uniqueRoles = useMemo(() => [...new Set(auditLog.map(l => l.role).filter(Boolean))], [auditLog]);

  if (loading && auditLog.length === 0) {
    return (
      <AccessGate feature="audit_trail" deny="lock">
        <div className="max-w-7xl mx-auto pb-32 py-8"><p className="text-white/60">Loading audit log...</p></div>
      </AccessGate>
    );
  }
  if (error && auditLog.length === 0) {
    return (
      <AccessGate feature="audit_trail" deny="lock">
        <div className="max-w-7xl mx-auto pb-32 py-8"><p className="text-alert">{error}</p></div>
      </AccessGate>
    );
  }

  return (
    <AccessGate feature="audit_trail" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-7xl mx-auto pb-32">

        {/* Header */}
        <motion.div variants={fadeSlideUp} className="flex justify-between items-end pb-8 border-b border-white/5">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 bg-alert animate-pulse" />
              <span className="text-[10px] font-mono text-alert uppercase tracking-widest">Live Surveillance Active</span>
            </div>
            <h1 className="text-4xl font-display text-white">System Audit Trail</h1>
            <p className="text-white/40 font-light mt-1">
              {auditLog.length} events logged · last: {auditLog[0]?.timestamp || "No events yet"}
            </p>
          </div>
          <div className="flex gap-3">
            <button onClick={handleForceSync}
              className="px-5 py-2.5 border border-white/10 text-white/40 hover:text-white hover:border-white/30 text-[10px] font-mono uppercase tracking-widest flex items-center gap-2 transition-colors">
              <RefreshCw className="w-3.5 h-3.5" /> Force Sync
            </button>
            <button onClick={handleExportCSV}
              className="px-5 py-2.5 border border-white/10 text-white/40 hover:text-white hover:border-white/30 text-[10px] font-mono uppercase tracking-widest flex items-center gap-2 transition-colors">
              <Download className="w-3.5 h-3.5" /> Export CSV
            </button>
            <button onClick={handleExportXLSX}
              className="px-5 py-2.5 bg-brand text-white hover:bg-brand/90 transition-colors text-[10px] font-mono uppercase tracking-widest flex items-center gap-2">
              <Download className="w-3.5 h-3.5" /> Export Excel
            </button>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div variants={fadeSlideUp} className="flex gap-4 py-5 border-b border-white/5 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search by User ID, IP, or action..."
              className="w-full bg-white/[0.02] border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white outline-none focus:border-brand transition-colors font-mono" />
          </div>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
            className="bg-white/[0.02] border border-white/10 px-4 py-2.5 text-sm text-white outline-none text-[10px] font-mono uppercase">
            <option value="all">All Event Types</option>
            <option value="login">Authentications</option>
            <option value="login_fail">Failed Logins</option>
            <option value="co_generate">CO Generation</option>
            <option value="marks">Marks Entries</option>
            <option value="approval">Approvals</option>
            <option value="override">Overrides</option>
            <option value="system">System Config</option>
            <option value="user">User Management</option>
            <option value="ay_lock">AY Locks</option>
          </select>
          <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
            className="bg-white/[0.02] border border-white/10 px-4 py-2.5 text-sm text-white outline-none text-[10px] font-mono uppercase">
            <option value="all">All Roles</option>
            {uniqueRoles.map(r => <option key={r} value={r} className="bg-[#0a0a0f]">{r}</option>)}
          </select>
          <span className="text-[10px] font-mono text-white/20 self-center">{filteredData.length} results</span>
        </motion.div>

        {/* Log table */}
        <motion.div variants={fadeSlideUp} className="border border-white/10 bg-white/[0.01] overflow-hidden">
          <div className="flex items-center gap-4 bg-white/[0.02] border-b border-white/10 px-6 py-3 font-mono text-[9px] uppercase tracking-widest text-white/30">
            <div className="w-8">Type</div>
            <div className="w-44">Timestamp</div>
            <div className="w-32">User</div>
            <div className="flex-1">Action</div>
            <div className="w-28 text-right">Source IP</div>
          </div>
          <div className="flex flex-col h-[600px] overflow-y-auto divide-y divide-white/5">
            <AnimatePresence>
              {filteredData.length === 0 ? (
                <div className="flex-1 flex items-center justify-center text-white/20 text-[10px] font-mono uppercase tracking-widest py-16">
                  {auditLog.length === 0 ? "No events yet. Perform actions to generate audit entries." : "No events match query."}
                </div>
              ) : filteredData.map(log => (
                <motion.div key={log.id} initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-white/[0.01] transition-colors">
                  <div className="w-8 flex justify-center">{getTypeIcon(log.type)}</div>
                  <div className="w-44 text-white/30 text-[10px] font-mono">{log.timestamp}</div>
                  <div className="w-32">
                    <p className="text-white text-xs font-mono font-bold">{log.userId}</p>
                    <p className={`text-[9px] uppercase tracking-widest ${log.role === "admin" ? "text-brand" : "text-white/30"}`}>{log.role}</p>
                  </div>
                  <div className="flex-1 text-white/60 text-xs font-light leading-relaxed">{log.action}</div>
                  <div className="w-28 text-right text-white/30 text-xs font-mono">{log.ip}</div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </motion.div>

      </motion.div>
    </AccessGate>
  );
}
