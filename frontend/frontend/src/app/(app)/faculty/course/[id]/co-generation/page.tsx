"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function FacultyCOGenerationPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [course, setCourse] = useState<any>(null);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [syllabus, setSyllabus] = useState("");
  const [numCos, setNumCos] = useState(5);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [programOutcomes, setProgramOutcomes] = useState<any[]>([]);
  const [programSpecificOutcomes, setProgramSpecificOutcomes] = useState<any[]>([]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, cos] = await Promise.all([apiClient.getCourse(courseId), apiClient.getCourseOutcomes(courseId)]);
      setCourse(c);
      setSyllabus(c?.syllabus || "");
      setOutcomes(Array.isArray(cos) ? cos : []);

      const programId = String(c?.program_id || c?.programId || "");
      if (programId) {
        const [pos, psos] = await Promise.all([
          apiClient.getProgramOutcomes(programId),
          apiClient.getPSOs(programId),
        ]);
        setProgramOutcomes(Array.isArray(pos) ? pos : []);
        setProgramSpecificOutcomes(Array.isArray(psos) ? psos : []);
      } else {
        setProgramOutcomes([]);
        setProgramSpecificOutcomes([]);
      }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load CO generation data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [courseId]);

  async function generate() {
    if (!syllabus.trim()) {
      setError("Syllabus is required for AI CO generation.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiClient.generateCourseOutcomes(courseId, {
        syllabus,
        num_cos: numCos,
        program_outcomes: programOutcomes.map((po: any) => ({ code: po.code ?? po.id, statement: po.statement ?? po.description ?? "" })),
        program_specific_outcomes: programSpecificOutcomes.map((pso: any) => ({ code: pso.code ?? pso.id, statement: pso.statement ?? pso.description ?? "" })),
      });
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "CO generation failed.");
    } finally {
      setSaving(false);
    }
  }

  async function regenerate(coId: string) {
    setSaving(true);
    setError(null);
    try {
      await apiClient.regenerateSingleCO(courseId, coId);
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "CO regeneration failed.");
    } finally {
      setSaving(false);
    }
  }

  async function saveSyllabus() {
    setSaving(true);
    setError(null);
    try {
      await apiClient.updateSyllabus(courseId, syllabus);
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to update syllabus.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AccessGate feature="co_generation" deny="lock">
      <div className="w-full min-h-screen py-12 px-8">
        {/* Header Section */}
        <div className="mb-12">
          <h1 className="text-4xl text-white font-bold mb-3 tracking-tight">Course Outcome Generation</h1>
          <p className="text-xl text-white/70 font-medium">
            {course?.course_name || "Course"} 
            <span className="text-white/50 ml-2">({course?.course_code || "-"})</span>
          </p>
        </div>

        {/* Status Messages */}
        {loading && (
          <div className="mb-8">
            <p className="text-lg text-white/60">Loading course data...</p>
          </div>
        )}
        {error && (
          <div className="mb-8">
            <p className="text-lg text-red-400 font-medium">{error}</p>
          </div>
        )}

        {!loading && (
          <>
            {/* Syllabus Input Section */}
            <div className="w-full mb-16">
              <div className="mb-8">
                <h2 className="text-2xl text-white font-semibold mb-4">Course Syllabus</h2>
                <p className="text-white/60 mb-6">Enter the complete course syllabus to generate relevant course outcomes using AI</p>
              </div>
              
              <textarea
                value={syllabus}
                onChange={(e) => setSyllabus(e.target.value)}
                rows={12}
                className="w-full bg-gray-900/60 text-white text-base p-6 leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="Enter the detailed course syllabus including topics, learning objectives, and key concepts..."
              />
              
              {/* Configuration Row */}
              <div className="flex items-center justify-between mt-8">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-3">
                    <label className="text-white font-medium text-lg">Number of Course Outcomes:</label>
                    <select
                      value={numCos}
                      onChange={(e) => setNumCos(Number(e.target.value))}
                      className="bg-gray-800 text-white px-4 py-2 text-base font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    >
                      <option value={4}>4 Outcomes</option>
                      <option value={5}>5 Outcomes</option>
                      <option value={6}>6 Outcomes</option>
                    </select>
                  </div>
                </div>
                
                {/* Action Buttons */}
                <div className="flex gap-4">
                  <button 
                    onClick={() => void saveSyllabus()} 
                    disabled={saving} 
                    className="px-6 py-3 text-base font-medium bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {saving ? 'Saving...' : 'Save Syllabus'}
                  </button>
                  <button 
                    onClick={() => void generate()} 
                    disabled={saving || !syllabus.trim()} 
                    className="px-8 py-3 text-base font-medium bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {saving ? 'Generating...' : 'Generate Course Outcomes with AI'}
                  </button>
                </div>
              </div>
            </div>

            {/* Course Outcomes Section */}
            <div className="w-full">
              <div className="mb-8">
                <h2 className="text-2xl text-white font-semibold mb-4">Generated Course Outcomes</h2>
                <p className="text-white/60">AI-generated course outcomes based on the provided syllabus</p>
              </div>
              
              {outcomes.length === 0 ? (
                <div className="text-center py-16">
                  <p className="text-xl text-white/50 mb-4">No course outcomes available</p>
                  <p className="text-white/40">Enter a syllabus above and click 'Generate Course Outcomes with AI' to get started</p>
                </div>
              ) : (
                <div className="w-full space-y-8">
                  {outcomes.map((co, index) => (
                    <div key={co.id} className="w-full py-6 border-b border-white/10 last:border-b-0">
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-4">
                          <span className="text-2xl font-bold text-blue-400">#{index + 1}</span>
                          <h3 className="text-xl text-white font-semibold">{co.code || co.co_code}</h3>
                        </div>
                        <button 
                          onClick={() => void regenerate(String(co.id))} 
                          disabled={saving} 
                          className="px-4 py-2 text-sm font-medium text-blue-400 hover:text-blue-300 hover:bg-blue-400/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                          {saving ? 'Regenerating...' : 'Regenerate'}
                        </button>
                      </div>
                      
                      <div className="ml-12">
                        <p className="text-lg text-white/90 leading-relaxed mb-3">
                          {co.statement || co.co_statement || co.description}
                        </p>
                        <div className="flex items-center gap-6">
                          <div className="flex items-center gap-2">
                            <span className="text-white/60 font-medium">Bloom's Taxonomy Level:</span>
                            <span className="text-white font-medium bg-gray-800/60 px-3 py-1 text-sm">
                              {co.bloom_level || "Not specified"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AccessGate>
  );
}
