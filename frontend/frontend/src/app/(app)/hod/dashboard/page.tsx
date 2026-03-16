"use client";

import { AccessGate } from "@/components/auth/AccessGate";
import { DepartmentHeadDashboardView } from "@/components/dashboard/DepartmentHeadDashboardView";

export default function HODDashboardPage() {
  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="w-full min-h-screen px-8 md:px-16 py-10">
        <DepartmentHeadDashboardView />
      </div>
    </AccessGate>
  );
}
