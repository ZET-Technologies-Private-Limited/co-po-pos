"use client";

import { AccessGate } from "@/components/auth/AccessGate";
import { AdminDashboardView } from "@/components/dashboard/AdminDashboardView";

export default function AdminDashboardPage() {
  return (
    <AccessGate feature="admin_dashboard" deny="lock">
      <AdminDashboardView />
    </AccessGate>
  );
}
