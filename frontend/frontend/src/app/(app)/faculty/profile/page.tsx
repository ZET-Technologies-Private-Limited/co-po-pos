"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Mail, Shield, LogOut, KeyRound, User, Building2 } from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import { useRouter } from "next/navigation";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

export default function FacultyProfilePage() {
  const { user, activeRole, logout } = useAuthStore();
  const router = useRouter();

  const initials = useMemo(() => {
    if (!user?.name) return "?";
    const parts = user.name.trim().split(" ");
    return ((parts[0]?.[0] || "") + (parts[parts.length - 1]?.[0] || "")).toUpperCase();
  }, [user?.name]);

  if (!user || activeRole !== "faculty") {
    return <div className="py-20 text-white/40 text-sm font-mono">Faculty profile is available only for faculty users.</div>;
  }

  const fields = [
    { icon: User, label: "Employee ID", value: user.employeeId || user.id || "—" },
    { icon: Mail, label: "Email", value: user.email || "Not available" },
    { icon: Building2, label: "Department", value: user.department || "—" },
    { icon: Shield, label: "Role", value: activeRole },
  ];

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full px-6 lg:px-10 py-8 pb-24">
      {/* Header */}
      <motion.div variants={fadeSlideUp} className="border-b border-white/10 pb-8 mb-10 flex items-start justify-between">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center text-xl text-white font-display shrink-0">
            {initials}
          </div>
          <div>
            <h1 className="text-3xl text-white font-display">{user.name}</h1>
            <p className="text-white/40 text-sm mt-1 font-mono">{user.department || "Department"} · Faculty</p>
          </div>
        </div>
        <button
          onClick={() => { logout(); router.push("/login"); }}
          className="flex items-center gap-2 text-xs font-mono text-red-400/70 hover:text-red-400 border border-red-400/20 hover:border-red-400/50 px-3 py-2 transition-colors"
        >
          <LogOut className="w-3 h-3" /> Logout
        </button>
      </motion.div>

      {/* Profile Fields — full-width list */}
      <motion.div variants={fadeSlideUp} className="divide-y divide-white/5 mb-10">
        {fields.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <Icon className="w-4 h-4 text-white/30 shrink-0" />
              <span className="text-xs font-mono text-white/30 uppercase tracking-widest w-28">{label}</span>
            </div>
            <span className="text-sm text-white/70 font-mono">{String(value)}</span>
          </div>
        ))}
      </motion.div>

      {/* Password Reset */}
      <motion.div variants={fadeSlideUp} className="border-t border-white/5 pt-8">
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">Security</h2>
        <button
          onClick={() => router.push("/reset-password")}
          className="flex items-center gap-2 text-sm text-white/60 hover:text-white transition-colors"
        >
          <KeyRound className="w-4 h-4" />
          Reset Password via OTP
        </button>
      </motion.div>
    </motion.div>
  );
}
