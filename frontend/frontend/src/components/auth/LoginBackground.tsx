"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";
import { Canvas } from "@react-three/fiber";

const ProfessionalAbstract3D = dynamic(() => import("@/components/landing/ProfessionalAbstract3D"), {
  ssr: false,
  loading: () => null
});

export function LoginBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none opacity-30">
      <Canvas camera={{ position: [0, 0, 9], fov: 50 }}>
        <Suspense fallback={null}>
          <ProfessionalAbstract3D />
        </Suspense>
      </Canvas>
      {/* Vignette - Light theme */}
      <div className="absolute inset-0 bg-gradient-to-r from-white via-blue-50/40 to-white" />
      <div className="absolute inset-0 bg-gradient-to-b from-white/70 via-transparent to-white/70" />
    </div>
  );
}
