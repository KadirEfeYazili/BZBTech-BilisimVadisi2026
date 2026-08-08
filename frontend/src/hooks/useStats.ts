import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Gösterge paneli istatistikleri. */
export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: () => api.stats(),
    retry: 1,
    staleTime: 30_000,
  });
}
