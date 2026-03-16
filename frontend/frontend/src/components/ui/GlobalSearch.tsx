"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, ArrowRight, X, BookOpen, BarChart3, FileText, Bot, Users, Settings, Plus } from "lucide-react";
import { useUIStore } from "@/lib/uiStore";
import { useRouter } from "next/navigation";

const SEARCH_ITEMS = [
  { label: "Dashboard", icon: BarChart3, href: "/dashboard", desc: "System overview and attainment summary" },
  { label: "New Course", icon: Plus, href: "/faculty/course/new", desc: "Create a new course profile" },
  { label: "Courses", icon: BookOpen, href: "/courses", desc: "Browse and manage all courses" },
  { label: "Analytics", icon: BarChart3, href: "/analytics", desc: "Charts, trends, and department analytics" },
  { label: "Reports", icon: FileText, href: "/reports", desc: "Generate and export CO/PO reports" },
  { label: "AI Assistant", icon: Bot, href: "/chatbot", desc: "Ask questions about attainment data" },
  { label: "User Management", icon: Users, href: "/admin/users", desc: "Create, edit and assign roles to users" },
  { label: "Settings", icon: Settings, href: "/settings", desc: "Configure thresholds and system options" },
  { label: "DBMS — Syllabus", icon: BookOpen, href: "/courses/cs301/syllabus", desc: "CS301 · Upload or edit syllabus" },
  { label: "DBMS — CO Attainment", icon: BarChart3, href: "/courses/cs301/co-attainment", desc: "View CO attainment for CS301" },
  { label: "DBMS — PO Attainment", icon: BarChart3, href: "/courses/cs301/po-attainment", desc: "View PO/PSO attainment for CS301" },
];

export function GlobalSearch() {
  const { searchOpen, closeSearch } = useUIStore();
  const [query, setQuery] = useState("");
  const router = useRouter();
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = SEARCH_ITEMS.filter(s =>
    query.length === 0 || s.label.toLowerCase().includes(query.toLowerCase()) || s.desc.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => { if (searchOpen) { setQuery(""); setSelected(0); setTimeout(() => inputRef.current?.focus(), 50); } }, [searchOpen]);
  useEffect(() => { setSelected(0); }, [query]);

  const go = (href: string) => { router.push(href); closeSearch(); };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!searchOpen) return;
      if (e.key === "ArrowDown") { e.preventDefault(); setSelected(s => Math.min(s + 1, filtered.length - 1)); }
      if (e.key === "ArrowUp") { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); }
      if (e.key === "Enter" && filtered[selected]) go(filtered[selected].href);
      if (e.key === "Escape") closeSearch();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [searchOpen, filtered, selected]);

  return (
    <AnimatePresence>
      {searchOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={closeSearch} className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm" />
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="fixed top-[15vh] left-1/2 -translate-x-1/2 z-[160] w-full max-w-xl bg-[#0D1829] border border-white/10 shadow-2xl"
          >
            {/* Input */}
            <div className="flex items-center gap-4 px-6 py-5 border-b border-white/10">
              <Search className="w-5 h-5 text-white/40 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search pages, courses, features..."
                className="flex-1 bg-transparent text-white text-lg placeholder-white/25 outline-none font-light"
              />
              {query && <button onClick={() => setQuery("")} className="text-white/30 hover:text-white"><X className="w-4 h-4" /></button>}
              <kbd className="hidden sm:block text-xs font-mono text-white/20 border border-white/10 px-2 py-1">ESC</kbd>
            </div>

            {/* Results */}
            <div className="py-2 max-h-[400px] overflow-y-auto">
              {filtered.length === 0 ? (
                <div className="py-8 text-center text-white/30 font-mono text-sm">No results found</div>
              ) : (
                filtered.map((item, i) => (
                  <button key={item.href} onClick={() => go(item.href)}
                    className={`w-full flex items-center gap-4 px-6 py-4 text-left transition-colors ${i === selected ? "bg-white/[0.07]" : "hover:bg-white/[0.04]"}`}>
                    <item.icon className={`w-4 h-4 shrink-0 ${i === selected ? "text-brand" : "text-white/30"}`} />
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${i === selected ? "text-white" : "text-white/70"}`}>{item.label}</p>
                      <p className="text-white/30 text-xs font-light truncate">{item.desc}</p>
                    </div>
                    <ArrowRight className={`w-4 h-4 shrink-0 transition-opacity ${i === selected ? "opacity-60" : "opacity-0"}`} />
                  </button>
                ))
              )}
            </div>

            <div className="px-6 py-3 border-t border-white/5 flex items-center gap-4 text-xs font-mono text-white/20">
              <span>↑↓ navigate</span>
              <span>↵ select</span>
              <span>ESC close</span>
              <span className="ml-auto">Cmd+K</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
