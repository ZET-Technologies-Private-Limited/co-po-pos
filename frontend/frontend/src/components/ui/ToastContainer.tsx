"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useUIStore } from "@/lib/uiStore";
import { CheckCircle2, AlertTriangle, Info, X, AlertCircle } from "lucide-react";

const ICONS = {
  success: <CheckCircle2 className="w-4 h-4 text-attain shrink-0" />,
  error: <AlertCircle className="w-4 h-4 text-alert shrink-0" />,
  info: <Info className="w-4 h-4 text-brand shrink-0" />,
  warning: <AlertTriangle className="w-4 h-4 text-aurora shrink-0" />,
};

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore();

  return (
    <div className="fixed bottom-4 left-4 right-4 z-[200] flex flex-col gap-3 items-stretch pointer-events-none sm:left-auto sm:right-6 sm:w-[360px]">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 28 }}
            role={toast.type === "error" ? "alert" : "status"}
            className={`flex items-start gap-3 px-5 py-3 bg-[#1E293B] shadow-2xl pointer-events-auto ${
              toast.type === "error"
                ? "border border-alert/30"
                : toast.type === "success"
                  ? "border border-attain/20"
                  : toast.type === "warning"
                    ? "border border-aurora/30"
                    : "border border-white/10"
            }`}
          >
            {ICONS[toast.type]}
            <div className="flex-1">
              <span className="text-white/80 text-sm font-light block">{toast.message}</span>
              {toast.type === "error" && <span className="mt-1 block text-[10px] font-mono uppercase tracking-widest text-alert/70">Dismiss manually</span>}
            </div>
            <button onClick={() => removeToast(toast.id)} className="text-white/30 hover:text-white transition-colors ml-2 shrink-0">
              <X className="w-3 h-3" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
