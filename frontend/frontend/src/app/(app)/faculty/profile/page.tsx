"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Mail, Shield, LogOut, KeyRound, User } from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import { useRouter } from "next/navigation";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

export default function FacultyProfilePage() {
  const { user, activeRole, logout } = useAuthStore();
  const router = useRouter();

  const initials = useMemo(() => {
    if (!user?.name) return "?";
    const parts = user.name.trim().split(" ");
    return (parts[0]?.[0] || "") + (parts[parts.length - 1]?.[0] || "");
  }, [user?.name]);

  if (!user || activeRole !== "faculty") {
    return <div className="py-20 text-white/60">Faculty profile is available only for faculty users.</div>;
  }

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-4xl mx-auto pb-24">
      <motion.section variants={fadeSlideUp} className="border border-white/10 rounded-2xl p-8">
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-white/10 flex items-center justify-center text-2xl text-white">{initials.toUpperCase()}</div>
          <div className="flex-1">
            <h1 className="text-3xl text-white font-display">{user.name}</h1>
            <p className="text-white/50 mt-1">{user.department || "Department"} | Faculty</p>
          </div>
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="px-4 py-2 border border-alert/40 text-alert hover:bg-alert hover:text-white text-xs uppercase tracking-widest"
          >
            <span className="inline-flex items-center gap-2"><LogOut className="w-3 h-3" /> Logout</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
          <div className="border border-white/10 rounded-lg p-4">
            <p className="text-[11px] text-white/40 uppercase">Identity</p>
            <p className="text-white mt-2 inline-flex items-center gap-2"><User className="w-4 h-4" /> {user.employeeId || user.id}</p>
          </div>
          <div className="border border-white/10 rounded-lg p-4">
            <p className="text-[11px] text-white/40 uppercase">Email</p>
            <p className="text-white mt-2 inline-flex items-center gap-2"><Mail className="w-4 h-4" /> {user.email || "Not available"}</p>
          </div>
          <div className="border border-white/10 rounded-lg p-4">
            <p className="text-[11px] text-white/40 uppercase">Role</p>
            <p className="text-brand mt-2 inline-flex items-center gap-2"><Shield className="w-4 h-4" /> {activeRole}</p>
          </div>
          <div className="border border-white/10 rounded-lg p-4">
            <p className="text-[11px] text-white/40 uppercase">Password</p>
            <button
              onClick={() => router.push("/reset-password")}
              className="mt-2 text-white inline-flex items-center gap-2 hover:text-brand"
            >
              <KeyRound className="w-4 h-4" /> Reset via OTP
            </button>
          </div>
        </div>
      </motion.section>
    </motion.div>
  );
}
