"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { CheckCircle2, ShieldAlert } from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { useUIStore } from "@/lib/uiStore";

const BLOOM_LEVELS_DEFAULT = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"];

export default function SettingsPage() {
  const { activeRole, setActiveRole } = useAuthStore();
  const { addToast } = useUIStore();
  const [threshold, setThreshold] = useState(60);
  const [deptInput, setDeptInput] = useState("");
  const [depts, setDepts] = useState<string[]>([]);
  const [bloomLevels] = useState(BLOOM_LEVELS_DEFAULT);
  const [yearInput, setYearInput] = useState("");
  const [academicYears, setAcademicYears] = useState<string[]>([]);
  const [programInput, setProgramInput] = useState("");
  const [programs, setPrograms] = useState<{ id: string; code: string; name: string }[]>([]);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ayRes, progRes, threshRes] = await Promise.all([
        apiClient.getAcademicYears().catch(() => ({ items: [] })),
        apiClient.getPrograms().catch(() => []),
        apiClient.getThresholds().catch(() => ({ level2: 0.6, level3: 0.7 })),
      ]);
      const ayList = Array.isArray(ayRes?.items) ? ayRes.items : Array.isArray(ayRes) ? ayRes : [];
      setAcademicYears(ayList.map((a: any) => a.code ?? a.ay ?? "").filter(Boolean));
      setPrograms(Array.isArray(progRes) ? progRes : []);
      setThreshold(Math.round((threshRes?.level2 ?? 0.6) * 100));
      // Derive depts from programs
      const deptSet = new Set<string>();
      (Array.isArray(progRes) ? progRes : []).forEach((p: any) => { if (p.department) deptSet.add(p.department); });
      if (deptSet.size === 0) setDepts(["CSE", "ECE", "MECH", "CIVIL", "IT"]);
      else setDepts([...deptSet]);
    } catch {
      setDepts(["CSE", "ECE", "MECH", "CIVIL", "IT"]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const saveAll = async () => {
    try {
      await apiClient.setThresholds({ level2: threshold / 100, level3: (threshold + 10) / 100 });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      addToast(e?.message ?? "Failed to save settings", "error");
    }
  };

  const addDept = () => { if (deptInput.trim()) { setDepts(prev => [...prev, deptInput.trim()]); setDeptInput(""); } };
  const removeDept = (d: string) => setDepts(prev => prev.filter(x => x !== d));

  const addYear = async () => {
    if (!yearInput.trim()) return;
    try {
      await apiClient.createAcademicYear({ code: yearInput.trim(), name: yearInput.trim(), start_date: "", end_date: "", is_active: false });
      setYearInput("");
      await load();
    } catch (e: any) {
      addToast(e?.message ?? "Failed to create AY", "error");
    }
  };
  const removeYear = (y: string) => setAcademicYears(prev => prev.filter(x => x !== y));

  const addProgram = () => { if (programInput.trim()) { addToast("Programs must be created via the database.", "info"); setProgramInput(""); } };
  const removeProgram = (p: string) => setPrograms(prev => prev.filter(x => x.id !== p));

  if (loading) return <div className="max-w-3xl mx-auto px-6 pt-12"><p className="text-white/60">Loading settings...</p></div>;

  if (activeRole !== "admin") {
    return (
      <div className="w-full min-h-[60vh] flex flex-col items-center justify-center p-8 text-center">
        <ShieldAlert className="w-16 h-16 text-alert mb-6" />
        <h2 className="text-3xl font-display text-white mb-4">Access Restricted</h2>
        <p className="text-white/40 font-light max-w-md">System Architecture and Configuration is strictly limited to System Administrators to ensure referential integrity.</p>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen pb-24">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-3xl mx-auto px-6 pt-12">

        <motion.div variants={fadeSlideUp} className="mb-16">
          <div className="flex items-center gap-3 text-sm font-mono text-white/40 uppercase tracking-widest mb-4">
            <span className="w-8 h-[1px] bg-white/20"></span>
            System
          </div>
          <h1 className="text-5xl font-display text-white">Settings</h1>
        </motion.div>

        {/* Attainment Threshold */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Attainment Threshold</h2>
          <p className="text-white/50 font-light mb-8">COs below this percentage will be flagged as at-risk.</p>
          <div className="flex items-center gap-8">
            <input type="range" min={40} max={80} value={threshold} onChange={e => setThreshold(+e.target.value)}
              className="flex-1 accent-brand h-1 bg-white/10" />
            <span className="text-5xl font-mono font-light text-white w-24 text-right">{threshold}<span className="text-xl text-white/40">%</span></span>
          </div>
          <div className="flex justify-between text-xs font-mono text-white/30 mt-3">
            <span>40% (Lenient)</span>
            <span>60% (Standard)</span>
            <span>80% (Strict)</span>
          </div>
        </motion.div>

        {/* Bloom Taxonomy Levels */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Bloom's Taxonomy Levels</h2>
          <p className="text-white/50 font-light mb-8">Reorder or rename the cognitive levels used for CO classification.</p>
          <div className="flex flex-col gap-3">
            {bloomLevels.map((level, i) => (
              <div key={level} className="flex items-center gap-4 py-3 border-b border-white/5 group">
                <span className="font-mono text-white/20 text-sm w-6">{i + 1}</span>
                <span className="flex-1 text-white/70 font-light">{level}</span>
                <div className={`w-2 h-2 rounded-full ${i < 2 ? "bg-white/30" : i < 4 ? "bg-aurora" : "bg-brand"}`} />
              </div>
            ))}
          </div>
        </motion.div>

        {/* Academic Years */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Academic Years</h2>
          <p className="text-white/50 font-light mb-8">Define the active catalog of academic sessions.</p>
          <div className="flex flex-col gap-3 mb-6">
            {academicYears.map(y => (
              <div key={y} className="flex items-center justify-between py-3 border-b border-white/5 group">
                <span className="text-white/70">{y}</span>
                <button onClick={() => removeYear(y)} className="text-white/20 hover:text-alert transition-colors opacity-0 group-hover:opacity-100 text-sm font-mono">Remove</button>
              </div>
            ))}
          </div>
          <div className="flex gap-4">
            <input value={yearInput} onChange={e => setYearInput(e.target.value)} onKeyDown={e => e.key === "Enter" && void addYear()}
              placeholder="e.g. 2026-27"
              className="flex-1 bg-transparent border-b border-white/20 focus:border-white text-white placeholder-white/30 outline-none py-2 transition-colors" />
            <button onClick={() => void addYear()} className="px-4 py-2 border border-white/20 text-white text-sm font-mono hover:border-white transition-colors">Add</button>
          </div>
        </motion.div>

        {/* Programs */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Academic Programs</h2>
          <p className="text-white/50 font-light mb-8">Configure the degree programs tracked within the system.</p>
          <div className="flex flex-col gap-3 mb-6">
            {programs.map(p => (
              <div key={p.id} className="flex items-center justify-between py-3 border-b border-white/5 group">
                <span className="text-white/70">{p.code} — {p.name}</span>
                <button onClick={() => removeProgram(p.id)} className="text-white/20 hover:text-alert transition-colors opacity-0 group-hover:opacity-100 text-sm font-mono">Remove</button>
              </div>
            ))}
            {programs.length === 0 && <p className="text-white/30 text-sm">No programs found. Create programs via the database.</p>}
          </div>
          <div className="flex gap-4">
            <input value={programInput} onChange={e => setProgramInput(e.target.value)} onKeyDown={e => e.key === "Enter" && addProgram()}
              placeholder="New program (e.g. B.Tech IT)"
              className="flex-1 bg-transparent border-b border-white/20 focus:border-white text-white placeholder-white/30 outline-none py-2 transition-colors" />
            <button onClick={addProgram} className="px-4 py-2 border border-white/20 text-white text-sm font-mono hover:border-white transition-colors">Add</button>
          </div>
        </motion.div>

        {/* Departments */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Departments</h2>
          <p className="text-white/50 font-light mb-8">Configure the list of departments used throughout the system.</p>
          <div className="flex flex-col gap-3 mb-6">
            {depts.map(d => (
              <div key={d} className="flex items-center justify-between py-3 border-b border-white/5 group">
                <span className="text-white/70">{d}</span>
                <button onClick={() => removeDept(d)} className="text-white/20 hover:text-alert transition-colors opacity-0 group-hover:opacity-100 text-sm font-mono">Remove</button>
              </div>
            ))}
          </div>
          <div className="flex gap-4">
            <input value={deptInput} onChange={e => setDeptInput(e.target.value)} onKeyDown={e => e.key === "Enter" && addDept()}
              placeholder="New department name..."
              className="flex-1 bg-transparent border-b border-white/20 focus:border-white text-white placeholder-white/30 outline-none py-2 transition-colors" />
            <button onClick={addDept} className="px-4 py-2 border border-white/20 text-white text-sm font-mono hover:border-white transition-colors">Add</button>
          </div>
        </motion.div>



        {/* Security & Access */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Security & Integrity</h2>
          <p className="text-white/50 font-light mb-8">Manage workspace authentication and session protocols.</p>
          <div className="flex flex-col gap-8">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Multi-Factor Authentication</p>
                <p className="text-xs text-white/30 truncate max-w-[200px] md:max-w-none">Require biometric or OTP verification for all faculty.</p>
              </div>
              <button className="w-12 h-6 rounded-full bg-white/5 border border-white/10 p-1 flex items-center justify-start group hover:border-white/30 transition-all">
                <div className="w-4 h-4 rounded-full bg-white/20 group-hover:bg-white/40 transition-colors" />
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">Institutional Single Sign-On (SSO)</p>
                <p className="text-xs text-white/30">Connect with LDAP/Active Directory.</p>
              </div>
              <span className="text-[10px] font-mono text-white/20 border border-white/10 px-2 py-0.5 rounded uppercase">Configure</span>
            </div>
          </div>
        </motion.div>

        {/* Notifications */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-2">Synchronized Notifications</h2>
          <p className="text-white/50 font-light mb-8">Define how Nexus AI communicates with stakeholders.</p>
          <div className="grid grid-cols-2 gap-8">
            {["Attainment Alerts", "Exam Reminders", "AI Mapping Suggestions", "Student Deficit Reports"].map(n => (
              <div key={n} className="flex items-center justify-between py-4 border-b border-white/5">
                <span className="text-sm text-white/60">{n}</span>
                <input type="checkbox" defaultChecked className="accent-brand" />
              </div>
            ))}
          </div>
        </motion.div>

        {/* Advanced / Role Simulation */}
        <motion.div variants={fadeSlideUp} className="pb-12 mb-12 border-b border-white/10">
          <h2 className="text-2xl font-display text-white mb-4 italic text-white/40">Nexus Sandbox Experiments</h2>
          <div className="flex items-center justify-between bg-white/[0.02] p-8 border border-white/5">
            <div>
              <p className="text-white font-medium">Environment Simulation</p>
              <p className="text-xs text-white/30 mt-1">Preview the dashboard as a different user role to verify visibility.</p>
            </div>
            <select 
              value={activeRole || ""}
              onChange={(e) => setActiveRole(e.target.value as any)}
              className="bg-transparent text-white font-mono text-[10px] uppercase tracking-widest border border-white/20 px-4 py-2 outline-none cursor-pointer hover:border-white transition-colors"
            >
               <option value="admin" className="bg-cosmic">Active: Administrator</option>
               <option value="department_head" className="bg-cosmic">Department Head View</option>
               <option value="subject_lead" className="bg-cosmic">Subject Lead View</option>
               <option value="faculty" className="bg-cosmic">Faculty View</option>
            </select>
          </div>
        </motion.div>

        {/* Save */}
        <motion.div variants={fadeSlideUp}>
          <button onClick={() => void saveAll()} className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm hover:bg-white/90 transition-colors">
            {saved ? <><CheckCircle2 className="w-4 h-4 text-attain" /> Saved Successfully</> : "Save All Settings"}
          </button>
        </motion.div>
      </motion.div>
    </div>
  );
}
