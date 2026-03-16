"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Upload, Check, X, Loader2, ChevronDown, AlertCircle } from "lucide-react";

interface FileUploadSectionProps {
  title: string;
  description?: string;
  acceptedFormats: string[]; // e.g., [".pdf", ".xlsx", ".csv"]
  maxSizeMB?: number;
  onFileSelect: (file: File) => Promise<any>;
  onSuccess?: (result: any) => void;
  onError?: (error: string) => void;
  isOpen?: boolean;
  onToggle?: (open: boolean) => void;
}

export function FileUploadSection({
  title,
  description,
  acceptedFormats,
  maxSizeMB = 10,
  onFileSelect,
  onSuccess,
  onError,
  isOpen = false,
  onToggle,
}: FileUploadSectionProps) {
  const [isExpanded, setIsExpanded] = useState(isOpen);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);

  const handleToggle = () => {
    const newState = !isExpanded;
    setIsExpanded(newState);
    onToggle?.(newState);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const fileName = file.name.toLowerCase();
    const isValid = acceptedFormats.some(ext => fileName.endsWith(ext));

    if (!isValid) {
      const msg = `Only ${acceptedFormats.join(", ")} files are allowed.`;
      setError(msg);
      onError?.(msg);
      return;
    }

    // Validate file size
    if (file.size > maxSizeMB * 1024 * 1024) {
      const msg = `File size must be less than ${maxSizeMB} MB.`;
      setError(msg);
      onError?.(msg);
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);
    setUploadedFile(null);

    try {
      const result = await onFileSelect(file);
      setSuccess(true);
      setUploadedFile(file.name);
      onSuccess?.(result);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      const msg = typeof err?.message === "string" ? err.message : "File upload failed.";
      setError(msg);
      onError?.(msg);
    } finally {
      setUploading(false);
      // Reset file input
      e.target.value = "";
    }
  };

  return (
    <div className="bg-gradient-to-br from-white/10 to-white/5 rounded-lg border border-white/10 p-6">
      <button
        onClick={handleToggle}
        className="flex items-center justify-between w-full mb-4"
      >
        <div className="flex items-center gap-3">
          <Upload className="w-5 h-5 text-brand" />
          <div className="text-left">
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            {description && (
              <p className="text-white/40 text-sm">{description}</p>
            )}
          </div>
        </div>
        <ChevronDown 
          className={`w-5 h-5 text-white/40 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      {isExpanded && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }} 
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="space-y-4"
        >
          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex gap-3">
              <X className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 flex gap-3">
              <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
              <p className="text-green-300 text-sm">
                {uploadedFile} uploaded and processed successfully!
              </p>
            </div>
          )}

          {/* File Upload Area */}
          <div className="border-2 border-dashed border-white/20 rounded-lg p-8 text-center hover:border-brand/50 transition-colors cursor-pointer group">
            <label className="cursor-pointer">
              <input
                type="file"
                accept={acceptedFormats.join(",")}
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
              <div className="flex flex-col items-center gap-3">
                <Upload 
                  className={`w-8 h-8 ${
                    uploading 
                      ? 'text-white/40 animate-pulse' 
                      : 'text-brand group-hover:scale-110 transition-transform'
                  }`} 
                />
                <p className="text-white/60 text-sm font-medium">
                  {uploading ? "Processing file..." : "Click to upload or drag and drop"}
                </p>
                <p className="text-white/40 text-xs">
                  {acceptedFormats.join(", ")} • Max {maxSizeMB} MB
                </p>
              </div>
            </label>
          </div>

          {/* Info Box */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 flex gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-blue-300 text-sm">
              Upload files to automatically extract data and populate this workflow.
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
