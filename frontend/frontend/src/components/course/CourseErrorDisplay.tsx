import Link from "next/link";

interface CourseErrorDisplayProps {
  title?: string;
  message: string;
  showBackButton?: boolean;
  suggestion?: string;
}

export function CourseErrorDisplay({
  title = "⚠ Course Not Found",
  message,
  showBackButton = true,
  suggestion,
}: CourseErrorDisplayProps) {
  return (
    <div className="w-full flex items-center justify-center p-8">
      <div className="max-w-md">
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-6 mb-6">
          <h2 className="text-lg font-semibold text-red-400 mb-2">{title}</h2>
          <p className="text-sm text-white/70 mb-4">{message}</p>
          {suggestion && <p className="text-xs text-white/50 mb-4">{suggestion}</p>}
          {showBackButton && (
            <Link
              href="/faculty/dashboard"
              className="inline-block px-4 py-2 bg-brand text-white text-sm rounded hover:bg-brand/90 transition"
            >
              ← Back to Dashboard
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
