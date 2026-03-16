"use client";

import { AccessGate } from "@/components/auth/AccessGate";
import { LeadDashboardView } from "@/components/dashboard/SubjectLeadDashboardView";

export default function LeadDashboardPage() {
  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="w-full px-6 py-8">
        <LeadDashboardView />
      </div>
    </AccessGate>
  );
}
