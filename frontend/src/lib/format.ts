/**
 * Türkçe biçimleme yardımcıları.
 *
 * Tüm sayısal ve tarihsel gösterim `tr-TR` yerel ayarıyla yapılır:
 *   %2,05 · 5.000 ₺ · 31.12.2026
 * Backend ISO 8601 döndürür; dönüşüm yalnızca gösterim katmanında yapılır.
 */

const numberFormatter = new Intl.NumberFormat("tr-TR");

const dateFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const currencyFormatter = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 2,
});

/** Tarih bulunmadığında gösterilen metin. Boş dize BIRAKILMAZ. */
export const NO_DATE_LABEL = "Belirtilmemiş";

/** Sayıyı Türkçe biçimde gösterir (1234 -> "1.234"). */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return numberFormatter.format(value);
}

/** ISO tarihini gg.aa.yyyy biçiminde gösterir. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return NO_DATE_LABEL;

  // Backend tarih alanlarını saat bilgisi olmadan (YYYY-MM-DD) döndürür.
  // Doğrudan Date'e verilirse UTC olarak yorumlanıp yerel saatte bir gün
  // kayabilir; bu yüzden parçalara ayrılarak yerel tarih kurulur.
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  const parsed = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(value);

  if (Number.isNaN(parsed.getTime())) return NO_DATE_LABEL;
  return dateFormatter.format(parsed);
}

/** ISO zaman damgasını gg.aa.yyyy ss:dd biçiminde gösterir. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return NO_DATE_LABEL;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return NO_DATE_LABEL;
  return dateTimeFormatter.format(parsed);
}

/** Oranı yüzde biçiminde gösterir (2.05 -> "%2,05"). */
export function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `%${numberFormatter.format(value)}`;
}

/** Tutarı Türk lirası biçiminde gösterir. */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return currencyFormatter.format(value);
}

/** Boş olabilen metinleri güvenle gösterir. */
export function formatText(value: string | null | undefined, fallback = "—"): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}
