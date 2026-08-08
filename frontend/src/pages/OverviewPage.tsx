import { Building2, CalendarClock, CalendarX2, CircleHelp, Layers, Tag } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { StatCard } from "@/components/common/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime, formatNumber } from "@/lib/format";
import { useStats } from "@/hooks/useStats";
import type { BankCampaignCount } from "@/types/api";

export function OverviewPage() {
  const statsQuery = useStats();

  if (statsQuery.isError) {
    return <ErrorState error={statsQuery.error} onRetry={() => statsQuery.refetch()} />;
  }

  if (statsQuery.isPending) {
    return <LoadingState variant="cards" />;
  }

  const stats = statsQuery.data;
  const maxCount = Math.max(...stats.campaigns_by_bank.map((item) => item.count), 1);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-text-900">Genel Bakış</h1>
          <p className="mt-1 text-sm text-text-500">
            {formatNumber(stats.total_banks)} katılım bankası izleniyor,{" "}
            {formatNumber(stats.banks_with_data)} tanesinde kampanya verisi bulundu.
          </p>
        </div>

        <p className="text-sm text-text-500">
          Son güncelleme:{" "}
          <span className="tabular text-text-900">
            {stats.last_scrape_at ? formatDateTime(stats.last_scrape_at) : "Henüz kazıma yapılmadı"}
          </span>
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Toplam Banka" value={stats.total_banks} icon={Building2} />
        <StatCard label="Toplam Kampanya" value={stats.total_campaigns} icon={Layers} />
        <StatCard
          label="Aktif"
          value={stats.active_campaigns}
          icon={Tag}
          tone="active"
        />
        <StatCard
          label="Yaklaşan"
          value={stats.upcoming_campaigns}
          icon={CalendarClock}
          tone="upcoming"
        />
        <StatCard
          label="Süresi Dolan"
          value={stats.expired_campaigns}
          icon={CalendarX2}
          tone="expired"
        />
      </div>

      {/*
        ⚠️ "Tarih Yok" ayrı bir kart olarak gösterilir; "Süresi Dolan" ile
        BİRLEŞTİRİLMEZ. Tarihi bulunmayan kampanyayı süresi dolmuş göstermek
        yanlış bilgi olurdu.
      */}
      {stats.unknown_status_campaigns > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard
            label="Tarih Belirtilmemiş"
            value={stats.unknown_status_campaigns}
            icon={CircleHelp}
            tone="unknown"
            hint="Kaynakta tarih yok — süresi dolmuş değildir"
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Bankalara Göre Dağılım</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {stats.campaigns_by_bank.map((item) => (
            <BankBar key={item.bank_code} item={item} maxCount={maxCount} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

/** Basit HTML/CSS yatay bar — grafik kütüphanesi PART 4'te eklenecek (§10.3). */
function BankBar({ item, maxCount }: { item: BankCampaignCount; maxCount: number }) {
  const widthPercent = item.count === 0 ? 0 : Math.max((item.count / maxCount) * 100, 2);

  return (
    <div className="flex items-center gap-3">
      <span className="w-44 shrink-0 truncate text-sm text-text-900" title={item.bank_name}>
        {item.bank_name}
      </span>

      <div className="h-2.5 flex-1 overflow-hidden rounded-sm bg-neutral-50">
        <div
          className="h-full rounded-sm bg-brand-500 transition-[width] duration-150"
          style={{ width: `${widthPercent}%` }}
          role="img"
          aria-label={`${item.bank_name}: ${item.count} kampanya`}
        />
      </div>

      <span className="tabular w-10 shrink-0 text-right text-sm text-text-500">
        {formatNumber(item.count)}
      </span>
    </div>
  );
}
