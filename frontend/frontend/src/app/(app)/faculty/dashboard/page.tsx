"use client";

import { FacultyDashboardView } from "@/components/dashboard/FacultyDashboardView";
import { AccessGate } from "@/components/auth/AccessGate";

export default function FacultyDashboardPage() {
  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="max-w-7xl mx-auto">
        <FacultyDashboardView />
      </div>
    </AccessGate>
  );
}
