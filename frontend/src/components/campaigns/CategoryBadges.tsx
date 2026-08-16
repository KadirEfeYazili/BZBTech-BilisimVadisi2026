import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { CampaignCategory, TaxonomyAxis } from "@/types/api";

/**
 * Kontrollü sözlük değerlerinin Türkçe karşılıkları.
 *
 * Veritabanında slug tutulur (`market_gida`); kullanıcıya okunur ad gösterilir.
 * Karşılığı olmayan bir değer gelirse slug olduğu gibi gösterilir — sessizce
 * gizlemek, sınıflandırmanın yeni bir değer ürettiğini fark etmemize engel olur.
 */
const LABELS: Record<string, string> = {
  // sector
  market_gida: "Market ve Gıda",
  akaryakit: "Akaryakıt",
  giyim_aksesuar: "Giyim ve Aksesuar",
  elektronik_telekom: "Elektronik",
  beyaz_esya_ev: "Beyaz Eşya",
  mobilya_dekorasyon: "Mobilya",
  yapi_hirdavat: "Yapı ve Hırdavat",
  kuyum_optik_saat: "Kuyum ve Optik",
  eticaret_pazaryeri: "E-ticaret",
  seyahat_konaklama: "Seyahat",
  ulasim_arac_kiralama: "Ulaşım",
  restoran_kafe: "Restoran",
  eglence_dijital: "Eğlence ve Dijital",
  egitim_kitap: "Eğitim ve Kitap",
  saglik_kozmetik: "Sağlık ve Kozmetik",
  hobi_oyuncak_spor: "Hobi ve Spor",
  vergi_fatura_kamu: "Vergi ve Fatura",
  yatirim_birikim: "Yatırım",
  konut_gayrimenkul: "Konut",
  kurumsal_kobi: "Kurumsal / KOBİ",
  genel: "Genel",
  // product_type
  finansman: "Finansman",
  ihtiyac_finansmani: "İhtiyaç Finansmanı",
  konut_finansmani: "Konut Finansmanı",
  tasit_finansmani: "Taşıt Finansmanı",
  kart: "Kart",
  alisveris_puani: "Alışveriş Puanı",
  yeni_musteri: "Yeni Müşteri",
  yatirim_urunu: "Yatırım Ürünü",
  birikim_katilma_hesabi: "Katılma Hesabı",
  sigorta: "Sigorta",
  pos_uye_isyeri: "POS / Üye İşyeri",
  dijital_bankacilik: "Dijital Bankacılık",
  odeme_fatura: "Ödeme ve Fatura",
  kobi_ticari: "KOBİ / Ticari",
  isyeri_finansmani: "İşyeri Finansmanı",
  // benefit
  nakit_iade: "Nakit İade",
  puan_mil: "Puan / Mil",
  taksit: "Taksit",
  vade_farksiz_taksit: "Vade Farksız Taksit",
  indirim: "İndirim",
  hediye_ceki: "Hediye Çeki",
  ucret_muafiyeti: "Ücret Muafiyeti",
  masrafsiz: "Masrafsız",
  avantajli_kar_payi: "Avantajlı Kâr Payı",
  hediye_urun: "Hediye Ürün",
  cekilis: "Çekiliş",
};

const SOURCE_LABELS: Record<string, string> = {
  url: "adres yolundan (bankanın verisi)",
  bank_category: "bankanın kendi etiketi",
  merchant: "marka eşleşmesi",
  keyword: "anahtar kelime",
  llm: "yapay zekâ çıkarımı",
};

/**
 * ⚠️ Düşük güvenli etiket GİZLENMEZ, ayrı gösterilir.
 *
 * Sektörü çıkarılamayan kampanyalara `genel` etiketi 0.30 güvenle yazılıyor.
 * Bunu diğerleriyle aynı biçimde göstermek "sınıflandırıldı" izlenimi verir;
 * gizlemek ise kampanyayı etiketsiz gösterir. İkisi de yanlış — soluk
 * gösterilir ve nedeni ipucunda yazar.
 */
const LOW_CONFIDENCE = 0.5;

function labelOf(value: string): string {
  return LABELS[value] ?? value;
}

interface CategoryBadgesProps {
  categories: CampaignCategory[];
  /** Gösterilecek eksen. Verilmezse tüm eksenler gösterilir. */
  axis?: TaxonomyAxis;
  /** En fazla kaç etiket gösterilsin; gerisi "+N" olarak özetlenir. */
  max?: number;
  className?: string;
}

/**
 * Kampanyanın taksonomi etiketlerini rozet olarak gösterir.
 *
 * Her rozetin ipucunda kanıt bulunur: etiket hangi kaynaktan ve hangi metinden
 * çıkarıldı. Kaynaksız etiket bankacılıkta kabul edilemez, bu yüzden kanıt
 * arayüzde de erişilebilir durur.
 */
export function CategoryBadges({
  categories,
  axis,
  max = 3,
  className,
}: CategoryBadgesProps) {
  const filtered = axis
    ? categories.filter((category) => category.axis === axis)
    : categories;

  if (filtered.length === 0) {
    // Sınıflandırma henüz çalıştırılmamış olabilir; boş göstermek yanıltır.
    return <span className="text-text-400">Sınıflandırılmadı</span>;
  }

  const shown = filtered.slice(0, max);
  const rest = filtered.length - shown.length;

  return (
    <div className={cn("flex flex-wrap items-center gap-1", className)}>
      {shown.map((category) => {
        const weak = Number(category.confidence) < LOW_CONFIDENCE;
        return (
          <Tooltip key={`${category.axis}-${category.value}`}>
            <TooltipTrigger asChild>
              <span
                className={cn(
                  "inline-flex items-center rounded border px-1.5 py-0.5 text-xs",
                  weak
                    ? "border-dashed border-border text-text-400"
                    : "border-border bg-surface-100 text-text-700",
                )}
              >
                {labelOf(category.value)}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <div className="max-w-xs space-y-1">
                <div>
                  Kaynak: {SOURCE_LABELS[category.source] ?? category.source} · güven{" "}
                  {Number(category.confidence).toFixed(2)}
                </div>
                {category.evidence && (
                  <div className="text-text-400">“{category.evidence}”</div>
                )}
                {weak && (
                  <div className="text-text-400">
                    Sektör çıkarılamadı; sonraki aşamada yeniden değerlendirilecek.
                  </div>
                )}
              </div>
            </TooltipContent>
          </Tooltip>
        );
      })}
      {rest > 0 && <span className="text-xs text-text-400">+{rest}</span>}
    </div>
  );
}
