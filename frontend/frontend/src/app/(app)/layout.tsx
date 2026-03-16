"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { AIOrb } from "@/components/ai/AIOrb";
import { DemoPanel } from "@/components/demo/DemoPanel";
import { ToastContainer } from "@/components/ui/ToastContainer";
import { NotificationsPanel } from "@/components/ui/NotificationsPanel";
import { GlobalSearch } from "@/components/ui/GlobalSearch";
import { ProfileMenu } from "@/components/ui/ProfileMenu";
import { SessionTimeoutModal } from "@/components/ui/SessionTimeoutModal";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useUIStore } from "@/lib/uiStore";
import { useAuthStore, Role } from "@/lib/authStore";
import {
  LayoutDashboard, BookOpen, BarChart3, FileText, Bot, Users, Settings,
  Bell, Search, Layers, Lock, Menu, X, ChevronDown, MessageSquare, TrendingUp
} from "lucide-react";

const Clock = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
);

const ROLE_NAV_CONFIG: Record<Role, { href: string; label: string; icon: any }[]> = {
  admin: [
    { href: "/admin/dashboard",     label: "System Hub",   icon: LayoutDashboard },
    { href: "/admin/users",          label: "Users",        icon: Users },
    { href: "/admin/academic-year",  label: "AY Config",    icon: Settings },
    { href: "/admin/thresholds",     label: "Thresholds",   icon: BarChart3 },
    { href: "/admin/co-library",     label: "CO Library",   icon: BookOpen },
    { href: "/admin/po-pso",         label: "PO / PSO",     icon: Layers },
    { href: "/admin/audit-log",      label: "Audit Trail",  icon: FileText },
  ],
  department_head: [
    { href: "/dashboard",            label: "Dept Hub",     icon: LayoutDashboard },
    { href: "/hod/co-attainment",    label: "CO Attainment",icon: BarChart3 },
    { href: "/hod/po-pso-attainment",label: "PO/PSO",       icon: Layers },
    { href: "/hod/ay-history",       label: "AY History",   icon: Clock },
    { href: "/co-library",           label: "CO Library",   icon: BookOpen },
    { href: "/co-po-matrix",         label: "CO-PO Matrix", icon: Layers },
    { href: "/audit-trail",          label: "Audit Trail",  icon: FileText },
    { href: "/hod/department-report",label: "Dept Report",  icon: FileText },
    { href: "/hod/thresholds",       label: "Thresholds",   icon: Settings },
    { href: "/hod/year-end-lock",    label: "Sign-Off",     icon: Lock },
  ],
  subject_lead: [
    { href: "/dashboard",            label: "Hub",          icon: LayoutDashboard },
    { href: "/lead/dashboard",       label: "Lead Dashboard", icon: LayoutDashboard },
    { href: "/lead/marks-approval",  label: "Queue",        icon: BookOpen },
    { href: "/lead/co-attainment",   label: "CO Tracking",  icon: BarChart3 },
    { href: "/lead/po-attainment",   label: "PO Tracking",  icon: Layers },
    { href: "/lead/ay-comparison",   label: "AY Compare",   icon: TrendingUp },
    { href: "/lead/reports",         label: "Reports",      icon: FileText },
    { href: "/co-library",           label: "CO Library",   icon: BookOpen },
    { href: "/co-po-matrix",         label: "CO-PO Matrix", icon: Layers },
    { href: "/low-co-alerts",        label: "Alerts",       icon: Bell },
    { href: "/lead/remedial-actions",label: "Remedial",     icon: FileText },
    { href: "/audit-trail",          label: "Audit Trail",  icon: FileText },
  ],
  faculty: [
    { href: "/faculty/dashboard",    label: "My Hub",       icon: LayoutDashboard },
    { href: "/co-library",           label: "CO Library",   icon: BookOpen },
    { href: "/co-po-matrix",         label: "CO-PO Matrix", icon: Layers },
    { href: "/low-co-alerts",        label: "Alerts",       icon: Bell },
    { href: "/reports",              label: "Reports",      icon: FileText },
    { href: "/faculty/profile",      label: "Profile",      icon: Settings },
    { href: "#",                    label: "Chat",         icon: MessageSquare },
  ],
  student: [
    { href: "/student/dashboard",    label: "My Hub",       icon: LayoutDashboard },
    { href: "/student/courses",      label: "My Courses",   icon: BookOpen },
    { href: "/student/marks",        label: "My Marks",     icon: FileText },
    { href: "/student/grievance",    label: "Grievances",   icon: MessageSquare },
  ],
};

const AY_OPTIONS = ["2025-26", "2024-25", "2023-24", "2022-23"];

function GlobalKeyBindings() {
  const { openSearch } = useUIStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      const inInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      if (inInput) return;

      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); openSearch(); return; }
      if (e.key === "/") { e.preventDefault(); openSearch(); return; }
      // S = save: dispatch custom event that form pages can listen to
      if (e.key === "s" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); window.dispatchEvent(new CustomEvent("kb:save")); return; }
      // N = new: dispatch custom event
      if (e.key === "n") { e.preventDefault(); window.dispatchEvent(new CustomEvent("kb:new")); return; }
      // Escape handled per-modal
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [openSearch]);

  return null;
}

const ROLE_HOME: Record<string, string> = {
  admin: "/admin/dashboard",
  department_head: "/dashboard",
  subject_lead: "/dashboard",
  faculty: "/faculty/dashboard",
  student: "/student/dashboard",
};

// Pages that manage their own layout (no outer padding)
const FULL_BLEED_PREFIXES = [
  "/faculty/course/",
  "/hod/",
  "/dashboard",
];

// Pages that render completely standalone — no header, no nav shell
const STANDALONE_PATHS = [
  "/faculty/course/new",
];

function AppContent({ pathname, children }: { pathname: string; children: React.ReactNode }) {
  const isFullBleed = FULL_BLEED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (isFullBleed) return <>{children}</>;
  return <div className="px-4 md:px-8 py-8">{children}</div>;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { openNotif, notifications, openSearch, profileMenuOpen, openProfileMenu, closeProfileMenu, darkMode, openChat } = useUIStore();
  const { activeRole, user, activeAY, setActiveAY, setActiveRole, isAuthenticated } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const unread = notifications.filter(n => !n.read).length;
  const isReadOnlyAY = activeAY !== AY_OPTIONS[0];

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, router]);

  // Initialize activeRole from user.roles if null (handles hydration issues)
  useEffect(() => {
    if (!activeRole && user?.roles && user.roles.length > 0) {
      setActiveRole(user.roles[0] as any);
    }
  }, [activeRole, user, setActiveRole]);

  // Close mobile nav on route change
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const ayFromUrl = new URLSearchParams(window.location.search).get("ay");
    if (ayFromUrl && AY_OPTIONS.includes(ayFromUrl) && ayFromUrl !== activeAY) {
      setActiveAY(ayFromUrl);
    }
  }, [activeAY, setActiveAY]);

  useEffect(() => {
    if (!mobileOpen) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [mobileOpen]);

  useEffect(() => {
    if (!mobileOpen) {
      document.body.style.overflow = "";
      return;
    }
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  // Apply dark mode class to html
  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const navItems = (activeRole && ROLE_NAV_CONFIG[activeRole]) ? ROLE_NAV_CONFIG[activeRole] : ROLE_NAV_CONFIG["faculty"];

  const handleAYChange = (ay: string) => {
    setActiveAY(ay);
    const params = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
    params.set("ay", ay);
    router.replace(`${pathname}?${params.toString()}`);
    router.refresh();
  };

  // Standalone pages bypass the entire shell
  if (STANDALONE_PATHS.some((p) => pathname === p || pathname.startsWith(p + "?")))
    return (
      <div className={`min-h-screen bg-cosmic text-white ${darkMode ? "" : "brightness-110"}`}>
        <ToastContainer />
        <SessionTimeoutModal />
        {children}
      </div>
    );

  return (
    <div className={`min-h-screen bg-cosmic text-white flex flex-col ${darkMode ? "" : "brightness-110"}`}>
      <GlobalKeyBindings />
      <AIOrb />
      <DemoPanel />
      <ToastContainer />
      <NotificationsPanel />
      <GlobalSearch />
      <SessionTimeoutModal />

      {/* ── TOP NAVIGATION ── */}
      <header
        role="banner"
        className="sticky top-0 z-40 bg-cosmic/95 backdrop-blur-xl border-b border-white/5 h-16 flex items-center px-4 md:px-8 justify-between print:hidden"
      >
        {/* Logo + Portal name */}
        <div className="flex items-center gap-3">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(v => !v)}
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            className="md:hidden p-2 text-white/40 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-brand rounded"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <Link href="/dashboard" aria-label="Nexus Engine — Home" className="font-display font-bold text-xl tracking-wide flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-aurora flex items-center justify-center" aria-hidden="true">
              <span className="text-white text-xs font-bold">N</span>
            </div>
            <span className="hidden sm:inline">Nexus<span className="text-white/40">Engine</span></span>
          </Link>

          {/* AY Selector */}
          <div className="relative ml-2">
            <label htmlFor="ay-select" className="sr-only">Academic Year</label>
            <div className="flex items-center gap-1 px-3 py-1.5 border border-white/10 hover:border-white/30 transition-colors cursor-pointer rounded">
              <select
                id="ay-select"
                value={activeAY}
                onChange={e => handleAYChange(e.target.value)}
                aria-label="Select Academic Year"
                className="bg-transparent text-white/70 text-xs font-mono outline-none cursor-pointer appearance-none pr-4"
              >
                {AY_OPTIONS.map((ay, i) => (
                  <option key={ay} value={ay} className="bg-[#0D1829]">
                    {i === 0 ? `AY ${ay} (Current)` : `AY ${ay}`}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-white/30 pointer-events-none absolute right-2" aria-hidden="true" />
            </div>
          </div>
          {/* Read-only badge for past AYs */}
          {isReadOnlyAY && (
            <span className="hidden sm:flex items-center gap-1 px-2 py-1 bg-alert/10 border border-alert/30 text-alert text-[9px] font-mono uppercase tracking-widest rounded" aria-live="polite">
              <Lock className="w-2.5 h-2.5" aria-hidden="true" /> Read-only
            </span>
          )}
        </div>

        {/* Desktop nav */}
        <nav aria-label="Main navigation" className="hidden md:flex gap-0 text-[11px] font-mono flex-1 ml-4 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          {navItems.map(item => (
            item.href === "#" ? (
              <button
                key="chat"
                type="button"
                onClick={openChat}
                className="flex items-center gap-1 px-2 py-5 transition-colors border-b-2 uppercase tracking-wider whitespace-nowrap shrink text-white/50 hover:text-white border-transparent hover:border-white/30 focus:outline-none focus:ring-2 focus:ring-brand rounded-none"
              >
                <item.icon className="w-3 h-3 shrink-0 hidden lg:block" aria-hidden="true" />
                {item.label}
              </button>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                aria-current={pathname === item.href ? "page" : undefined}
                className={`flex items-center gap-1 px-2 py-5 transition-colors border-b-2 uppercase tracking-wider whitespace-nowrap shrink ${
                  pathname === item.href
                    ? "text-white border-brand"
                    : "text-white/50 hover:text-white border-transparent hover:border-white/30"
                }`}
              >
                <item.icon className="w-3 h-3 shrink-0 hidden lg:block" aria-hidden="true" />
                {item.label}
              </Link>
            )
          ))}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-1 ml-2">
          {/* Search */}
          <button
            onClick={openSearch}
            aria-label="Open search (/ or Cmd+K)"
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 border border-white/10 text-white/30 hover:text-white hover:border-white/30 transition-colors font-mono text-xs focus:outline-none focus:ring-2 focus:ring-brand rounded"
          >
            <Search className="w-3 h-3" aria-hidden="true" />
            <span>Search</span>
            <kbd className="text-[9px] border border-white/10 px-1.5 py-0.5" aria-label="Keyboard shortcut: slash">/</kbd>
          </button>
          <button
            onClick={openSearch}
            aria-label="Open search"
            className="sm:hidden p-2 text-white/40 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-brand rounded"
          >
            <Search className="w-5 h-5" aria-hidden="true" />
          </button>

          {/* Notification bell */}
          <button
            onClick={openNotif}
            aria-label={`Notifications${unread > 0 ? `, ${unread} unread` : ""}`}
            className="relative p-2 text-white/40 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-brand rounded"
          >
            <Bell className="w-5 h-5" aria-hidden="true" />
            {unread > 0 && (
              <span
                aria-hidden="true"
                className="absolute top-1 right-1 min-w-[16px] h-4 rounded-full bg-brand flex items-center justify-center text-[9px] text-white font-mono px-1"
              >
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>

          {/* Profile avatar */}
          <div className="relative ml-1">
            <button
              onClick={() => profileMenuOpen ? closeProfileMenu() : openProfileMenu()}
              aria-label="Open profile menu"
              aria-haspopup="menu"
              aria-expanded={profileMenuOpen}
              className="flex items-center gap-2 pl-2 pr-1 py-1 hover:bg-white/5 transition-colors rounded focus:outline-none focus:ring-2 focus:ring-brand"
            >
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-medium text-white leading-tight">{user?.name?.split(" ")[0] || "User"}</span>
                <span className="text-[9px] font-mono uppercase tracking-widest text-brand leading-tight">{activeRole?.replace("_", " ")}</span>
              </div>
              <div
                className="w-8 h-8 rounded bg-gradient-to-br from-brand/40 to-aurora/40 border border-white/10 flex items-center justify-center text-white text-sm font-display"
                aria-hidden="true"
              >
                {user?.name?.[0] || "?"}
              </div>
            </button>
            <ProfileMenu />
          </div>
        </div>
      </header>

      {isReadOnlyAY && (
        <div className="print:hidden border-b border-alert/15 bg-alert/5 px-4 py-2 md:px-8">
          <p className="text-[10px] font-mono uppercase tracking-widest text-alert/80">
            Read-only mode for AY {activeAY}. Switch to AY {AY_OPTIONS[0]} to edit records, upload marks, or submit approvals.
          </p>
        </div>
      )}

      {/* ── MOBILE SIDEBAR ── */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 top-16 z-30 flex print:hidden"
        >
          <button
            aria-label="Close mobile navigation"
            className="absolute inset-0 bg-black/55"
            onClick={() => setMobileOpen(false)}
          />
          <div
            id="mobile-nav"
            role="navigation"
            aria-label="Mobile navigation"
            className="relative z-10 h-full w-[min(86vw,22rem)] border-r border-white/10 bg-cosmic/98 backdrop-blur-xl"
          >
            <nav className="flex h-full flex-col overflow-y-auto py-4">
              {navItems.map(item => (
                item.href === "#" ? (
                  <button
                    key="chat"
                    type="button"
                    onClick={() => { openChat(); setMobileOpen(false); }}
                    className="flex items-center gap-3 px-6 py-4 text-sm font-mono uppercase tracking-widest transition-colors border-l-2 text-white/50 border-transparent hover:text-white hover:bg-white/5 text-left w-full"
                  >
                    <item.icon className="w-4 h-4" aria-hidden="true" />
                    {item.label}
                  </button>
                ) : (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={pathname === item.href ? "page" : undefined}
                    className={`flex items-center gap-3 px-6 py-4 text-sm font-mono uppercase tracking-widest transition-colors border-l-2 ${
                      pathname === item.href
                        ? "text-white border-brand bg-white/5"
                        : "text-white/50 border-transparent hover:text-white hover:bg-white/5"
                    }`}
                  >
                    <item.icon className="w-4 h-4" aria-hidden="true" />
                    {item.label}
                  </Link>
                )
              ))}
            </nav>
          </div>
        </div>
      )}

      {/* ── MAIN CONTENT ── */}
      <main id="main-content" role="main" className="flex-1 w-full">
        <ErrorBoundary>
          <AppContent pathname={pathname}>{children}</AppContent>
        </ErrorBoundary>
      </main>

      {/* ── PRINT STYLES ── */}
      <style jsx global>{`
        @media print {
          header, nav, .print\\:hidden { display: none !important; }
          main { padding: 0 !important; }
          body { background: white !important; color: black !important; }
        }
      `}</style>
    </div>
  );
}
