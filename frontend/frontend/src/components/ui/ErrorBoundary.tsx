"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";

interface Props { children: React.ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-8" role="alert" aria-live="assertive">
        <div className="max-w-md w-full bg-[#0D1829] border border-alert/20 p-8 flex flex-col items-center gap-6 text-center">
          <div className="w-16 h-16 rounded-full bg-alert/10 flex items-center justify-center">
            <AlertTriangle className="w-7 h-7 text-alert" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-white font-display text-2xl mb-2">Something went wrong</h2>
            <p className="text-white/50 text-sm font-light">
              An unexpected error occurred. Please try again or contact support if the issue persists.
            </p>
            {this.state.error?.message && (
              <p className="mt-3 text-[10px] font-mono text-white/20 bg-white/5 px-3 py-2 rounded">
                {this.state.error.message}
              </p>
            )}
          </div>
          <div className="flex gap-3 w-full">
            <button
              onClick={() => this.setState({ hasError: false, error: undefined })}
              className="flex-1 py-3 bg-brand text-white text-sm font-medium hover:bg-brand/80 transition-colors focus:outline-none focus:ring-2 focus:ring-brand"
            >
              Retry
            </button>
            <a
              href="mailto:support@nexus.edu"
              className="flex-1 py-3 border border-white/10 text-white/60 text-sm text-center hover:text-white hover:border-white/30 transition-colors focus:outline-none focus:ring-2 focus:ring-white/20"
            >
              Contact Support
            </a>
          </div>
        </div>
      </div>
    );
  }
}
