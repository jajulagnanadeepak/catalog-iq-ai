import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Package, Search, ShoppingBag, TrendingUp } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RecommendationCard } from "@/components/catalog/recommendation-card";
import { ProductCard } from "@/components/catalog/product-card";
import { ListSkeleton, ProductGridSkeleton } from "@/components/catalog/skeletons";
import { getProducts, getRecommendations } from "@/lib/api/services";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — CatalogIQ AI" },
      {
        name: "description",
        content: "Track catalog performance, AI recommendations and query volume in real time.",
      },
      { property: "og:title", content: "Dashboard — CatalogIQ AI" },
      { property: "og:description", content: "Catalog performance and AI recommendations." },
    ],
  }),
  component: DashboardPage,
});

const trend = [
  { day: "Mon", queries: 3200, conversions: 410 },
  { day: "Tue", queries: 4100, conversions: 520 },
  { day: "Wed", queries: 3800, conversions: 470 },
  { day: "Thu", queries: 5200, conversions: 690 },
  { day: "Fri", queries: 6100, conversions: 830 },
  { day: "Sat", queries: 7400, conversions: 990 },
  { day: "Sun", queries: 6800, conversions: 910 },
];

const stats = [
  { label: "AI queries", value: "36,842", delta: "+12.4%", icon: Search },
  { label: "Products indexed", value: "128,410", delta: "+1,204", icon: Package },
  { label: "Assisted revenue", value: "$412,980", delta: "+31.2%", icon: ShoppingBag },
  { label: "Conversion lift", value: "8.7%", delta: "+1.9pt", icon: TrendingUp },
];

function DashboardPage() {
  const recs = useQuery({ queryKey: ["recommend", 4], queryFn: () => getRecommendations(4) });
  const products = useQuery({
    queryKey: ["products", "dashboard"],
    queryFn: () => getProducts({ pageSize: 4, sort: "rating" }),
  });

  return (
    <AppShell
      title="Dashboard"
      description="Catalog intelligence overview for the last 7 days"
      actions={
        <Button asChild size="sm" className="hidden sm:inline-flex">
          <Link to="/search">Open search</Link>
        </Button>
      }
    >
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label} className="gap-2 p-5 shadow-card">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{s.label}</span>
              <s.icon className="size-4 text-primary" />
            </div>
            <p className="font-display text-2xl font-semibold">{s.value}</p>
            <p className="flex items-center gap-1 text-xs text-success">
              <ArrowUpRight className="size-3.5" />
              {s.delta} vs last week
            </p>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card className="gap-4 p-6 shadow-card">
          <div>
            <h2 className="text-base font-semibold">Query volume &amp; conversions</h2>
            <p className="text-xs text-muted-foreground">Semantic + visual search traffic</p>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ left: -18, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="q" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="c" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-chart-3)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="var(--color-chart-3)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="day" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-popover)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 12,
                    color: "var(--color-popover-foreground)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="queries"
                  stroke="var(--color-chart-1)"
                  fill="url(#q)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="conversions"
                  stroke="var(--color-chart-3)"
                  fill="url(#c)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold">AI recommendations</h2>
            <Button asChild variant="ghost" size="sm">
              <Link to="/seasonal">More</Link>
            </Button>
          </div>
          {recs.isPending ? (
            <ListSkeleton rows={4} />
          ) : (
            <div className="space-y-3">
              {recs.data?.map((r) => <RecommendationCard key={r.id} recommendation={r} />)}
            </div>
          )}
        </div>
      </div>

      <div className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">Top rated in catalog</h2>
          <Button asChild variant="ghost" size="sm">
            <Link to="/search">Browse catalog</Link>
          </Button>
        </div>
        {products.isPending ? (
          <ProductGridSkeleton count={4} />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {products.data?.items.map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        )}
      </div>
    </AppShell>
  );
}
