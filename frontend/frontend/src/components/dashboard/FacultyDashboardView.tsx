"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import Link from "next/link";
import { AlertCircle, Bell, CheckCircle2, Clock, Plus } from "lucide-react";
import apiClient from "@/lib/apiClient";
import { useAuthStore } from "@/lib/authStore";

type DashboardCourse = {
  id: string;
  course_code: string;
  course_name: string;
  semester?: number;
  enrolled_students?: number;
  co_status?: string;
  marks_status?: string;
  action_url?: string;
};

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export function FacultyDashboardView() {
  const { activeAY, user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashRes, actRes, notifRes] = await Promise.all([
        apiClient.getFacultyDashboard({ ay_code: activeAY }),
        apiClient.getFacultyActivityLog(10),
        apiClient.getNotifications(),
      ]);
      setDashboard(dashRes);
      setActivity(asArray<any>(dashRes?.recent_activity?.items ?? actRes?.items ?? actRes?.activities ?? actRes));
      setNotifications(asArray<any>(notifRes?.items ?? notifRes?.notifications ?? notifRes));
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, [activeAY]);

  useEffect(() => {
    void load();
  }, [load]);

  const courses = useMemo(() => {
    const rows = asArray<any>(dashboard?.courses_table?.rows);
    const myCourses = asArray<any>(dashboard?.my_courses);
    if (rows.length) {
      return rows.map((r: any) => ({
        id: r.course_id,
        course_code: r.course_code,
        course_name: r.course_name,
        semester: r.semester,
        enrolled_students: r.enrolled_students,
        co_status: r.co_status,
        marks_status: r.marks_status,
        action_url: r.actions?.[0]?.link,
      })) as DashboardCourse[];
    }
    return myCourses.map((c: any) => ({
      id: c.id,
      course_code: c.course_code,
      course_name: c.course_name,
      semester: c.semester,
      enrolled_students: undefined,
      co_status: undefined,
      marks_status: undefined,
      action_url: `/faculty/course/${c.id}/co-generation`,
    })) as DashboardCourse[];
  }, [dashboard]);

  const pendingActions = useMemo(() => {
    const items = asArray<any>(dashboard?.pending_actions?.items ?? dashboard?.pending_actions ?? dashboard?.actions);
    return items.map((a: any) => ({
      ...a,
      text: a.description ?? a.text ?? a.label,
      href: a.action_link ?? a.go_link ?? a.href,
    }));
  }, [dashboard]);

  const unread = useMemo(
    () => notifications.filter((n) => !n?.is_read && !n?.read).length,
    [notifications],
  );

  if (loading) {
    return <div className="py-20 text-white/60">Loading faculty dashboard...</div>;
  }

  if (error) {
    return <div className="py-20 text-alert">{error}</div>;
  }

  return (
    <div className="flex flex-col gap-8 pb-24">
      <section className="border-b border-white/10 pb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-white font-display">Faculty Dashboard</h1>
          <p className="text-white/50 text-sm mt-1">
            {dashboard?.header?.welcome_line ?? (user?.name ? `Welcome, ${user.name}` : "Welcome")} | AY {activeAY}
          </p>
        </div>
        <Link 
          href="/faculty/course/new"
          className="flex items-center gap-2 bg-brand text-white text-sm font-semibold px-4 py-2 rounded-md hover:bg-brand/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Course
        </Link>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="border border-white/10 rounded-lg p-4">
          <p className="text-[11px] text-white/40 uppercase">Assigned Courses</p>
          <p className="text-2xl text-white mt-1">{courses.length}</p>
        </div>
        <div className="border border-white/10 rounded-lg p-4">
          <p className="text-[11px] text-white/40 uppercase">Pending Actions</p>
          <p className="text-2xl text-amber-400 mt-1">{pendingActions.length}</p>
        </div>
        <div className="border border-white/10 rounded-lg p-4">
          <p className="text-[11px] text-white/40 uppercase">Unread Notifications</p>
          <p className="text-2xl text-brand mt-1">{unread}</p>
        </div>
      </section>

      <section>
        <h2 className="text-sm text-white/80 mb-3">Courses</h2>
        <div className="border border-white/10 rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/[0.03] text-white/50">
              <tr>
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Semester</th>
                <th className="px-3 py-2">Students</th>
                <th className="px-3 py-2">CO Status</th>
                <th className="px-3 py-2">Marks Status</th>
                <th className="px-3 py-2">Open</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id} className="border-t border-white/10">
                  <td className="px-3 py-2 text-white/70">{c.course_code}</td>
                  <td className="px-3 py-2 text-white">{c.course_name}</td>
                  <td className="px-3 py-2 text-white/70">{c.semester ?? "-"}</td>
                  <td className="px-3 py-2 text-white/70">{c.enrolled_students ?? "-"}</td>
                  <td className="px-3 py-2 text-white/70">{c.co_status ?? "-"}</td>
                  <td className="px-3 py-2 text-white/70">{c.marks_status ?? "-"}</td>
                  <td className="px-3 py-2">
                    <Link className="text-brand hover:text-white" href={c.action_url ?? `/faculty/course/${c.id}/co-generation`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
              {courses.length === 0 && (
                <tr>
                  <td className="px-3 py-6 text-white/40" colSpan={7}>
                    No courses found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-white/10 rounded-lg p-4">
          <div className="flex items-center gap-2 text-white mb-3">
            <Clock className="w-4 h-4" /> Recent Activity
          </div>
          <div className="space-y-2">
            {activity.slice(0, 8).map((a, idx) => (
              <div key={idx} className="text-xs text-white/70 border-b border-white/5 pb-2">
                <div>{a.text ?? a.action ?? a.message ?? "Activity"}</div>
                <div className="text-white/40 mt-1">{a.time_ago ?? a.timestamp ?? a.at ?? ""}</div>
              </div>
            ))}
            {activity.length === 0 && <p className="text-xs text-white/40">No recent activity.</p>}
          </div>
        </div>

        <div className="border border-white/10 rounded-lg p-4">
          <div className="flex items-center gap-2 text-white mb-3">
            <Bell className="w-4 h-4" /> Notifications
          </div>
          <div className="space-y-2">
            {notifications.slice(0, 8).map((n, idx) => {
              const isRead = Boolean(n?.is_read ?? n?.read);
              return (
                <div key={idx} className="text-xs border-b border-white/5 pb-2">
                  <div className={isRead ? "text-white/60" : "text-white"}>{n.title || "Notification"}</div>
                  <div className="text-white/40 mt-1">{n.message || ""}</div>
                  <div className="text-white/30 mt-1">{n.created_at || n.timestamp || ""}</div>
                </div>
              );
            })}
            {notifications.length === 0 && <p className="text-xs text-white/40">No notifications.</p>}
          </div>
        </div>
      </section>

      <section className="border border-white/10 rounded-lg p-4">
        <h2 className="text-sm text-white mb-3">Priority Actions</h2>
        <div className="space-y-2">
          {pendingActions.map((a, idx) => (
            <div key={idx} className="flex items-center justify-between text-sm border-b border-white/5 pb-2">
              <div className="flex items-center gap-2">
                {a.overdue ? (
                  <AlertCircle className="w-4 h-4 text-alert" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-amber-400" />
                )}
                <span className="text-white/80">{a.text ?? a.description ?? a.label ?? "Action"}</span>
              </div>
              {(a.href ?? a.action_link ?? a.go_link) ? (
                <Link className="text-brand hover:text-white text-xs" href={a.href ?? a.action_link ?? a.go_link}>
                  Go
                </Link>
              ) : null}
            </div>
          ))}
          {pendingActions.length === 0 && <p className="text-xs text-white/40">No pending actions.</p>}
        </div>
      </section>
    </div>
  );
}
