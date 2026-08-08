import type { ReactNode } from "react";

import { Sidebar } from "@/components/layout/Sidebar";

/** Uygulama kabuğu: sabit kenar çubuğu + kaydırılabilir içerik alanı. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-neutral-50">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden p-6">
        <div className="mx-auto max-w-7xl">{children}</div>
      </main>
    </div>
  );
}
