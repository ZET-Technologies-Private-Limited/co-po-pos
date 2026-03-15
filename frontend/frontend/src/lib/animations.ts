export const spring = {
  // For UI elements (fast, snappy)
  snappy: { type: "spring", stiffness: 500, damping: 30, mass: 1 },
  // For page transitions (smooth, elegant)
  smooth: { type: "spring", stiffness: 280, damping: 28, mass: 0.8 },
  // For large elements (slow, majestic)
  majestic: { type: "spring", stiffness: 180, damping: 24, mass: 1.2 },
  // For micro-interactions (barely noticeable but feels better)
  micro: { type: "spring", stiffness: 800, damping: 35, mass: 0.5 }
} as const;

// Stagger children animation
export const staggerContainer: any = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } }
};

export const fadeSlideUp: any = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: spring.smooth }
};
