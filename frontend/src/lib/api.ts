/**
 * Tipli API istemcisi.
 *
 * ⚠️ KRİTİK KURAL (§10.4): Ağ hatası ve 4xx/5xx yanıtları `ApiError` fırlatır;
 * boş sonuç ASLA hata değildir. Bu ayrım sayesinde arayüz "veri alınamadı" ile
 * "sonuca uyan kayıt yok" durumlarını karıştırmaz. API çöktüğünde kullanıcıya
 * "kampanya yok" demek, bu projede kabul edilemez bir hata sınıfıdır.
 */

import type {
  ApiErrorBody,
  Bank,
  BankDetail,
  CampaignDetail,
  CampaignListItem,
  CampaignQuery,
  HealthResponse,
  Page,
  Stats,
} from "@/types/api";

const API_BASE = "/api/v1";

/** API'den dönen veya ağ katmanında oluşan hata. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: string | null;

  constructor(status: number, code: string, message: string, detail: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }

  /** Ağa hiç ulaşılamadığında (sunucu kapalı, DNS hatası) üretilir. */
  static network(cause: unknown): ApiError {
    return new ApiError(
      0,
      "NETWORK_ERROR",
      "Sunucuya ulaşılamadı. Bağlantınızı kontrol edip tekrar deneyin.",
      cause instanceof Error ? cause.message : String(cause),
    );
  }
}

/** Sorgu parametrelerini URL'e çevirir; boş değerler atlanır. */
function buildQueryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;

    if (Array.isArray(value)) {
      // Çoklu seçim: ?bank=a&bank=b
      for (const item of value) {
        if (item !== undefined && item !== null && item !== "") {
          search.append(key, String(item));
        }
      }
      continue;
    }
    search.append(key, String(value));
  }

  const queryString = search.toString();
  return queryString ? `?${queryString}` : "";
}

async function request<T>(path: string): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch (cause) {
    throw ApiError.network(cause);
  }

  if (!response.ok) {
    // Backend tek biçimli hata gövdesi döndürür; okunamazsa durum koduna düşülür.
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }

    throw new ApiError(
      response.status,
      body?.error?.code ?? "HTTP_ERROR",
      body?.error?.message ?? `İstek başarısız oldu (HTTP ${response.status})`,
      body?.error?.detail ?? null,
    );
  }

  try {
    return (await response.json()) as T;
  } catch (cause) {
    throw new ApiError(response.status, "INVALID_JSON", "Sunucu yanıtı okunamadı", String(cause));
  }
}

export const api = {
  health: (): Promise<HealthResponse> => request<HealthResponse>("/health"),

  banks: (): Promise<Bank[]> => request<Bank[]>("/banks"),

  bank: (code: string): Promise<BankDetail> => request<BankDetail>(`/banks/${code}`),

  campaigns: (query: CampaignQuery = {}): Promise<Page<CampaignListItem>> =>
    request<Page<CampaignListItem>>(`/campaigns${buildQueryString({ ...query })}`),

  campaign: (id: number): Promise<CampaignDetail> => request<CampaignDetail>(`/campaigns/${id}`),

  stats: (): Promise<Stats> => request<Stats>("/stats"),
};
