import { Skeleton } from "@/components/ui/skeleton";

interface LoadingStateProps {
  /** İskelet satır sayısı. */
  rows?: number;
  /** Tablo yerine kart ızgarası iskeleti gösterir. */
  variant?: "table" | "cards";
}

/**
 * YÜKLENİYOR bileşeni.
 *
 * Spinner yerine içeriğin biçimini taklit eden iskelet kullanılır: sayfa
 * yerleşimi yüklenme sırasında zıplamaz.
 */
export function LoadingState({ rows = 8, variant = "table" }: LoadingStateProps) {
  if (variant === "cards") {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5" aria-busy="true" aria-live="polite">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="rounded-lg border border-border bg-surface p-4">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-3 h-7 w-16" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className="overflow-hidden rounded-lg border border-border bg-surface"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="h-10 border-b border-border bg-neutral-50" />
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex h-row items-center gap-4 border-b border-border px-3">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-3 flex-1" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-16" />
        </div>
      ))}
      <span className="sr-only">Veriler yükleniyor</span>
    </div>
  );
}
