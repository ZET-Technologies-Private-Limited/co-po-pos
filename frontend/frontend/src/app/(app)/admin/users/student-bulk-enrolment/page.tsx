"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { AccessGate } from "@/components/auth/AccessGate";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useUIStore } from "@/lib/uiStore";

type EnrolError = { row: number; error: string };

type EnrolRow = {
  rollNo: string;
  name: string;
  email: string;
  courseCodes: string[];
};

function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      quoted = !quoted;
      continue;
    }
    if (ch === "," && !quoted) {
      out.push(cur.trim());
      cur = "";
      continue;
    }
    cur += ch;
  }
  out.push(cur.trim());
  return out;
}

export default function StudentBulkEnrolmentPage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useUIStore();

  const [rows, setRows] = useState<EnrolRow[]>([]);
  const [errors, setErrors] = useState<EnrolError[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const c = await apiClient.getCourses().catch(() => []);
      setCourses(Array.isArray(c) ? c : c?.items ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const courseCodes = useMemo(() => new Set(courses.map((c: any) => (c.course_code ?? c.code ?? "").toLowerCase()).filter(Boolean)), [courses]);

  function downloadTemplate() {
    const csv = [
      "Roll No,Name,Email,Course Codes",
      "21CS301,Arun Kumar,arun@college.edu,CS301,CS401",
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "student_bulk_enrolment_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  function parseFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || "");
      const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
      if (lines.length < 2) {
        setRows([]);
        setErrors([{ row: 1, error: "CSV must include data rows." }]);
        return;
      }

      const parsed: EnrolRow[] = [];
      const errs: EnrolError[] = [];
      const seenRolls = new Set<string>();

      for (let i = 1; i < lines.length; i += 1) {
        const row = parseCsvLine(lines[i]);
        const rowNo = i + 1;
        const rollNo = (row[0] || "").trim();
        const name = (row[1] || "").trim();
        const email = (row[2] || "").trim();
        const codes = row.slice(3).join(",").split(",").map((c) => c.trim()).filter(Boolean);

        if (!rollNo || !name || !email || codes.length === 0) {
          errs.push({ row: rowNo, error: "Missing required fields" });
          continue;
        }
        if (seenRolls.has(rollNo.toLowerCase())) {
          errs.push({ row: rowNo, error: `Duplicate roll number: ${rollNo}` });
          continue;
        }
        seenRolls.add(rollNo.toLowerCase());

        const invalidCodes = codes.filter((c) => !courseCodes.has(c.toLowerCase()));
        if (invalidCodes.length > 0) {
          errs.push({ row: rowNo, error: `Invalid course code(s): ${invalidCodes.join(", ")}` });
          continue;
        }

        parsed.push({ rollNo, name, email, courseCodes: codes });
      }

      setRows(parsed);
      setErrors(errs);
    };
    reader.readAsText(file);
  }

  const [enrolling, setEnrolling] = useState(false);

  async function confirmEnrolment() {
    setEnrolling(true);
    let success = 0;
    const errs: EnrolError[] = [];
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      try {
        await apiClient.createUser({
          username: r.rollNo,
          email: r.email,
          password: "Student@123",
          full_name: r.name,
          role: "viewer",
          department: "",
        });
        success++;
      } catch (e: any) {
        errs.push({ row: i + 2, error: e?.message || "Failed to enrol" });
      }
    }
    setEnrolling(false);
    if (errs.length > 0) {
      setErrors(errs);
      addToast(`${success} enrolled, ${errs.length} failed.`, "warning");
    } else {
      addToast(`${success} students enrolled successfully.`, "success");
      setRows([]);
      setErrors([]);
    }
  }

  if (loading) return (<AccessGate feature="user_management" deny="lock"><div className="max-w-6xl mx-auto pb-24 py-8"><p className="text-white/60">Loading courses...</p></div></AccessGate>);

  return (
    <AccessGate feature="user_management" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-5">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4">
          <h1 className="text-2xl font-display text-white">Student Bulk Enrolment</h1>
          <p className="text-xs font-mono text-white/30 mt-2">CSV template: Roll No, Name, Email, Course Codes (comma-separated).</p>
        </motion.header>

        <motion.section variants={fadeSlideUp} className="space-y-3">
          <button onClick={downloadTemplate} className="text-xs font-mono text-brand hover:text-white uppercase">Download CSV template</button>
          <input type="file" accept=".csv" onChange={(e) => { const f = e.target.files?.[0]; if (f) parseFile(f); }} className="text-sm text-white" />
        </motion.section>

        {errors.length > 0 && (
          <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-alert/30">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Row</th>
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Error</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((e, idx) => (
                  <tr key={`${e.row}-${idx}`} className="border-b border-white/5">
                    <td className="px-3 py-2 text-xs text-white/70">{e.row}</td>
                    <td className="px-3 py-2 text-xs text-alert">{e.error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.section>
        )}

        {rows.length > 0 && (
          <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Roll No</th>
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Name</th>
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Email</th>
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Course Codes</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 10).map((r) => (
                  <tr key={r.rollNo} className="border-b border-white/5">
                    <td className="px-3 py-2 text-xs text-white/70">{r.rollNo}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{r.name}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{r.email}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{r.courseCodes.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.section>
        )}

        <motion.section variants={fadeSlideUp}>
          <button
            onClick={confirmEnrolment}
            disabled={rows.length === 0 || errors.length > 0 || enrolling}
            className="px-4 py-2 bg-attain text-white text-xs font-mono uppercase disabled:opacity-40"
          >
            {enrolling ? "Enrolling..." : "Confirm enrol"}
          </button>
        </motion.section>
      </motion.div>
    </AccessGate>
  );
}
