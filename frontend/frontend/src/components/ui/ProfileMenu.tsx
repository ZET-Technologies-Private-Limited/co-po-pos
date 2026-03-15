"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useUIStore } from "@/lib/uiStore";
import { useAuthStore, Role } from "@/lib/authStore";
import { useRouter } from "next/navigation";
import { User, Settings, LogOut, Sun, Moon, Globe, RefreshCw, Building2, Shield } from "lucide-react";

const LANG_OPTIONS = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "ta", label: "தமிழ்" },
  { code: "te", label: "తెలుగు" },
] as const;

const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrator",
  department_head: "Dept. Head",
  subject_lead: "Subject Lead",
  faculty: "Faculty",
  student: "Student",
};

const ROLE_HOME: Record<Role, string> = {
  admin: "/dashboard",
  department_head: "/dashboard",
  subject_lead: "/dashboard",
  faculty: "/faculty/dashboard",
  student: "/student/dashboard",
};

export function ProfileMenu() {
  const { profileMenuOpen, closeProfileMenu, darkMode, toggleDarkMode, language, setLanguage, addToast } = useUIStore();
  const { user, activeRole, setActiveRole, logout } = useAuthStore();
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!profileMenuOpen) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) closeProfileMenu();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [profileMenuOpen, closeProfileMenu]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") closeProfileMenu(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [closeProfileMenu]);

  function navigate(href: string) { closeProfileMenu(); router.push(href); }
  function handleLogout() { closeProfileMenu(); logout(); router.push("/login"); }
  function handleRoleSwitch(role: Role) {
    if (role === activeRole) {
      closeProfileMenu();
      return;
    }
    setActiveRole(role);
    closeProfileMenu();
    addToast(`Role switched to ${ROLE_LABELS[role]}.`, "success");
    router.push(ROLE_HOME[role]);
    router.refresh();
  }

  const dualRoles = user?.roles && user.roles.length > 1;

  return (
    <AnimatePresence>
      {profileMenuOpen && (
        <motion.div
          ref={ref}
          role="menu"
          aria-label="Profile menu"
          initial={{ opacity: 0, y: -8, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.97 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          className="absolute right-0 top-full mt-2 w-72 bg-[#0D1829] border border-white/10 shadow-2xl z-[200] flex flex-col"
        >
          {/* Identity */}
          <div className="px-5 py-4 border-b border-white/10">
            <p className="text-white font-medium text-sm">{user?.name || "Anonymous"}</p>
            <div className="flex items-center gap-2 mt-1">
              <Shield className="w-3 h-3 text-brand" aria-hidden="true" />
              <span className="text-[10px] font-mono text-brand uppercase tracking-widest">{activeRole ? ROLE_LABELS[activeRole] : "—"}</span>
            </div>
            {user?.department && (
              <div className="flex items-center gap-2 mt-1">
                <Building2 className="w-3 h-3 text-white/30" aria-hidden="true" />
                <span className="text-[10px] font-mono text-white/40">{user.department}</span>
              </div>
            )}
          </div>

          {/* Nav items */}
          <div className="py-1">
            <button
              role="menuitem"
              onClick={() =>
                navigate(activeRole === "faculty" ? "/faculty/profile" : "/profile")
              }
              className="w-full flex items-center gap-3 px-5 py-3 text-sm text-white/70 hover:text-white hover:bg-white/5 transition-colors focus:outline-none focus:bg-white/5"
            >
              <User className="w-4 h-4" aria-hidden="true" /> My Profile
            </button>
            <button role="menuitem" onClick={() => navigate("/settings")} className="w-full flex items-center gap-3 px-5 py-3 text-sm text-white/70 hover:text-white hover:bg-white/5 transition-colors focus:outline-none focus:bg-white/5">
              <Settings className="w-4 h-4" aria-hidden="true" /> Settings
            </button>

            {/* Switch Role */}
            {dualRoles && (
              <div className="px-5 py-3 border-t border-white/5">
                <div className="flex items-center gap-2 mb-2">
                  <RefreshCw className="w-3 h-3 text-white/30" aria-hidden="true" />
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Switch Role</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {user!.roles.map(r => (
                    <button
                      key={r}
                      role="menuitem"
                      onClick={() => handleRoleSwitch(r)}
                      className={`px-2 py-1 text-[10px] font-mono uppercase tracking-widest border transition-colors focus:outline-none focus:ring-1 focus:ring-brand ${activeRole === r ? "border-brand text-brand bg-brand/10" : "border-white/10 text-white/40 hover:border-white/30 hover:text-white"}`}
                    >
                      {ROLE_LABELS[r]}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Dark mode + Language */}
          <div className="border-t border-white/10 px-5 py-3 flex flex-col gap-3">
            {/* Dark mode */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-white/60">
                {darkMode ? <Moon className="w-4 h-4" aria-hidden="true" /> : <Sun className="w-4 h-4" aria-hidden="true" />}
                <span>{darkMode ? "Dark Mode" : "Light Mode"}</span>
              </div>
              <button
                role="switch"
                aria-checked={darkMode}
                aria-label="Toggle dark mode"
                onClick={toggleDarkMode}
                className={`w-10 h-5 rounded-full transition-colors relative focus:outline-none focus:ring-2 focus:ring-brand ${darkMode ? "bg-brand" : "bg-white/20"}`}
              >
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${darkMode ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
            </div>

            {/* Language */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-white/60">
                <Globe className="w-4 h-4" aria-hidden="true" />
                <span>Language</span>
              </div>
              <select
                value={language}
                onChange={e => setLanguage(e.target.value as any)}
                aria-label="Select language"
                className="bg-transparent text-white/60 text-xs font-mono border border-white/10 px-2 py-1 outline-none hover:border-white/30 transition-colors cursor-pointer focus:ring-1 focus:ring-brand"
              >
                {LANG_OPTIONS.map(l => (
                  <option key={l.code} value={l.code} className="bg-[#0D1829]">{l.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Logout */}
          <div className="border-t border-white/10 py-1">
            <button
              role="menuitem"
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-5 py-3 text-sm text-alert/70 hover:text-alert hover:bg-alert/5 transition-colors focus:outline-none focus:bg-alert/5"
            >
              <LogOut className="w-4 h-4" aria-hidden="true" /> Logout
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
