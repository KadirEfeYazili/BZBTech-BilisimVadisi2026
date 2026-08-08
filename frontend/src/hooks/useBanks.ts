import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Banka listesi. Kampanyası olmayan bankalar da döner (campaign_count=0). */
export function useBanks() {
  return useQuery({
    queryKey: ["banks"],
    queryFn: () => api.banks(),
    retry: 1,
    // Banka listesi nadiren değişir; daha uzun süre taze sayılır.
    staleTime: 5 * 60_000,
  });
}
