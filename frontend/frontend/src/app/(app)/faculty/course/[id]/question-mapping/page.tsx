"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AccessGate } from "@/components/auth/AccessGate";

export default function QuestionMappingPage() {
  const { id } = useParams();
  const router = useRouter();
  const courseId = id as string;

  useEffect(() => {
    router.replace(`/faculty/course/${courseId}/question-analyser`);
  }, [courseId, router]);

  return (
    <AccessGate feature="ai_question_mapping" deny="lock">
      <div className="max-w-3xl mx-auto min-h-[60vh] flex flex-col items-center justify-center gap-3 text-center">
        <Loader2 className="w-5 h-5 animate-spin text-brand" />
        <p className="text-sm text-white/60">Redirecting to AI Question Analyser...</p>
      </div>
    </AccessGate>
  );
}
