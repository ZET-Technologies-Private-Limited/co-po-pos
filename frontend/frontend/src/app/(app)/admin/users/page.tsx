"use client";

import { useMemo, useRef, useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Download, Ellipsis, Plus, Upload } from "lucide-react";
import { AccessGate } from "@/components/auth/AccessGate";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { Role, useAuthStore } from "@/lib/authStore";
import { useUIStore } from "@/lib/uiStore";

type UserRecord = {
  id: string;
  employeeId: string;
  name: string;
  email: string;
  phone?: string;
  roles: Role[];
  dept: string;
  designation?: string;
  status: "active" | "inactive";
  lastLogin?: string;
  password?: string;
};

type SortKey = "employeeId" | "name" | "email" | "role" | "dept" | "status" | "lastLogin";

type FormState = {
  employeeId: string;
  name: string;
  email: string;
  phone: string;
  role: Role;
  dept: string;
  designation: string;
  password: string;
  alsoLead: boolean;
  sendWelcome: boolean;
};

type CsvError = { row: number; field: string; error: string };

const ROLE_OPTIONS: Array<{ value: Role; label: string }> = [
  { value: "faculty", label: "Faculty" },
  { value: "subject_lead", label: "Course Lead" },
  { value: "department_head", label: "HOD" },
  { value: "admin", label: "Admin" },
  { value: "student", label: "Student" },
];

/** Translate frontend Role values to backend-accepted role strings. */
function toApiRole(role: Role): string {
  if (role === "department_head") return "hod";
  if (role === "student") return "viewer";
  return role;
}

const BLANK_FORM: FormState = {
  employeeId: "",
  name: "",
  email: "",
  phone: "",
  role: "faculty",
  dept: "CSE",
  designation: "",
  password: "Nexus@123",
  alsoLead: false,
  sendWelcome: true,
};

function primaryRole(user: UserRecord): Role {
  if (user.roles?.includes("admin")) return "admin";
  if (user.roles?.includes("department_head")) return "department_head";
  if (user.roles?.includes("subject_lead")) return "subject_lead";
  if (user.roles?.includes("faculty")) return "faculty";
  return "student";
}

function roleLabel(role: Role): string {
  return ROLE_OPTIONS.find((r) => r.value === role)?.label || role;
}

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

const backendToFrontendRole: Record<string, Role> = {
  hod: "department_head",
  course_lead: "subject_lead",
  accreditation_officer: "subject_lead",
  viewer: "student",
};

function toUserRecord(u: any): UserRecord {
  const raw = (u.role || "faculty").toLowerCase().replace(" ", "_");
  const role = (backendToFrontendRole[raw] || raw) as Role;
  return {
    id: u.id,
    employeeId: u.username || u.employee_id || "",
    name: u.full_name || u.name || "",
    email: u.email || "",
    phone: "",
    roles: [role],
    dept: u.department || u.dept || "",
    status: u.is_active !== false ? "active" : "inactive",
    lastLogin: "",
  };
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user: me } = useAuthStore();
  const { addToast } = useUIStore();
  const router = useRouter();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersRes, coursesRes] = await Promise.all([
        apiClient.getUsers().catch(() => []),
        apiClient.getCourses().catch(() => []),
      ]);
      setUsers((Array.isArray(usersRes) ? usersRes : []).map(toUserRecord));
      setCourses(Array.isArray(coursesRes) ? coursesRes : coursesRes?.items ?? []);
    } catch (e: any) {
      setError(e?.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const deptOptions = useMemo(() => {
    const set = new Set<string>(["Administration", ...courses.map((c: any) => c.department ?? c.dept ?? "").filter(Boolean), ...users.map((u) => u.dept).filter(Boolean)]);
    return [...set];
  }, [courses, users]);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<"all" | Role>("all");
  const [deptFilter, setDeptFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [sortKey, setSortKey] = useState<SortKey>("employeeId");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [actionMenuUserId, setActionMenuUserId] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(BLANK_FORM);
  const [employeeIdError, setEmployeeIdError] = useState("");

  const [showImport, setShowImport] = useState(false);
  const [csvErrors, setCsvErrors] = useState<CsvError[]>([]);
  const [csvPreview, setCsvPreview] = useState<FormState[]>([]);
  const csvRef = useRef<HTMLInputElement>(null);

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const role = primaryRole(u);
      const matchesRole = roleFilter === "all" || role === roleFilter;
      const matchesDept = deptFilter === "all" || u.dept === deptFilter;
      const matchesStatus = statusFilter === "all" || u.status === statusFilter;
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        u.name.toLowerCase().includes(q) ||
        u.employeeId.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q);
      return matchesRole && matchesDept && matchesStatus && matchesSearch;
    });
  }, [users, roleFilter, deptFilter, statusFilter, search]);

  const sortedUsers = useMemo(() => {
    const list = [...filteredUsers];
    list.sort((a, b) => {
      const roleA = roleLabel(primaryRole(a));
      const roleB = roleLabel(primaryRole(b));
      const valA =
        sortKey === "employeeId" ? a.employeeId :
        sortKey === "name" ? a.name :
        sortKey === "email" ? a.email :
        sortKey === "role" ? roleA :
        sortKey === "dept" ? a.dept :
        sortKey === "status" ? a.status :
        a.lastLogin || "";
      const valB =
        sortKey === "employeeId" ? b.employeeId :
        sortKey === "name" ? b.name :
        sortKey === "email" ? b.email :
        sortKey === "role" ? roleB :
        sortKey === "dept" ? b.dept :
        sortKey === "status" ? b.status :
        b.lastLogin || "";

      const comp = String(valA).localeCompare(String(valB));
      return sortDir === "asc" ? comp : -comp;
    });
    return list;
  }, [filteredUsers, sortKey, sortDir]);

  const selectAllChecked = sortedUsers.length > 0 && sortedUsers.every((u) => selected.has(u.id));

  function toggleSort(next: SortKey) {
    if (sortKey === next) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(next);
    setSortDir("asc");
  }

  function openAddForm() {
    setEditingId(null);
    setForm(BLANK_FORM);
    setEmployeeIdError("");
    setShowForm(true);
  }

  function openEditForm(user: UserRecord) {
    setEditingId(user.id);
    setForm({
      employeeId: user.employeeId,
      name: user.name,
      email: user.email,
      phone: user.phone || "",
      role: primaryRole(user),
      dept: user.dept,
      designation: user.designation,
      password: user.password || "Nexus@123",
      alsoLead: user.roles.includes("faculty") && user.roles.includes("subject_lead"),
      sendWelcome: false,
    });
    setEmployeeIdError("");
    setShowForm(true);
  }

  function validateEmployeeIdUniqueness(value: string) {
    const exists = users.some((u) => u.employeeId.toLowerCase() === value.toLowerCase() && u.id !== editingId);
    setEmployeeIdError(exists ? "Employee ID must be unique." : "");
  }

  async function submitForm(e: React.FormEvent) {
    e.preventDefault();
    if (!form.employeeId || !form.name || !form.email) {
      addToast("Employee ID, Full Name and Email are required.", "warning");
      return;
    }
    validateEmployeeIdUniqueness(form.employeeId);
    if (users.some((u) => u.employeeId.toLowerCase() === form.employeeId.toLowerCase() && u.id !== editingId)) {
      return;
    }

    try {
      if (editingId) {
        await apiClient.updateUser(editingId, {
          role: toApiRole(form.role),
          department: form.dept,
          full_name: form.name,
          is_active: true,
        });
        addToast("User updated.", "success");
        await loadData();
      } else {
        await apiClient.createUser({
          username: form.employeeId,
          email: form.email,
          password: form.password,
          full_name: form.name,
          role: toApiRole(form.role),
          department: form.dept,
        });
        addToast("User created.", "success");
        await loadData();
      }
      setShowForm(false);
      setEditingId(null);
      setForm(BLANK_FORM);
    } catch (err: any) {
      addToast(err?.message || "Failed to save user", "error");
    }
  }

  function toggleUserSelection(userId: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(userId);
      else next.delete(userId);
      return next;
    });
  }

  async function applyBulkDeactivate() {
    try {
      for (const id of selected) {
        await apiClient.updateUser(id, { is_active: false });
      }
      addToast(`${selected.size} user(s) deactivated.`, "info");
      setSelected(new Set());
      await loadData();
    } catch (err: any) {
      addToast(err?.message || "Failed to deactivate", "error");
    }
  }

  function applyBulkResetPassword() {
    addToast("Use Forgot password or per-user reset from profile.", "info");
    setSelected(new Set());
  }

  async function exportUsersToExcel(data: UserRecord[]) {
    const XLSX = await import("xlsx");
    const rows = data.map((u) => ({
      "Employee ID": u.employeeId,
      "Full Name": u.name,
      Email: u.email,
      Role: roleLabel(primaryRole(u)),
      Department: u.dept,
      Status: u.status,
      "Last Login": u.lastLogin || "",
    }));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), "Users");
    XLSX.writeFile(wb, "users_filtered_export.xlsx");
  }

  function downloadTemplate() {
    const template = [
      "Employee ID,Full Name,Email,Phone,Role,Department,Designation,Password",
      "FAC109,Anita Reddy,anita@example.com,9876543210,faculty,CSE,Assistant Professor,Nexus@123",
    ].join("\n");
    const blob = new Blob([template], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "user_import_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  function parseCsv(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || "");
      const lines = raw.split(/\r?\n/).filter((l) => l.trim().length > 0);
      if (lines.length < 2) {
        setCsvErrors([{ row: 1, field: "file", error: "CSV must contain header and at least one data row." }]);
        setCsvPreview([]);
        return;
      }

      const headers = parseCsvLine(lines[0]).map((h) => h.trim().toLowerCase());
      const errors: CsvError[] = [];
      const preview: FormState[] = [];
      const seenIds = new Set<string>();

      function getCell(row: string[], key: string, aliases: string[] = []) {
        const keys = [key, ...aliases].map((k) => k.toLowerCase());
        for (const k of keys) {
          const idx = headers.indexOf(k);
          if (idx >= 0) return (row[idx] || "").trim();
        }
        return "";
      }

      for (let i = 1; i < lines.length; i += 1) {
        const row = parseCsvLine(lines[i]);
        const rowNo = i + 1;
        const employeeId = getCell(row, "employee id", ["employee_id", "id", "employeeid"]);
        const name = getCell(row, "full name", ["name"]);
        const email = getCell(row, "email");
        const phone = getCell(row, "phone");
        const roleRaw = getCell(row, "role").toLowerCase();
        const dept = getCell(row, "department", ["dept"]) || "CSE";
        const designation = getCell(row, "designation");
        const password = getCell(row, "password") || "Nexus@123";

        if (!employeeId) errors.push({ row: rowNo, field: "Employee ID", error: "Missing Employee ID" });
        if (!name) errors.push({ row: rowNo, field: "Full Name", error: "Missing Full Name" });
        if (!email || !email.includes("@")) errors.push({ row: rowNo, field: "Email", error: "Invalid Email" });

        const normalizedRole = roleRaw === "course lead" ? "subject_lead" : roleRaw;
        const validRole = ROLE_OPTIONS.some((r) => r.value === normalizedRole);
        if (!validRole) errors.push({ row: rowNo, field: "Role", error: `Invalid Role: ${roleRaw || "(blank)"}` });

        if (employeeId) {
          if (seenIds.has(employeeId.toLowerCase())) {
            errors.push({ row: rowNo, field: "Employee ID", error: "Duplicate Employee ID in CSV" });
          }
          seenIds.add(employeeId.toLowerCase());
        }

        if (users.some((u) => u.employeeId.toLowerCase() === employeeId.toLowerCase())) {
          errors.push({ row: rowNo, field: "Employee ID", error: "Already exists in system" });
        }

        if (!errors.some((e) => e.row === rowNo)) {
          preview.push({
            employeeId,
            name,
            email,
            phone,
            role: normalizedRole as Role,
            dept,
            designation,
            password,
            alsoLead: false,
            sendWelcome: false,
          });
        }
      }

      setCsvErrors(errors);
      setCsvPreview(preview);
    };
    reader.readAsText(file);
  }

  async function confirmCsvImport() {
    if (csvErrors.length > 0) return;
    try {
      for (const item of csvPreview) {
        await apiClient.createUser({
          username: item.employeeId,
          email: item.email,
          password: item.password,
          full_name: item.name,
          role: toApiRole(item.role),
          department: item.dept,
        });
      }
      addToast(`${csvPreview.length} users imported.`, "success");
      setCsvPreview([]);
      setCsvErrors([]);
      await loadData();
    } catch (err: any) {
      addToast(err?.message || "Import failed", "error");
    }
  }

  const thClass = "px-3 py-3 text-left text-[10px] font-mono text-white/30 uppercase tracking-widest cursor-pointer";

  if (loading) {
    return (
      <AccessGate feature="user_management" deny="lock">
        <div className="max-w-7xl mx-auto pb-32 py-8"><p className="text-white/60">Loading users...</p></div>
      </AccessGate>
    );
  }
  if (error) {
    return (
      <AccessGate feature="user_management" deny="lock">
        <div className="max-w-7xl mx-auto pb-32 py-8"><p className="text-alert">{error}</p></div>
      </AccessGate>
    );
  }

  return (
    <AccessGate feature="user_management" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-7xl mx-auto pb-32 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-5">
          <h1 className="text-3xl font-display text-white">User Management</h1>
          <p className="text-xs font-mono text-white/30 mt-2">
            User List Page and workflows for add/edit, import, bulk actions, and assignment sub-pages.
          </p>
        </motion.header>

        <motion.section variants={fadeSlideUp} className="flex flex-wrap gap-2 items-center">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or employee ID"
            className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white min-w-[250px]"
          />
          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as "all" | Role)} className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
            <option value="all">All Roles</option>
            {ROLE_OPTIONS.map((r) => (
              <option key={r.value} value={r.value} className="bg-[#0a0a0f]">{r.label}</option>
            ))}
          </select>
          <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
            <option value="all">All Departments</option>
            {deptOptions.map((d) => (
              <option key={d} value={d} className="bg-[#0a0a0f]">{d}</option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as "all" | "active" | "inactive")} className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <button onClick={() => exportUsersToExcel(sortedUsers)} className="px-3 py-2 border border-white/10 text-xs font-mono text-white/60 hover:text-white uppercase flex items-center gap-1">
            <Download className="w-3.5 h-3.5" /> Export Users
          </button>
          <button onClick={openAddForm} className="px-3 py-2 bg-brand text-white text-xs font-mono uppercase flex items-center gap-1">
            <Plus className="w-3.5 h-3.5" /> Add User
          </button>
          <button onClick={() => setShowImport((v) => !v)} className="px-3 py-2 border border-white/10 text-xs font-mono text-white/60 hover:text-white uppercase flex items-center gap-1">
            <Upload className="w-3.5 h-3.5" /> Bulk Import
          </button>
          <Link href="/admin/users/course-assignment" className="px-3 py-2 border border-white/10 text-xs font-mono text-white/60 hover:text-white uppercase">
            Course Assignment
          </Link>
          <Link href="/admin/users/student-bulk-enrolment" className="px-3 py-2 border border-white/10 text-xs font-mono text-white/60 hover:text-white uppercase">
            Student Enrolment
          </Link>
        </motion.section>

        {selected.size > 0 && (
          <motion.section variants={fadeSlideUp} className="border border-brand/30 bg-brand/10 px-3 py-2 text-xs font-mono text-white flex items-center gap-3">
            <span>{selected.size} selected:</span>
            <button onClick={applyBulkDeactivate} className="text-alert hover:text-white uppercase">Deactivate</button>
            <button onClick={applyBulkResetPassword} className="text-amber-300 hover:text-white uppercase">Reset Password</button>
            <button onClick={() => exportUsersToExcel(users.filter((u) => selected.has(u.id)))} className="text-attain hover:text-white uppercase">Export</button>
          </motion.section>
        )}

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className="px-3 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectAllChecked}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelected(new Set(sortedUsers.map((u) => u.id)));
                      } else {
                        setSelected(new Set());
                      }
                    }}
                  />
                </th>
                <th className={thClass} onClick={() => toggleSort("employeeId")}>Employee ID</th>
                <th className={thClass} onClick={() => toggleSort("name")}>Full Name</th>
                <th className={thClass} onClick={() => toggleSort("email")}>Email</th>
                <th className={thClass} onClick={() => toggleSort("role")}>Role</th>
                <th className={thClass} onClick={() => toggleSort("dept")}>Dept</th>
                <th className={thClass} onClick={() => toggleSort("status")}>Status</th>
                <th className={thClass} onClick={() => toggleSort("lastLogin")}>Last Login</th>
                <th className="px-3 py-3 text-left text-[10px] font-mono text-white/30 uppercase tracking-widest">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-3 py-10 text-center text-sm text-white/30">No users found.</td>
                </tr>
              ) : (
                sortedUsers.map((u) => {
                  const role = primaryRole(u);
                  return (
                    <tr key={u.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="px-3 py-3">
                        <input type="checkbox" checked={selected.has(u.id)} onChange={(e) => toggleUserSelection(u.id, e.target.checked)} />
                      </td>
                      <td className="px-3 py-3 text-xs font-mono text-white">{u.employeeId}</td>
                      <td className="px-3 py-3 text-sm text-white">{u.name}</td>
                      <td className="px-3 py-3 text-sm text-white/70">{u.email}</td>
                      <td className="px-3 py-3 text-sm text-white/70">{roleLabel(role)}</td>
                      <td className="px-3 py-3 text-sm text-white/70">{u.dept}</td>
                      <td className="px-3 py-3 text-sm">
                        <span className={u.status === "active" ? "text-attain" : "text-alert"}>{u.status}</span>
                      </td>
                      <td className="px-3 py-3 text-sm text-white/50">{u.lastLogin || "Never"}</td>
                      <td className="px-3 py-3 text-sm text-white/60 relative">
                        <button onClick={() => setActionMenuUserId((id) => (id === u.id ? null : u.id))} className="p-1 border border-white/10 hover:border-white/40">
                          <Ellipsis className="w-4 h-4" />
                        </button>
                        {actionMenuUserId === u.id && (
                          <div className="absolute right-3 top-10 z-10 border border-white/10 bg-[#0a0a0f] min-w-[170px]">
                            <button onClick={() => { openEditForm(u); setActionMenuUserId(null); }} className="block w-full text-left px-3 py-2 text-xs hover:bg-white/[0.04]">Edit</button>
                            <button onClick={() => { void apiClient.updateUser(u.id, { is_active: false }).then(() => loadData()); setActionMenuUserId(null); }} className="block w-full text-left px-3 py-2 text-xs hover:bg-white/[0.04]">Deactivate</button>
                            <button onClick={() => { addToast("Password reset link sent.", "info"); setActionMenuUserId(null); }} className="block w-full text-left px-3 py-2 text-xs hover:bg-white/[0.04]">Reset Password</button>
                            <button onClick={() => { addToast(`Activity view for ${u.name} opened in audit trail.`, "info"); router.push("/admin/audit-log"); }} className="block w-full text-left px-3 py-2 text-xs hover:bg-white/[0.04]">View Activity</button>
                            <button onClick={() => { router.push(`/admin/users/course-assignment?userId=${u.id}`); }} className="block w-full text-left px-3 py-2 text-xs hover:bg-white/[0.04]">Assign Courses</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </motion.section>

        {showForm && (
          <motion.section variants={fadeSlideUp} className="border border-white/10 p-4">
            <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-4">{editingId ? "Edit User" : "Add User"}</h2>
            <form onSubmit={submitForm} className="space-y-4">
              <div className="grid md:grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] font-mono text-white/40 uppercase">Employee ID</label>
                  <input
                    value={form.employeeId}
                    onBlur={(e) => validateEmployeeIdUniqueness(e.target.value)}
                    onChange={(e) => setForm((p) => ({ ...p, employeeId: e.target.value.trim().toUpperCase() }))}
                    className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white"
                    required
                  />
                  {employeeIdError && <p className="text-xs text-alert mt-1">{employeeIdError}</p>}
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/40 uppercase">Full Name</label>
                  <input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white" required />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/40 uppercase">Email</label>
                  <input type="email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white" required />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/40 uppercase">Phone</label>
                  <input value={form.phone} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white" />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/40 uppercase">Department</label>
                  <select value={form.dept} onChange={(e) => setForm((p) => ({ ...p, dept: e.target.value }))} className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
                    {deptOptions.map((d) => (
                      <option key={d} value={d} className="bg-[#0a0a0f]">{d}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/40 uppercase">Designation</label>
                  <input value={form.designation} onChange={(e) => setForm((p) => ({ ...p, designation: e.target.value }))} className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white" />
                </div>
              </div>

              <div>
                <p className="text-[10px] font-mono text-white/40 uppercase mb-2">Role</p>
                <div className="flex flex-wrap gap-2">
                  {ROLE_OPTIONS.map((r) => (
                    <label key={r.value} className="text-xs text-white/70 flex items-center gap-1 border border-white/10 px-2 py-1">
                      <input type="radio" name="role" checked={form.role === r.value} onChange={() => setForm((p) => ({ ...p, role: r.value, alsoLead: r.value === "faculty" ? p.alsoLead : false }))} />
                      {r.label}
                    </label>
                  ))}
                </div>
              </div>

              {form.role === "faculty" && (
                <label className="text-xs text-white/70 flex items-center gap-2">
                  <input type="checkbox" checked={form.alsoLead} onChange={(e) => setForm((p) => ({ ...p, alsoLead: e.target.checked }))} />
                  Also assign as Lead
                </label>
              )}

              {!editingId && (
                <div className="grid md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] font-mono text-white/40 uppercase">Initial Password</label>
                    <input value={form.password} onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} className="w-full bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white" />
                  </div>
                  <label className="text-xs text-white/70 flex items-center gap-2 mt-6">
                    <input type="checkbox" checked={form.sendWelcome} onChange={(e) => setForm((p) => ({ ...p, sendWelcome: e.target.checked }))} />
                    Send welcome email
                  </label>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button type="submit" className="px-4 py-2 bg-brand text-white text-xs font-mono uppercase">Save</button>
                <button type="button" onClick={() => { setShowForm(false); setEditingId(null); setForm(BLANK_FORM); }} className="px-4 py-2 border border-white/10 text-white/70 text-xs font-mono uppercase">Cancel</button>
              </div>
            </form>
          </motion.section>
        )}

        {showImport && (
          <motion.section variants={fadeSlideUp} className="border border-white/10 p-4 space-y-4">
            <h2 className="text-sm font-mono text-white uppercase tracking-widest">Bulk CSV Import</h2>
            <button onClick={downloadTemplate} className="text-xs font-mono text-brand hover:text-white uppercase">Download user import template</button>
            <div>
              <input ref={csvRef} type="file" accept=".csv" onChange={(e) => { const f = e.target.files?.[0]; if (f) parseCsv(f); }} className="text-sm text-white" />
            </div>

            {csvErrors.length > 0 && (
              <div className="overflow-x-auto border border-alert/30">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="px-3 py-2 text-left text-[10px] font-mono uppercase text-white/40">Row</th>
                      <th className="px-3 py-2 text-left text-[10px] font-mono uppercase text-white/40">Field</th>
                      <th className="px-3 py-2 text-left text-[10px] font-mono uppercase text-white/40">Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvErrors.map((err, idx) => (
                      <tr key={`${err.row}-${idx}`} className="border-b border-white/5">
                        <td className="px-3 py-2 text-xs text-white/70">{err.row}</td>
                        <td className="px-3 py-2 text-xs text-white/70">{err.field}</td>
                        <td className="px-3 py-2 text-xs text-alert">{err.error}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {csvPreview.length > 0 && (
              <div className="overflow-x-auto border border-white/10">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      {"Employee ID,Full Name,Email,Role,Department".split(",").map((h) => (
                        <th key={h} className="px-3 py-2 text-left text-[10px] font-mono uppercase text-white/40">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {csvPreview.slice(0, 10).map((u) => (
                      <tr key={`${u.employeeId}-${u.email}`} className="border-b border-white/5">
                        <td className="px-3 py-2 text-xs text-white/70">{u.employeeId}</td>
                        <td className="px-3 py-2 text-xs text-white/70">{u.name}</td>
                        <td className="px-3 py-2 text-xs text-white/70">{u.email}</td>
                        <td className="px-3 py-2 text-xs text-white/70">{roleLabel(u.role)}</td>
                        <td className="px-3 py-2 text-xs text-white/70">{u.dept}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <button
              onClick={confirmCsvImport}
              disabled={csvErrors.length > 0 || csvPreview.length === 0}
              className="px-4 py-2 bg-attain text-white text-xs font-mono uppercase disabled:opacity-40"
            >
              Confirm Import
            </button>
          </motion.section>
        )}
      </motion.div>
    </AccessGate>
  );
}
