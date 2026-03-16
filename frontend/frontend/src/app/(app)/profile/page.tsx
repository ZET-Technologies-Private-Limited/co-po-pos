"use client";

import { motion } from "framer-motion";
import { 
  User, Mail, Phone, Building2, Shield, Moon, Sun, Monitor, LogOut, Link2, Settings
} from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import { useAuthStore } from "@/lib/authStore";
import { useRouter } from "next/navigation";
import { useUIStore } from "@/lib/uiStore";

export default function ProfilePage() {
  const { user, activeRole, logout } = useAuthStore();
  const router = useRouter();
  const { addToast } = useUIStore();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-4xl mx-auto pb-32">
      
      {/* ── HEADER ── */}
      <motion.div variants={fadeSlideUp} className="mb-12 border-b border-white/10 pb-12 flex flex-col md:flex-row md:items-end gap-8">
         <div className="w-32 h-32 rounded-3xl bg-gradient-to-br from-brand via-aurora to-insight p-1 shrink-0">
            <div className="w-full h-full bg-cosmic rounded-[22px] flex items-center justify-center">
               <span className="text-6xl font-display text-white">{user?.name?.[0] || "?"}</span>
            </div>
         </div>
         <div className="flex-1">
            <h1 className="text-5xl font-display text-white mb-3">{user?.name || "Unidentified User"}</h1>
            <div className="flex items-center gap-4 flex-wrap">
               <span className="px-3 py-1 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase tracking-widest rounded">
                  {user?.id || "N/A"}
               </span>
               <span className="px-3 py-1 bg-brand/10 border border-brand/20 text-brand text-xs font-mono uppercase tracking-widest rounded flex items-center gap-1.5">
                  <Shield className="w-3 h-3" /> {activeRole?.replace('_', ' ') || "NO_ROLE"}
               </span>
            </div>
         </div>
         <div className="shrink-0 flex items-center gap-4">
            <button onClick={handleLogout} className="px-6 py-3 border border-alert/30 text-alert hover:bg-alert hover:text-white transition-colors text-[10px] font-mono uppercase tracking-widest flex items-center gap-2 rounded">
              <LogOut className="w-4 h-4" /> Terminate Session
            </button>
         </div>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
         
         {/* ── IDENTITY RECORD ── */}
         <motion.section variants={fadeSlideUp}>
            <div className="flex items-center gap-3 text-sm font-mono text-white/50 uppercase tracking-widest mb-6 border-b border-white/10 pb-4">
              <User className="w-4 h-4 text-white" /> Identity Record
            </div>
            <div className="bg-white/[0.02] border border-white/5 p-6 rounded-xl flex flex-col gap-6">
               <div className="flex flex-col gap-1 border-b border-white/5 pb-4">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest flex items-center gap-2 mb-1"><Mail className="w-3 h-3" /> Institutional Email</span>
                  <span className="text-white text-lg font-light">{user?.email || "No email linked"}</span>
               </div>
               <div className="flex flex-col gap-1 border-b border-white/5 pb-4">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest flex items-center gap-2 mb-1"><Building2 className="w-3 h-3" /> Department Affiliation</span>
                  <span className="text-white text-lg font-light">{user?.department || "N/A"}</span>
               </div>
               <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest flex items-center gap-2 mb-1"><Link2 className="w-3 h-3" /> Authorized Roles</span>
                  <div className="flex gap-2 mt-2">
                     {user?.roles?.map((r: string) => (
                       <span key={r} className="text-[10px] uppercase font-mono px-2 py-0.5 border border-brand text-brand">{r.replace("_", " ")}</span>
                     )) ?? (
                       <span className="text-[10px] uppercase font-mono px-2 py-0.5 border border-brand text-brand">{activeRole?.replace("_", " ") || "—"}</span>
                     )}
                  </div>
               </div>
            </div>
         </motion.section>

         {/* ── PREFERENCES ── */}
         <motion.section variants={fadeSlideUp}>
            <div className="flex items-center gap-3 text-sm font-mono text-white/50 uppercase tracking-widest mb-6 border-b border-white/10 pb-4">
              <Settings className="w-4 h-4 text-white" /> System Preferences
            </div>
            <div className="bg-white/[0.02] border border-white/5 p-6 rounded-xl flex flex-col gap-6">
               <div className="flex flex-col gap-4 border-b border-white/5 pb-6">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Interface Theme</span>
                  <div className="flex bg-black/40 p-1 rounded-lg border border-white/10">
                     <button onClick={() => addToast("Theme locked to Dark Mode", "success")} className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md bg-white/10 text-white text-xs font-mono uppercase tracking-widest"><Moon className="w-3.5 h-3.5" /> Dark</button>
                     <button onClick={() => addToast("Theme locked to Light Mode", "success")} className="flex-1 flex items-center justify-center gap-2 py-2.5 text-white/30 hover:text-white transition-colors text-xs font-mono uppercase tracking-widest"><Sun className="w-3.5 h-3.5" /> Light</button>
                     <button onClick={() => addToast("Theme set to System Default", "info")} className="flex-1 flex items-center justify-center gap-2 py-2.5 text-white/30 hover:text-white transition-colors text-xs font-mono uppercase tracking-widest"><Monitor className="w-3.5 h-3.5" /> Auto</button>
                  </div>
               </div>
               <div className="flex flex-col gap-4">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Security Controls</span>
                  <button 
                    onClick={() => addToast("Password update link sent to institutional email", "info")}
                    className="text-left w-full max-w-[200px] px-4 py-2 border border-white/10 text-white hover:border-white/30 transition-colors text-xs font-mono uppercase tracking-widest">
                     Update Password
                  </button>
                  <button 
                    onClick={() => addToast("Redirecting to Multi-factor Authentication Setup", "info")}
                    className="text-left w-full max-w-[200px] px-4 py-2 border border-white/10 text-white hover:border-white/30 transition-colors text-xs font-mono uppercase tracking-widest">
                     Configure 2FA
                  </button>
               </div>
            </div>
         </motion.section>

      </div>
    </motion.div>
  );
}
