// This layout intentionally left minimal — the (app)/layout.tsx handles
// standalone bypass for /faculty/course/new via STANDALONE_PATHS.
export default function CreateCourseLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
