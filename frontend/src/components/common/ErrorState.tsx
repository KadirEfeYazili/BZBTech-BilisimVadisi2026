import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/**
 * API HATASI bileşeni.
 *
 * ⚠️ Bu bileşen `EmptyState` ile ASLA karıştırılmaz. API çöktüğünde kullanıcıya
 * "kampanya bulunamadı" demek, verinin gerçekten yok olduğu izlenimini yaratır
 * ve bu projede kabul edilemez bir hata sınıfıdır (§10.4).
 */
export function ErrorState({ error, onRetry, title = "Veriler yüklenemedi" }: ErrorStateProps) {
  const message =
    error instanceof ApiError
      ? error.message
      : "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.";
  const code = error instanceof ApiError ? error.code : null;

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-danger-600/30 bg-surface px-6 py-12 text-center"
    >
      <AlertTriangle className="h-6 w-6 text-danger-600" aria-hidden="true" />

      <div>
        <p className="font-semibold text-text-900">{title}</p>
        <p className="mt-1 text-sm text-text-500">{message}</p>
        {code && <p className="mt-1 text-xs text-text-500">Hata kodu: {code}</p>}
      </div>

      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Tekrar Dene
        </Button>
      )}
    </div>
  );
}
