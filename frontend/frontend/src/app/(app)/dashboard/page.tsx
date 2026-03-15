"use client";

import { useAuthStore } from "@/lib/authStore";
import { AdminDashboardView } from "@/components/dashboard/AdminDashboardView";
import { DepartmentHeadDashboardView } from "@/components/dashboard/DepartmentHeadDashboardView";
import { LeadDashboardView } from "@/components/dashboard/SubjectLeadDashboardView";
import { FacultyDashboardView } from "@/components/dashboard/FacultyDashboardView";
import { StudentDashboardView } from "@/components/dashboard/StudentDashboardView";
import { motion, AnimatePresence } from "framer-motion";

export default function DashboardPage() {
  const { activeRole } = useAuthStore();

  return (
    <div className="w-full min-h-screen pb-32 pt-4">
      <div className="max-w-5xl mx-auto">
        <AnimatePresence mode="wait">
          {/* Use keys based on activeRole to ensure clean mounting/unmounting animation */}
          <motion.div 
            key={activeRole}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            {activeRole === "admin" && <AdminDashboardView />}
            {activeRole === "department_head" && <DepartmentHeadDashboardView />}
            {activeRole === "subject_lead" && <LeadDashboardView />}
            {activeRole === "faculty" && <FacultyDashboardView />}
            {activeRole === "student" && <StudentDashboardView />}
            {!activeRole && <FacultyDashboardView />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
