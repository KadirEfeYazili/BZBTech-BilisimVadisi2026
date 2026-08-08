import { useState } from "react";

import { CampaignFilters, type FilterState } from "@/components/campaigns/CampaignFilters";
import { CampaignTable } from "@/components/campaigns/CampaignTable";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useBanks } from "@/hooks/useBanks";
import { useCampaigns } from "@/hooks/useCampaigns";
import type { CampaignQuery } from "@/types/api";

const PAGE_SIZE = 25;
const EMPTY_FILTERS: FilterState = { banks: [], status: "all", q: "" };

export function CampaignsPage() {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [sort, setSort] = useState<NonNullable<CampaignQuery["sort"]>>("title");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);

  const banksQuery = useBanks();
  const campaignsQuery = useCampaigns({
    bank: filters.banks.length ? filters.banks : undefined,
    status: filters.status === "all" ? undefined : filters.status,
    q: filters.q || undefined,
    sort,
    order,
    page,
    page_size: PAGE_SIZE,
  });

  const handleFilterChange = (next: FilterState) => {
    setFilters(next);
    setPage(1); // Filtre değişince ilk sayfaya dön.
  };

  const handleSortChange = (field: NonNullable<CampaignQuery["sort"]>) => {
    if (field === sort) {
      setOrder(order === "asc" ? "desc" : "asc");
    } else {
      setSort(field);
      setOrder("asc");
    }
    setPage(1);
  };

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-text-900">Kampanyalar</h1>
        <p className="mt-1 text-sm text-text-500">
          Katılım bankalarının kamuya açık kampanya sayfalarından toplanan kayıtlar.
        </p>
      </header>

      <CampaignFilters
        banks={banksQuery.data ?? []}
        value={filters}
        onChange={handleFilterChange}
      />

      {/*
        ⚠️ Üç durum KESİN olarak ayrıdır (§10.4):
          isError                    -> ErrorState  ("Veriler yüklenemedi")
          isLoading                  -> LoadingState
          başarılı + items.length===0 -> EmptyState ("Filtrelere uyan kampanya bulunamadı")
        Sıralama önemlidir: hata kontrolü boş kontrolünden ÖNCE gelir.
      */}
      {campaignsQuery.isError ? (
        <ErrorState error={campaignsQuery.error} onRetry={() => campaignsQuery.refetch()} />
      ) : campaignsQuery.isPending ? (
        <LoadingState rows={10} />
      ) : campaignsQuery.data.items.length === 0 ? (
        <EmptyState onClear={() => handleFilterChange(EMPTY_FILTERS)} />
      ) : (
        <CampaignTable
          items={campaignsQuery.data.items}
          sort={sort}
          order={order}
          onSortChange={handleSortChange}
          page={campaignsQuery.data.page}
          pageSize={campaignsQuery.data.page_size}
          total={campaignsQuery.data.total}
          totalPages={campaignsQuery.data.total_pages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
