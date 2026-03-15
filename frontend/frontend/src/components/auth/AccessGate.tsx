"use client";

import { ReactNode } from "react";
import { Lock } from "lucide-react";
import { useAuthStore, can, PermissionLevel } from "@/lib/authStore";

interface AccessGateProps {
  /** Feature key from the PERMISSIONS map (e.g. "co_generation", "po_attainment") */
  feature: string;
  /** Content to render when access is granted */
  children: ReactNode;
  /**
   * Fallback behaviour when access is denied:
   *   "hide"   (default)  — renders nothing
   *   "lock"              — renders a locked placeholder with a message
   *   "readonly"          — wraps children in a pointer-events-none overlay
   */
  deny?: "hide" | "lock" | "readonly";
  /** Optional label shown in the lock placeholder */
  lockMessage?: string;
}

export function AccessGate({
  feature,
  children,
  deny = "hide",
  lockMessage,
}: AccessGateProps) {
  const { activeRole } = useAuthStore();
  const level: PermissionLevel = can(activeRole, feature);

  // "view" and "own" are treated as allowed (children render normally)
  if (level === "yes" || level === "view" || level === "own") {
    return <>{children}</>;
  }

  // Access denied
  if (deny === "hide") return null;

  if (deny === "readonly") {
    return (
      <div className="relative pointer-events-none opacity-40 select-none">
        <div className="absolute inset-0 z-10 cursor-not-allowed" />
        {children}
      </div>
    );
  }

  // deny === "lock"
  return (
    <div className="flex items-center gap-4 p-6 border border-white/[0.07] bg-white/[0.02]">
      <Lock className="w-4 h-4 text-white/20 shrink-0" />
      <div>
        <p className="text-xs font-mono text-white/30 uppercase tracking-widest">
          {lockMessage ?? "Access restricted for your role"}
        </p>
        <p className="text-[10px] font-mono text-white/20 mt-1">
          Required permission:{" "}
          <span className="text-white/30 capitalize">{feature.replace(/_/g, " ")}</span>
        </p>
      </div>
    </div>
  );
}

// ── Convenience wrapper for read-only overlay ──────────────────────────────
export function ReadOnlyGate({
  feature,
  children,
}: {
  feature: string;
  children: ReactNode;
}) {
  const { activeRole } = useAuthStore();
  const level: PermissionLevel = can(activeRole, feature);

  if (level === "yes" || level === "own") return <>{children}</>;

  // view → read-only overlay
  if (level === "view") {
    return (
      <div className="relative">
        <div className="pointer-events-none opacity-70">{children}</div>
        <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 bg-white/5 border border-white/10">
          <Lock className="w-3 h-3 text-white/40" />
          <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">View Only</span>
        </div>
      </div>
    );
  }

  return null;
}
