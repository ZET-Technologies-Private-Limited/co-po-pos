"use client";

import { FacultyDashboardBackendView } from "@/components/dashboard/FacultyDashboardBackendView";
import { AccessGate } from "@/components/auth/AccessGate";

export default function FacultyDashboardPage() {
  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="w-full px-6 lg:px-10 py-8">
        <FacultyDashboardBackendView />
      </div>
    </AccessGate>
  );
}
