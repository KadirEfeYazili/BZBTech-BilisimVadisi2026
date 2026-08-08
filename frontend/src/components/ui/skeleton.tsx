import { cn } from "@/lib/utils";

/** Yükleniyor iskeleti. Spinner yerine içerik biçimini taklit eder. */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("skeleton-pulse rounded bg-border", className)}
      aria-hidden="true"
      {...props}
    />
  );
}
