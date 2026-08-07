import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Leaf } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ProductCard } from "@/components/catalog/product-card";
import { ProductGridSkeleton } from "@/components/catalog/skeletons";
import { getSeasonal } from "@/lib/api/services";

export const Route = createFileRoute("/seasonal")({
  head: () => ({
    meta: [
      { title: "Seasonal Recommendations — CatalogIQ AI" },
      {
        name: "description",
        content: "Climate and trend signals turned into ready-to-merchandise seasonal collections.",
      },
      { property: "og:title", content: "Seasonal Recommendations — CatalogIQ AI" },
      { property: "og:description", content: "Season-aware collections from your catalog." },
    ],
  }),
  component: SeasonalPage,
});

const SEASONS = ["Spring", "Summer", "Autumn", "Winter"];

function SeasonalPage() {
  const [season, setSeason] = useState("Autumn");
  const data = useQuery({ queryKey: ["seasonal", season], queryFn: () => getSeasonal(season) });

  return (
    <AppShell title="Seasonal Recommendations" description="Climate and trend-aware collections">
      <div className="flex flex-wrap gap-2">
        {SEASONS.map((s) => (
          <Button
            key={s}
            variant={s === season ? "default" : "outline"}
            size="sm"
            onClick={() => setSeason(s)}
          >
            {s}
          </Button>
        ))}
      </div>

      <Card className="mt-6 flex-row items-start gap-3 p-5 shadow-card">
        <Leaf className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <h2 className="text-sm font-semibold">{season} edit</h2>
          <p className="text-sm text-muted-foreground">
            {data.data?.headline ?? "Loading seasonal signals…"}
          </p>
        </div>
      </Card>

      <div className="mt-6">
        {data.isPending ? (
          <ProductGridSkeleton count={4} />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.data?.items.map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        )}
      </div>
    </AppShell>
  );
}
