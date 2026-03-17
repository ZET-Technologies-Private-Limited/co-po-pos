"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useUIStore } from "@/lib/uiStore";
import { CheckCircle2, AlertTriangle, Info, X, AlertCircle } from "lucide-react";

const ICONS = {
  success: <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />,
  error: <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />,
  info: <Info className="w-4 h-4 text-blue-600 shrink-0" />,
  warning: <AlertTriangle className="w-4 h-4 text-yellow-600 shrink-0" />,
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
            className={`flex items-start gap-3 px-5 py-3 bg-white shadow-lg pointer-events-auto rounded-lg ${
              toast.type === "error"
                ? "border border-red-200"
                : toast.type === "success"
                  ? "border border-green-200"
                  : toast.type === "warning"
                    ? "border border-yellow-200"
                    : "border border-gray-200"
            }`}
          >
            {ICONS[toast.type]}
            <div className="flex-1">
              <span className="text-gray-800 text-sm font-light block">{toast.message}</span>
              {toast.type === "error" && <span className="mt-1 block text-[10px] font-mono uppercase tracking-widest text-red-600">Dismiss manually</span>}
            </div>
            <button onClick={() => removeToast(toast.id)} className="text-gray-400 hover:text-gray-900 transition-colors ml-2 shrink-0">
              <X className="w-3 h-3" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
