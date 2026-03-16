"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function MarksIndexPage() {
  const { id } = useParams();
  const router = useRouter();
  const courseId = id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function resolveRoute() {
      setLoading(true);
      setError(null);
      try {
        const exams = await apiClient.getExams(courseId);
        if (cancelled) return;

        const examList = Array.isArray(exams) ? exams : [];
        if (examList.length > 0) {
          router.replace(`/faculty/course/${courseId}/marks/${examList[0].id}`);
          return;
        }

        setError("No exams found for this course. Create an exam first in Exam Configuration.");
      } catch (e: any) {
        if (!cancelled) {
          setError(typeof e?.message === "string" ? e.message : "Failed to load exams.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void resolveRoute();
    return () => {
      cancelled = true;
    };
  }, [courseId, router]);

  return (
    <AccessGate feature="marks_upload" deny="lock">
      <div className="max-w-4xl mx-auto py-12">
        {loading ? <p className="text-white/60">Loading marks workspace...</p> : null}
        {error ? (
          <div className="border border-white/10 rounded-lg p-4">
            <p className="text-alert">{error}</p>
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}
