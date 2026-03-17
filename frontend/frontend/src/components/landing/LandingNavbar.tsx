"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { BrainCircuit } from "lucide-react";

export function LandingNavbar() {
  return (
    <motion.nav 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="w-full max-w-7xl mx-auto px-6 py-8 flex items-center justify-between"
    >
      <div className="flex items-center gap-3">
        <BrainCircuit className="w-6 h-6 text-blue-600" />
        <span className="font-display font-medium text-gray-900 tracking-widest uppercase text-sm">AI Platform</span>
      </div>
      
      <div className="hidden md:flex items-center gap-12 text-sm text-gray-600 tracking-wide font-light uppercase">
        <a href="#platform" className="hover:text-gray-900 transition-colors">Platform</a>
        <a href="#solutions" className="hover:text-gray-900 transition-colors">Solutions</a>
        <a href="#accreditation" className="hover:text-gray-900 transition-colors">Accreditation</a>
      </div>
      
      <div className="flex items-center gap-6">
        <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900 transition-colors uppercase tracking-wide font-light hidden md:block">
          Sign In
        </Link>
        <Link href="/login" className="px-6 py-2 border border-blue-600 text-blue-600 text-sm font-medium hover:bg-blue-600 hover:text-white transition-all uppercase tracking-wide">
          Portal
        </Link>
      </div>
    </motion.nav>
  );
}
