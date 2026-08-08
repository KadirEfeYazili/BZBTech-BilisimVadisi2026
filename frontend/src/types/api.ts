/**
 * Backend Pydantic şemalarının TypeScript karşılıkları.
 *
 * ⚠️ `status` alanı BACKEND'de hesaplanır. Frontend bu değeri yalnızca
 * gösterir; tarihlerden yeniden hesaplamaz. Aksi hâlde iki taraf farklı
 * sonuç üretir ve kullanıcıya çelişkili bilgi gösterilir.
 */

/** Kampanya durumu. `unknown`, `expired`'dan AYRIDIR. */
export type CampaignStatus = "active" | "upcoming" | "expired" | "unknown";

/** Tarih çıkarımının güvenilirliği. */
export type DatePrecision = "exact" | "partial" | "inferred" | "unknown";

/** Bankanın kamuya açık veri zenginliği. */
export type DataStatus = "rich" | "limited" | "none";

export interface Bank {
  id: number;
  code: string;
  name: string;
  legal_name: string | null;
  website: string;
  bddk_status: string;
  tkbb_member: boolean;
  data_status: DataStatus;
  brand_color: string | null;
  notes: string | null;
  campaign_count: number;
}

export interface BankDetail extends Bank {
  legacy_domains: string[] | null;
}

export interface CampaignListItem {
  id: number;
  bank_code: string;
  bank_name: string;
  external_slug: string;
  title: string;
  category: string | null;
  segment: string | null;
  target_customer: string | null;
  /** Bilinmiyorsa null — tarih uydurulmaz. */
  start_date: string | null;
  end_date: string | null;
  date_precision: DatePrecision;
  status: CampaignStatus;
  source_url: string;
}

export interface SourceDocumentSummary {
  id: number;
  url: string;
  canonical_url: string | null;
  doc_type: string;
  http_status: number | null;
  fetched_at: string;
  scraper_name: string | null;
  scraper_version: string | null;
  raw_html_sha256: string | null;
}

export interface CampaignDetail extends CampaignListItem {
  description: string | null;
  conditions_text: string | null;
  exclusions_text: string | null;
  participation_method: string | null;
  participation_channel: string | null;
  sms_keyword: string | null;
  sms_number: string | null;
  coupon_code: string | null;
  is_archived: boolean;
  first_seen_at: string;
  last_seen_at: string;
  bank: Omit<Bank, "campaign_count">;
  source_document: SourceDocumentSummary | null;
}

/** Sayfalı liste yanıtı. Boş `items` bir hata değildir. */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BankCampaignCount {
  bank_code: string;
  bank_name: string;
  count: number;
}

export interface CategoryCount {
  category: string | null;
  count: number;
}

export interface Stats {
  total_banks: number;
  banks_with_data: number;
  total_campaigns: number;
  active_campaigns: number;
  upcoming_campaigns: number;
  expired_campaigns: number;
  /** Tarihi bulunamayan kampanyalar — "süresi dolmuş" değildir. */
  unknown_status_campaigns: number;
  campaigns_by_bank: BankCampaignCount[];
  campaigns_by_category: CategoryCount[];
  last_scrape_at: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  db_ok: boolean;
  campaign_count: number;
}

/** Backend'in tek biçimli hata gövdesi. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    detail: string | null;
  };
}

/** `GET /campaigns` sorgu parametreleri. */
export interface CampaignQuery {
  bank?: string[];
  category?: string;
  segment?: string;
  status?: CampaignStatus;
  q?: string;
  sort?: "title" | "start_date" | "end_date" | "bank";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}
