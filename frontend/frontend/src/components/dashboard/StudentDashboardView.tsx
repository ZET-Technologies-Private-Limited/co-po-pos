"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// The real student dashboard lives at /student/dashboard.
// This component is mounted by the shared /dashboard page when activeRole === "student".
// We simply redirect to keep all student logic in one place.
export function StudentDashboardView() {
  const router = useRouter();
  useEffect(() => { router.replace("/student/dashboard"); }, [router]);
  return null;
}
