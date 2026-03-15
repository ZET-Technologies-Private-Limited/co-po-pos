'use client';

import React from 'react';
import { AlertTriangle, X, Check } from 'lucide-react';

interface DeleteConfirmationDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  isDangerous?: boolean; // True for actual delete, false for other confirmations
}

/**
 * SF-09: Confirmation Dialog Component
 * Shows 'Are you sure? This cannot be undone.' before delete
 */
export const DeleteConfirmationDialog: React.FC<DeleteConfirmationDialogProps> = ({
  isOpen,
  onConfirm,
  onCancel,
  title = 'Confirm Delete',
  message = 'Are you sure? This cannot be undone.',
  confirmText = 'Delete',
  cancelText = 'Cancel',
  isDangerous = true,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-cosmic border border-white/10 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-5 h-5 text-alert flex-shrink-0" />
          <h2 className="text-lg font-semibold text-white">{title}</h2>
        </div>

        {/* Message */}
        <p className="text-white/70 mb-6 leading-relaxed">{message}</p>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors font-medium flex items-center gap-2"
          >
            <X className="w-4 h-4" />
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${
              isDangerous
                ? 'bg-alert hover:bg-alert/80 text-white'
                : 'bg-brand hover:bg-brand/80 text-white'
            }`}
          >
            <Check className="w-4 h-4" />
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DeleteConfirmationDialog;
