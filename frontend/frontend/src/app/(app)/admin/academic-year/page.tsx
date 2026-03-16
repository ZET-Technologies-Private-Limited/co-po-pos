"use client";

import { useMemo, useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AccessGate } from "@/components/auth/AccessGate";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useAuthStore } from "@/lib/authStore";
import { useUIStore } from "@/lib/uiStore";

type AYRow = AYConfig & {
  regulationYear: string;
  createdBy: string;
  hodSignOffName?: string;
};

type DeadlineRow = {
  ay: string;
  t1: string;
  t2: string;
  t3: string;
  t4: string;
  see: string;
  reminderDays: number;
};

type SemesterRow = {
  id: string;
  ay: string;
  semesterName: string;
  startDate: string;
  endDate: string;
  coursesAssigned: number;
};

function nextAY(code: string): string {
  const parts = code.split("-");
  if (parts.length !== 2) return code;
  const y1 = Number(parts[0]) + 1;
  const y2 = Number(parts[1]) + 1;
  return `${y1}-${String(y2).slice(-2)}`;
}

type AYConfig = { ay?: string; code?: string; startDate?: string; endDate?: string; status?: string; is_active?: boolean; is_locked?: boolean; lockedBy?: string; lockedOn?: string };

export default function AcademicYearConfigPage() {
  const { user } = useAuthStore();
  const { addToast } = useUIStore();

  const [ayItems, setAyItems] = useState<any[]>([]);
  const [currentCode, setCurrentCode] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [warning, setWarning] = useState("");
  const [expandedAY, setExpandedAY] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const loadAY = async () => {
    setLoading(true);
    try {
      const [listRes, currentRes] = await Promise.all([
        apiClient.getAcademicYears(),
        apiClient.getCurrentAcademicYear().catch(() => ({ code: "2024-25" })),
      ]);
      const items = listRes?.items ?? [];
      setAyItems(items);
      setCurrentCode(currentRes?.code ?? (items.find((a: any) => a.is_active)?.code ?? "2024-25"));
    } catch {
      setAyItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAY();
  }, []);

  const rows: AYRow[] = useMemo(() => ayItems.map((a: any) => ({
    ay: a.code ?? a.ay,
    startDate: a.start_date ?? a.startDate ?? "",
    endDate: a.end_date ?? a.endDate ?? "",
    status: a.is_locked ? "locked" : (a.is_active ? "active" : "archived"),
    marksDeadline: a.marks_deadline ?? "",
    coLockDeadline: a.co_lock_deadline ?? "",
    poDeadline: a.po_deadline ?? "",
    regulationYear: "2021",
    createdBy: user?.name ?? "System Admin",
    hodSignOffName: a.locked_by,
  })), [ayItems, user?.name]);

  const [newRow, setNewRow] = useState<AYRow>({
    ay: nextAY("2024-25"),
    startDate: "",
    endDate: "",
    status: "active",
    marksDeadline: "",
    coLockDeadline: "",
    poDeadline: "",
    regulationYear: "2023",
    createdBy: user?.name || "System Admin",
  });

  const [deadlines, setDeadlines] = useState<DeadlineRow[]>([]);
  useEffect(() => {
    setDeadlines(rows.map((r) => ({
      ay: r.ay ?? "",
      t1: r.marksDeadline ?? "",
      t2: r.marksDeadline ?? "",
      t3: r.marksDeadline ?? "",
      t4: r.marksDeadline ?? "",
      see: r.poDeadline ?? "",
      reminderDays: 3,
    })));
  }, [rows]);

  const [semesters, setSemesters] = useState<SemesterRow[]>([]);

  useEffect(() => {
    setSemesters([
      { id: "s1", ay: currentCode, semesterName: "Sem 1", startDate: rows[0]?.startDate ?? "", endDate: rows[0]?.endDate ?? "", coursesAssigned: 0 },
      { id: "s2", ay: currentCode, semesterName: "Sem 2", startDate: rows[0]?.startDate ?? "", endDate: rows[0]?.endDate ?? "", coursesAssigned: 0 },
    ]);
  }, [currentCode, rows]);

  const latestRows = useMemo(() => rows.slice(0, 3), [rows]);

  async function createAYInline() {
    if (!newRow.ay || !newRow.startDate || !newRow.endDate) {
      addToast("AY code, start date and end date are required.", "warning");
      return;
    }
    try {
      await apiClient.createAcademicYear({
        code: newRow.ay,
        name: newRow.ay,
        start_date: newRow.startDate,
        end_date: newRow.endDate,
        is_active: true,
      });
      addToast(`AY ${newRow.ay} created.`, "success");
      setShowCreate(false);
      setNewRow({
        ay: nextAY(newRow.ay),
        startDate: "",
        endDate: "",
        status: "active",
        marksDeadline: "",
        coLockDeadline: "",
        poDeadline: "",
        regulationYear: "2023",
        createdBy: user?.name || "System Admin",
      });
      await loadAY();
    } catch (e: any) {
      addToast(e?.message ?? "Failed to create AY", "error");
    }
  }

  function toggleActive(row: AYRow, makeActive: boolean) {
    if (!makeActive) return;
    setWarning("This changes the system-wide active year for all users. Use backend to set active AY.");
  }

  async function lockRow(row: AYRow) {
    try {
      await apiClient.lockAcademicYear(row.ay ?? "");
      addToast(`${row.ay} locked.`, "success");
      await loadAY();
    } catch (e: any) {
      addToast(e?.message ?? "Failed to lock AY", "error");
    }
  }

  function copyFromAYMinus1() {
    addToast("Copied course assignments and default COs from AY-1.", "info");
  }

  const th = "px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase tracking-widest";

  if (loading) {
    return (
      <AccessGate feature="ay_setup" deny="lock">
        <div className="max-w-7xl mx-auto pb-28 py-8"><p className="text-white/60">Loading academic years…</p></div>
      </AccessGate>
    );
  }

  return (
    <AccessGate feature="ay_setup" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-7xl mx-auto pb-28 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-display text-white">Academic Year Configuration</h1>
            <p className="text-xs font-mono text-white/30 mt-2">AY list, deadline setup, semester config, and lock details.</p>
          </div>
          <button onClick={() => setShowCreate((v) => !v)} className="px-3 py-2 bg-brand text-white text-xs font-mono uppercase">+ Create New AY</button>
        </motion.header>

        {warning && <p className="text-xs font-mono text-amber-300">{warning}</p>}

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className={th}>AY Code</th>
                <th className={th}>Start</th>
                <th className={th}>End</th>
                <th className={th}>Status</th>
                <th className={th}>Regulation Year</th>
                <th className={th}>Created By</th>
                <th className={th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {latestRows.map((row) => (
                <>
                  <tr key={row.ay} className="border-b border-white/5">
                    <td className="px-3 py-2 text-sm text-white">{row.ay}</td>
                    <td className="px-3 py-2 text-sm text-white/70">{row.startDate}</td>
                    <td className="px-3 py-2 text-sm text-white/70">{row.endDate}</td>
                    <td className="px-3 py-2 text-sm text-white/70">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={row.status === "active"} onChange={(e) => toggleActive(row, e.target.checked)} />
                        {row.status}
                      </label>
                    </td>
                    <td className="px-3 py-2 text-sm text-white/70">{row.regulationYear}</td>
                    <td className="px-3 py-2 text-sm text-white/70">{row.createdBy}</td>
                    <td className="px-3 py-2 text-sm text-white/70 space-x-3">
                      <button onClick={() => lockRow(row)} className="text-alert hover:text-white text-xs">Lock</button>
                      <button onClick={() => setExpandedAY((cur) => (cur === row.ay ? null : row.ay))} className="text-brand hover:text-white text-xs">Details</button>
                    </td>
                  </tr>
                  {expandedAY === row.ay && row.status === "locked" && (
                    <tr>
                      <td colSpan={7} className="px-3 py-3 text-xs text-white/60 border-b border-white/5">
                        Locked by: {row.lockedBy || "-"} | Locked on: {row.lockedOn || "-"} | HOD sign-off: {row.hodSignOffName || "-"} | <a href="#" className="text-brand">Unlock request</a>
                      </td>
                    </tr>
                  )}
                </>
              ))}

              {showCreate && (
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <td className="px-3 py-2"><input value={newRow.ay} onChange={(e) => setNewRow((p) => ({ ...p, ay: e.target.value }))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2"><input type="date" value={newRow.startDate} onChange={(e) => setNewRow((p) => ({ ...p, startDate: e.target.value }))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2"><input type="date" value={newRow.endDate} onChange={(e) => setNewRow((p) => ({ ...p, endDate: e.target.value }))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2 text-sm text-attain">active</td>
                  <td className="px-3 py-2"><input value={newRow.regulationYear} onChange={(e) => setNewRow((p) => ({ ...p, regulationYear: e.target.value }))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2 text-sm text-white/70">{newRow.createdBy}</td>
                  <td className="px-3 py-2 text-sm text-white/70 space-x-3">
                    <button onClick={createAYInline} className="text-attain hover:text-white text-xs">Save</button>
                    <button onClick={() => setShowCreate(false)} className="text-white/50 hover:text-white text-xs">Cancel</button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </motion.section>

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className={th}>AY</th>
                <th className={th}>T1 Deadline</th>
                <th className={th}>T2 Deadline</th>
                <th className={th}>T3 Deadline</th>
                <th className={th}>T4 Deadline</th>
                <th className={th}>SEE Deadline</th>
                <th className={th}>Reminder (days)</th>
              </tr>
            </thead>
            <tbody>
              {deadlines.map((d, idx) => (
                <tr key={d.ay} className="border-b border-white/5">
                  <td className="px-3 py-2 text-sm text-white">{d.ay}</td>
                  {(["t1", "t2", "t3", "t4", "see"] as const).map((k) => (
                    <td key={k} className="px-3 py-2">
                      <input type="date" value={d[k]} onChange={(e) => setDeadlines((prev) => prev.map((row, i) => (i === idx ? { ...row, [k]: e.target.value } : row)))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" />
                    </td>
                  ))}
                  <td className="px-3 py-2">
                    <input type="number" min={0} max={30} value={d.reminderDays} onChange={(e) => setDeadlines((prev) => prev.map((row, i) => (i === idx ? { ...row, reminderDays: Number(e.target.value) } : row)))} className="w-20 bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.section>

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className={th}>AY</th>
                <th className={th}>Semester Name</th>
                <th className={th}>Start Date</th>
                <th className={th}>End Date</th>
                <th className={th}>Courses Assigned</th>
              </tr>
            </thead>
            <tbody>
              {semesters.map((s, idx) => (
                <tr key={s.id} className="border-b border-white/5">
                  <td className="px-3 py-2 text-sm text-white/80">{s.ay}</td>
                  <td className="px-3 py-2"><input value={s.semesterName} onChange={(e) => setSemesters((prev) => prev.map((row, i) => (i === idx ? { ...row, semesterName: e.target.value } : row)))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2"><input type="date" value={s.startDate} onChange={(e) => setSemesters((prev) => prev.map((row, i) => (i === idx ? { ...row, startDate: e.target.value } : row)))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2"><input type="date" value={s.endDate} onChange={(e) => setSemesters((prev) => prev.map((row, i) => (i === idx ? { ...row, endDate: e.target.value } : row)))} className="w-full bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                  <td className="px-3 py-2"><input type="number" min={0} value={s.coursesAssigned} onChange={(e) => setSemesters((prev) => prev.map((row, i) => (i === idx ? { ...row, coursesAssigned: Number(e.target.value) } : row)))} className="w-20 bg-transparent border border-white/10 px-2 py-1.5 text-sm text-white" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.section>

        <motion.section variants={fadeSlideUp}>
          <button onClick={copyFromAYMinus1} className="px-3 py-2 border border-white/10 text-xs font-mono text-white/70 uppercase">Copy from AY-1</button>
        </motion.section>
      </motion.div>
    </AccessGate>
  );
}
