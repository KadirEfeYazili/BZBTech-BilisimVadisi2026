import { SearchX } from "lucide-react";

import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  title?: string;
  description?: string;
  onClear?: () => void;
}

/**
 * SONUÇ YOK bileşeni.
 *
 * ⚠️ Yalnızca istek BAŞARILI olduğunda ve sonuç kümesi boş olduğunda gösterilir.
 * Hata durumunda `ErrorState` kullanılır (§10.4).
 */
export function EmptyState({
  title = "Filtrelere uyan kampanya bulunamadı",
  description = "Farklı bir banka, durum veya arama terimi deneyebilirsiniz.",
  onClear,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-border bg-surface px-6 py-12 text-center">
      <SearchX className="h-6 w-6 text-text-500" aria-hidden="true" />

      <div>
        <p className="font-semibold text-text-900">{title}</p>
        <p className="mt-1 text-sm text-text-500">{description}</p>
      </div>

      {onClear && (
        <Button variant="secondary" size="sm" onClick={onClear}>
          Filtreleri Temizle
        </Button>
      )}
    </div>
  );
}
