import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { CampaignQuery } from "@/types/api";

/**
 * Kampanya listesi sorgusu.
 *
 * `retry: 1` ve `staleTime: 30s` (§10.4). Hata durumunda TanStack Query
 * `isError` döndürür; bileşen bunu `ErrorState` ile gösterir — boş listeyle
 * karıştırmaz.
 */
export function useCampaigns(query: CampaignQuery) {
  return useQuery({
    queryKey: ["campaigns", query],
    queryFn: () => api.campaigns(query),
    retry: 1,
    staleTime: 30_000,
    // Sayfa değişiminde tablo boşalmasın, önceki veri gösterilsin.
    placeholderData: (previous) => previous,
  });
}

export function useCampaign(id: number | null) {
  return useQuery({
    queryKey: ["campaign", id],
    queryFn: () => api.campaign(id as number),
    enabled: id !== null,
    retry: 1,
    staleTime: 30_000,
  });
}
