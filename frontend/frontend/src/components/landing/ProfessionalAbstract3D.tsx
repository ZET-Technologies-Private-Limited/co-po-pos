"use client";

import { useRef, useMemo, useEffect } from "react";
import * as THREE from "three";

// A single glowing point shader
function ParticleBrainCloud() {
  const particlesRef = useRef<THREE.Points>(null);
  const linesRef = useRef<THREE.LineSegments>(null);
  const elapsedRef = useRef(0);
  const COUNT = 400;

  const { positions, connections } = useMemo(() => {
    // Distribute particles on a sphere surface (fibonacci distribution)
    const positions = new Float32Array(COUNT * 3);
    const phi = Math.PI * (3.0 - Math.sqrt(5.0)); // golden angle

    for (let i = 0; i < COUNT; i++) {
      const y = 1 - (i / (COUNT - 1)) * 2;
      const radius = Math.sqrt(1 - y * y);
      const theta = phi * i;

      const spread = 2.8;
      positions[i * 3] = Math.cos(theta) * radius * spread;
      positions[i * 3 + 1] = y * spread;
      positions[i * 3 + 2] = Math.sin(theta) * radius * spread;
    }

    // Build connections between nearby particles
    const linePositions: number[] = [];
    const MAX_DIST = 1.2;
    for (let i = 0; i < COUNT; i++) {
      for (let j = i + 1; j < COUNT; j++) {
        const ax = positions[i * 3], ay = positions[i * 3 + 1], az = positions[i * 3 + 2];
        const bx = positions[j * 3], by = positions[j * 3 + 1], bz = positions[j * 3 + 2];
        const dist = Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2);
        if (dist < MAX_DIST) {
          linePositions.push(ax, ay, az, bx, by, bz);
        }
      }
    }

    return { positions, connections: new Float32Array(linePositions) };
  }, []);

  const animationRef = useRef<number>();
  
  const animate = () => {
    elapsedRef.current += 0.016; // ~60fps
    const t = elapsedRef.current;
    if (particlesRef.current) {
      particlesRef.current.rotation.y = t * 0.08;
      particlesRef.current.rotation.x = Math.sin(t * 0.04) * 0.15;
    }
    if (linesRef.current) {
      linesRef.current.rotation.y = t * 0.08;
      linesRef.current.rotation.x = Math.sin(t * 0.04) * 0.15;
    }
    animationRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  const dotTexture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d")!;
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, "rgba(255,255,255,1)");
    gradient.addColorStop(0.3, "rgba(100,210,255,0.8)");
    gradient.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(canvas);
  }, []);

  return (
    <>
      {/* Particle points */}
      <points ref={particlesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[positions, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.06}
          map={dotTexture}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          color="#7DD3FC"
          opacity={0.9}
        />
      </points>

      {/* Connection lines */}
      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[connections, 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color="#1E40AF"
          transparent
          opacity={0.15}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>

      {/* Ambient glowing core */}
      <mesh>
        <sphereGeometry args={[1.0, 32, 32]} />
        <meshStandardMaterial
          color="#06B6D4"
          emissive="#06B6D4"
          emissiveIntensity={0.2}
          transparent
          opacity={0.04}
        />
      </mesh>
    </>
  );
}

export default function ProfessionalAbstract3D() {
  return (
    <>
      <ambientLight intensity={0.1} />
      <pointLight position={[5, 5, 5]} intensity={1} color="#06B6D4" />
      <pointLight position={[-5, -5, -5]} intensity={0.5} color="#7C3AED" />
      <ParticleBrainCloud />
    </>
  );
}
