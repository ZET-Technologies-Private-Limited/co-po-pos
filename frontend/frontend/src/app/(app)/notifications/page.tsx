"use client";

import { motion } from "framer-motion";
import { Bell, CheckCircle2, ShieldAlert, Cpu, Award, Trash2, CheckSquare } from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import { useUIStore } from "@/lib/uiStore";

export default function NotificationsPage() {
  const { notifications, markAllRead, addToast } = useUIStore();

  const getIcon = (type: string) => {
    switch (type) {
      case "error":   return <ShieldAlert className="w-5 h-5 text-alert" />;
      case "success": return <CheckCircle2 className="w-5 h-5 text-attain" />;
      case "info":    return <Cpu className="w-5 h-5 text-brand" />;
      default:        return <Award className="w-5 h-5 text-insight" />;
    }
  };

  const handleClearAll = () => {
    // We don't persist cleared state yet; just toast
    addToast("All notifications cleared.", "info");
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-4xl mx-auto pb-32">

      <motion.div variants={fadeSlideUp} className="mb-12 flex justify-between items-end flex-wrap gap-6 border-b border-white/10 pb-8">
        <div>
          <h1 className="text-4xl font-display text-white mb-2">Notification Centre</h1>
          <p className="text-white/40 font-light italic">System-wide alerts, workflow approvals, and deadline triggers.</p>
        </div>
        <div className="flex gap-4">
          <button onClick={markAllRead}
            className="px-5 py-2 hover:bg-white/5 border border-transparent hover:border-white/10 text-white/50 hover:text-white transition-colors text-[10px] font-mono uppercase tracking-widest flex items-center gap-2 rounded">
            <CheckSquare className="w-3.5 h-3.5" /> Mark All Read
          </button>
          <button onClick={handleClearAll}
            className="px-5 py-2 hover:bg-alert/10 border border-transparent hover:border-alert/30 text-white/50 hover:text-alert transition-colors text-[10px] font-mono uppercase tracking-widest flex items-center gap-2 rounded">
            <Trash2 className="w-3.5 h-3.5" /> Clear All
          </button>
        </div>
      </motion.div>

      <motion.div variants={fadeSlideUp} className="flex flex-col gap-4">
        {notifications.length === 0 ? (
          <div className="py-32 flex flex-col items-center justify-center text-white/20">
            <Bell className="w-12 h-12 mb-4" />
            <p className="text-sm font-mono uppercase tracking-widest">Inbox is clear</p>
          </div>
        ) : notifications.map(notif => (
          <motion.div key={notif.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className={`group relative flex items-start gap-6 p-6 rounded-xl border transition-colors cursor-default
              ${!notif.read ? "bg-white/[0.03] border-white/20 shadow-lg" : "bg-transparent border-white/5 hover:bg-white/[0.01]"}`}>
            {!notif.read && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-12 rounded-r-md bg-brand" />}
            <div className={`mt-1 p-3 rounded-full ${!notif.read ? "bg-black/40" : "bg-white/5"}`}>
              {getIcon(notif.type)}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <h4 className={`text-lg font-display tracking-wide ${!notif.read ? "text-white" : "text-white/60"}`}>{notif.title}</h4>
                <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">{notif.time}</span>
              </div>
              <p className={`text-sm font-light leading-relaxed max-w-2xl ${!notif.read ? "text-white/80" : "text-white/40"}`}>
                {notif.desc}
              </p>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}
