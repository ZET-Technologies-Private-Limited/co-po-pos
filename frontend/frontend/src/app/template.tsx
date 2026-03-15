"use client";

import { motion } from "framer-motion";
import { spring } from "@/lib/animations";
import { usePathname } from "next/navigation";

export default function Template({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  
  return (
    <motion.div
      key={pathname}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={spring.smooth}
      className="min-h-screen relative"
    >
      {children}
    </motion.div>
  );
}
