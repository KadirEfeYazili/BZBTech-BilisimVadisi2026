import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { CampaignStatus, DatePrecision } from "@/types/api";

interface StatusBadgeProps {
  status: CampaignStatus;
  datePrecision?: DatePrecision;
}

const STATUS_LABELS: Record<CampaignStatus, string> = {
  active: "Aktif",
  upcoming: "Yaklaşan",
  expired: "Süresi Doldu",
  unknown: "Tarih Yok",
};

const STATUS_TOOLTIPS: Record<CampaignStatus, string> = {
  active: "Kampanya şu anda geçerli.",
  upcoming: "Kampanya henüz başlamadı.",
  expired: "Kampanyanın bitiş tarihi geçti.",
  // ⚠️ Bu metin bilinçli olarak "süresi doldu"dan farklıdır.
  unknown:
    "Kaynak sayfada tarih belirtilmemiş. Kampanya bitmiş olabilir de olmayabilir de — " +
    "bu bir 'süresi doldu' bilgisi DEĞİLDİR.",
};

const PRECISION_NOTES: Partial<Record<DatePrecision, string>> = {
  partial: "Tarihlerden yalnızca biri kaynakta belirtilmiş.",
  inferred: "Başlangıç yılı bitiş tarihinden çıkarsanmıştır.",
};

/**
 * Kampanya durumu rozeti.
 *
 * ⚠️ `unknown` durumu `expired`dan hem RENK hem METİN olarak ayrıdır.
 * Türkiye Finans'ın hiçbir kampanyasında tarih bulunmuyor; bunları
 * "süresi dolmuş" göstermek yanlış bilgi üretirdi (§10.3).
 */
export function StatusBadge({ status, datePrecision }: StatusBadgeProps) {
  const precisionNote = datePrecision ? PRECISION_NOTES[datePrecision] : undefined;
  const tooltip = [STATUS_TOOLTIPS[status], precisionNote].filter(Boolean).join(" ");

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant={status} tabIndex={0}>
          {STATUS_LABELS[status]}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{tooltip}</TooltipContent>
    </Tooltip>
  );
}
