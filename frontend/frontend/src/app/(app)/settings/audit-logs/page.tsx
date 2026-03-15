"use client";

import { motion } from "framer-motion";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import { Clock, User, Activity, ShieldCheck, CheckCircle, Search, Filter } from "lucide-react";
import Link from "next/link";

const AUDIT_LOGS = [
  { id: 1, user: "Dr. Ramesh Kumar", action: "Updated CO-PO Mapping", target: "CS301", timestamp: "10 mins ago", status: "Success", color: "text-brand" },
  { id: 2, user: "System (AI)", action: "Generated CO Suggestions", target: "ML-401", timestamp: "45 mins ago", status: "Success", color: "text-aurora" },
  { id: 3, user: "Dr. Meera Iyer", action: "Approved Syllabus Scan", target: "EC201", timestamp: "2 hours ago", status: "Success", color: "text-insight" },
  { id: 4, user: "Admin", action: "Invited new Faculty member", target: "Univ-Wide", timestamp: "5 hours ago", status: "Success", color: "text-attain" },
  { id: 5, user: "Dr. Ramesh Kumar", action: "Uploaded Marks Sheet", target: "CS301 (T2)", timestamp: "1 day ago", status: "Warning", color: "text-alert" },
  { id: 6, user: "System", action: "Backup Cycle Completed", target: "Infrastructure", timestamp: "2 days ago", status: "Success", color: "text-white/40" },
];

export default function AuditLogsPage() {
  return (
    <div className="w-full min-h-screen pb-24">
      <motion.div 
        variants={staggerContainer} 
        initial="hidden" 
        animate="visible" 
        className="max-w-5xl mx-auto px-6 pt-12"
      >
        <motion.div variants={fadeSlideUp} className="flex items-end justify-between mb-16">
          <div>
            <div className="flex items-center gap-3 text-sm font-mono text-white/40 uppercase tracking-widest mb-4">
              <span className="w-8 h-[1px] bg-white/20"></span>
              Institutional Governance
            </div>
            <h1 className="text-5xl font-display text-white">System Audit Logs</h1>
          </div>
          <Link href="/settings" className="px-6 py-3 border border-white/20 text-white font-medium text-sm hover:border-white transition-colors font-mono">
            Back to Settings
          </Link>
        </motion.div>

        {/* Global Search/Filter for Logs */}
        <motion.div variants={fadeSlideUp} className="flex items-center gap-12 mb-16 pb-8 border-b border-white/10">
           <div className="flex items-center gap-4 flex-1">
              <Search className="w-4 h-4 text-white/20" />
              <input 
                placeholder="Search audit trail by user, course, or action..."
                className="bg-transparent text-white placeholder-white/20 outline-none w-full text-lg font-light"
              />
           </div>
           <div className="flex items-center gap-8">
              <button className="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest hover:text-white transition-colors">
                 <Filter className="w-3 h-3" /> Filter Trace
              </button>
              <button className="flex items-center gap-2 text-[10px] font-mono text-white/30 uppercase tracking-widest hover:text-white transition-colors">
                 <Activity className="w-3 h-3" /> Real-time Feed
              </button>
           </div>
        </motion.div>

        {/* Logs Table (Flat Design) */}
        <div className="flex flex-col gap-0 border-t border-white/5">
          {AUDIT_LOGS.map((log) => (
            <motion.div 
              key={log.id} 
              variants={fadeSlideUp}
              className="group flex flex-col md:flex-row items-start md:items-center py-8 border-b border-white/5 hover:bg-white/[0.01] transition-all relative overflow-hidden px-4"
            >
              <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-brand opacity-0 group-hover:opacity-100 transition-opacity" />
              
              <div className="w-16 shrink-0 mb-4 md:mb-0">
                <div className="w-10 h-10 flex items-center justify-center border border-white/10 text-white/20">
                   <Clock className="w-4 h-4" />
                </div>
              </div>

              <div className="flex-1 min-w-0 pr-8">
                 <div className="flex items-center gap-3 mb-1">
                    <span className="text-white font-medium">{log.user}</span>
                    <span className="text-white/20 font-mono text-[10px] uppercase tracking-widest">via WebUI</span>
                 </div>
                 <p className="text-white/50 text-sm font-light leading-relaxed">
                   {log.action} <span className="text-white/80">[{log.target}]</span>
                 </p>
              </div>

              <div className="flex items-center gap-12 mt-6 md:mt-0 shrink-0">
                 <div className="text-right">
                    <p className="text-white/60 font-mono text-xs">{log.timestamp}</p>
                    <p className="text-[10px] font-mono text-white/20 uppercase tracking-widest mt-1">Audit Timestamp</p>
                 </div>
                 <div className="w-24 text-right">
                    <span className={`px-2 py-0.5 border text-[9px] font-mono uppercase tracking-widest ${
                      log.status === 'Success' ? 'border-attain/30 text-attain bg-attain/5' : 
                      log.status === 'Warning' ? 'border-alert/30 text-alert bg-alert/5' : 
                      'border-white/10 text-white/30'
                    }`}>
                      {log.status}
                    </span>
                 </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div variants={fadeSlideUp} className="mt-16 text-center">
           <button className="text-sm font-mono text-white/20 hover:text-white transition-colors uppercase tracking-[0.4em]">
              Load Archived History
           </button>
        </motion.div>
      </motion.div>
    </div>
  );
}
