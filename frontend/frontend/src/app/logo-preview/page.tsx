"use client";

import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { 
  Float, 
  PerspectiveCamera,
  Environment,
  PresentationControls,
  MeshTransmissionMaterial,
  MeshReflectorMaterial,
  Sparkles,
  BakeShadows
} from '@react-three/drei';

// ── PRECISE SHAPE COMPONENT ──
function ShieldCore() {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Create Shield Shape that matches the prompt logo precisely
  const shieldShape = useMemo(() => {
    const shape = new THREE.Shape();
    // Start at top center (indented)
    shape.moveTo(0, 1.1);
    // Top indented curves
    shape.quadraticCurveTo(0.5, 1.3, 1.2, 1.1);
    // Right side curve
    shape.quadraticCurveTo(1.4, 0.4, 1.2, -0.4);
    // Bottom point
    shape.quadraticCurveTo(0.6, -1.2, 0, -1.5);
    // Left side curve 
    shape.quadraticCurveTo(-0.6, -1.2, -1.2, -0.4);
    shape.quadraticCurveTo(-1.4, 0.4, -1.2, 1.1);
    // Back to top indented curves
    shape.quadraticCurveTo(-0.5, 1.3, 0, 1.1);
    return shape;
  }, []);

  const extrudeSettings = { depth: 0.2, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.05, bevelSegments: 20 };

  return (
    <group>
      {/* ── GLASS FRONT ── */}
      <mesh position={[0, 0, 0.15]}>
        <extrudeGeometry args={[shieldShape, { ...extrudeSettings, depth: 0.05 }]} />
        <MeshTransmissionMaterial 
          backside 
          samples={16} 
          resolution={512} 
          transmission={1} 
          thickness={0.5} 
          roughness={0.1} 
          chromaticAberration={0.04} 
          anisotropy={0.3} 
          distortion={0.1} 
          distortionScale={0.1} 
          temporalDistortion={0.1} 
          color="#93c5fd"
        />
      </mesh>

      {/* ── METALLIC BORDER ── */}
      <mesh position={[0, 0, 0]}>
        <extrudeGeometry args={[shieldShape, { ...extrudeSettings, depth: 0.25 }]} />
        <meshStandardMaterial 
          color="#1e40af" 
          metalness={1} 
          roughness={0.1} 
          emissive="#1e3a8a" 
          emissiveIntensity={0.5} 
        />
      </mesh>

      {/* ── INNER LOGO HUB ── */}
      <group position={[0, 0, 0.25]}>
        {/* Glow Ring */}
        <mesh>
          <torusGeometry args={[0.55, 0.02, 16, 100]} />
          <meshStandardMaterial color="#60a5fa" emissive="#3b82f6" emissiveIntensity={4} />
        </mesh>

        {/* The Star (Glowing Core) */}
        <mesh rotation={[0, 0, Math.PI / 5]}>
          <ringGeometry args={[0, 0.25, 5]} />
          <meshStandardMaterial color="white" emissive="white" emissiveIntensity={10} />
        </mesh>

        {/* Radial Spokes (Matching precision of logo) */}
        {[0, 72, 144, 216, 288].map((angle, i) => (
          <group key={i} rotation={[0, 0, (angle * Math.PI) / 180]}>
            <mesh position={[0, 0.45, 0.02]}>
              <boxGeometry args={[0.12, 0.4, 0.05]} />
              <meshStandardMaterial color="#3b82f6" emissive="#1d4ed8" emissiveIntensity={2} />
            </mesh>
          </group>
        ))}
      </group>
    </group>
  );
}

function Scene() {
  const { viewport } = useThree();
  
  return (
    <>
      <PerspectiveCamera makeDefault position={[0, 0, 8]} fov={35} />
      <ambientLight intensity={0.4} />
      <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={10} castShadow />
      <pointLight position={[-10, -10, -10]} intensity={2} color="#1e40af" />
      
      <PresentationControls
        global
        rotation={[0, 0.1, 0]}
        polar={[-Math.PI / 4, Math.PI / 4]}
        azimuth={[-Math.PI / 2, Math.PI / 2]}
      >
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <ShieldCore />
        </Float>
      </PresentationControls>

      {/* ── REFLECTIVE FLOOR ── */}
      <mesh position={[0, -3.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[100, 100]} />
        <MeshReflectorMaterial
          blur={[300, 100]}
          resolution={1024}
          mixBlur={1}
          mixStrength={40}
          roughness={1}
          depthScale={1.2}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
          color="#050505"
          metalness={0.5}
          mirror={1}
        />
      </mesh>

      <Sparkles count={100} scale={10} size={2} speed={0.4} color="#3b82f6" />
      <Environment preset="city" />
      <BakeShadows />
    </>
  );
}

export default function EnhancedLogoPreview() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return <div className="w-full h-screen bg-[#020617]" />;

  return (
    <div className="w-full h-screen bg-[#020617] flex flex-col relative overflow-hidden">
      {/* Background HUD Layer */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-brand/20 rounded-full animate-pulse-slow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[1200px] border border-brand/5 rounded-full" />
      </div>

      {/* Navbar Mockup */}
      <nav className="z-10 px-12 py-8 flex items-center justify-between border-b border-white/5 bg-cosmic/50 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-brand/10 border border-brand/30 flex items-center justify-center font-mono text-brand font-bold">N</div>
          <span className="text-white font-display text-lg tracking-tight">Nexus AI Identity</span>
        </div>
        <div className="flex items-center gap-12 text-[10px] font-mono text-white/30 uppercase tracking-[0.4em]">
           <span>High Fidelity</span>
           <span>v4.0.2</span>
           <span className="text-brand">Synchronized</span>
        </div>
      </nav>

      <div className="flex-1 w-full relative">
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
           <div className="flex flex-col items-center">
              <h1 className="text-[12vw] font-display text-white/5 font-black uppercase tracking-tighter leading-none select-none">CO-PO-PSO</h1>
           </div>
        </div>

        <Canvas shadows dpr={[1, 2]} className="z-20">
          <Scene />
        </Canvas>

        {/* Side HUD Stats */}
        <div className="absolute left-12 bottom-12 z-30 flex flex-col gap-8 pointer-events-none">
           <div>
              <p className="text-[10px] font-mono text-brand uppercase tracking-widest mb-1">Optical Engine</p>
              <p className="text-2xl font-display text-white">Refractive Glass v2</p>
           </div>
           <div>
              <p className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-1">Material Integrity</p>
              <div className="flex gap-2">
                 {[1,1,1,1,0.5].map((o,i) => <div key={i} className="w-1 h-4 bg-brand" style={{ opacity: o }} />)}
              </div>
           </div>
        </div>

        <div className="absolute right-12 bottom-12 z-30 text-right max-w-sm pointer-events-none">
           <p className="text-white/40 font-light text-sm leading-relaxed">
             Precisely reconstructed from institutional source imagery. The <span className="text-white underline underline-offset-4 decoration-brand/50">Y-Spoke hub</span> provides synchronous vector orientation for outcome mapping.
           </p>
        </div>
      </div>

      {/* Footer Controls */}
      <div className="z-10 px-12 py-10 bg-cosmic border-t border-white/5 flex items-center justify-between">
         <div className="flex gap-6">
            <button className="text-[10px] font-mono text-white/40 hover:text-white transition-colors uppercase tracking-widest">Toggle Wireframe</button>
            <button className="text-[10px] font-mono text-white/40 hover:text-white transition-colors uppercase tracking-widest">Cycle Lighting</button>
         </div>
         <div className="flex gap-4">
            <button className="px-10 py-4 border border-white/10 text-[10px] font-mono text-white/40 uppercase tracking-widest hover:border-white hover:text-white transition-all">
               Recalibrate Physics
            </button>
            <button className="px-10 py-4 bg-white text-black text-[10px] font-mono uppercase tracking-[0.4em] font-black hover:bg-brand hover:text-white transition-all">
               Deploy Core Identity
            </button>
         </div>
      </div>
      
      <style jsx global>{`
        @keyframes pulse-slow {
          0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.1; }
          50% { transform: translate(-50%, -50%) scale(1.05); opacity: 0.2; }
        }
        .animate-pulse-slow {
          animation: pulse-slow 8s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
