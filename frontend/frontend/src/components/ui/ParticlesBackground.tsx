"use client";

import { useEffect, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { type Container, type ISourceOptions } from "@tsparticles/engine";
import { loadSlim } from "@tsparticles/slim"; // We use loadSlim for lightweight particles

export function ParticlesBackground() {
  const [init, setInit] = useState(false);

  useEffect(() => {
    initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  const options: ISourceOptions = {
    background: {
      color: {
        value: "transparent",
      },
    },
    fpsLimit: 120,
    interactivity: {
      events: {
        onHover: {
          enable: true,
          mode: "grab",
        },
      },
      modes: {
        grab: {
          distance: 140,
          links: {
            opacity: 0.8,
            color: "#06B6D4"
          }
        },
      },
    },
    particles: {
      color: {
        value: ["#06B6D4", "#7C3AED", "#1D4ED8"],
      },
      links: {
        color: "#ffffff",
        distance: 150,
        enable: true,
        opacity: 0.1,
        width: 1,
      },
      move: {
        direction: "none",
        enable: true,
        outModes: {
          default: "bounce",
        },
        random: false,
        speed: 1.2,
        straight: false,
      },
      number: {
        density: {
          enable: true,
          width: 800,
          height: 800,
        },
        value: 120, // 120 nodes as requested
      },
      opacity: {
        value: 0.5,
      },
      shape: {
        type: "circle",
      },
      size: {
        value: { min: 1, max: 3 },
      },
    },
    detectRetina: true,
  };

  if (init) {
    return (
      <Particles
        id="tsparticles"
        options={options}
        className="absolute inset-0 z-0"
      />
    );
  }

  return null;
}
