import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Sparkles, SlidersHorizontal } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { SearchBar } from "@/components/catalog/search-bar";
import { Filters } from "@/components/catalog/filters";
import { ProductCard } from "@/components/catalog/product-card";
import { ProductGridSkeleton } from "@/components/catalog/skeletons";
import { Pagination } from "@/components/catalog/pagination";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { postSearch } from "@/lib/api/services";
import type { ProductQuery } from "@/lib/api/types";

export const Route = createFileRoute("/search")({
  head: () => ({
    meta: [
      { title: "Semantic Search — CatalogIQ AI" },
      {
        name: "description",
        content:
          "Search the catalog in natural language. CatalogIQ AI resolves intent, filters and ranks by semantic similarity.",
      },
      { property: "og:title", content: "Semantic Search — CatalogIQ AI" },
      { property: "og:description", content: "Natural-language product search over your catalog." },
    ],
  }),
  component: SearchPage,
});

const SUGGESTIONS = [
  "warm coat for rainy commutes under $300",
  "minimal white sneakers for everyday",
  "gift for a friend who loves ceramics",
  "office-appropriate but comfortable",
];

const DEFAULT_QUERY: ProductQuery = { page: 1, pageSize: 8, sort: "relevance" };

function SearchPage() {
  const [query, setQuery] = useState("warm coat for rainy commutes under $300");
  const [filters, setFilters] = useState<ProductQuery>(DEFAULT_QUERY);

  const results = useQuery({
    queryKey: ["search", query, filters],
    queryFn: () => postSearch({ query, ...filters }),
  });

  const scoreOf = (id: string) =>
    results.data?.matches.find((m) => m.productId === id)?.score ?? undefined;

  return (
    <AppShell title="Semantic Search" description="Natural-language discovery across the catalog">
      <SearchBar
        defaultValue={query}
        onSearch={(v) => {
          setQuery(v);
          setFilters((f) => ({ ...f, page: 1 }));
        }}
        suggestions={SUGGESTIONS}
        loading={results.isFetching}
      />

      {results.data && (
        <Card className="mt-5 flex-row items-start gap-3 p-4 shadow-card">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
          <p className="text-sm text-muted-foreground">{results.data.interpretation}</p>
        </Card>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[260px_1fr]">
        <div className="hidden lg:block">
          <Filters
            value={filters}
            onChange={setFilters}
            onReset={() => setFilters(DEFAULT_QUERY)}
          />
        </div>

        <div>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {results.data ? `${results.data.total} matches` : "Searching…"}
            </p>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm" className="lg:hidden">
                  <SlidersHorizontal className="size-4" /> Filters
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-80 overflow-y-auto p-4">
                <SheetTitle className="sr-only">Filters</SheetTitle>
                <Filters
                  value={filters}
                  onChange={setFilters}
                  onReset={() => setFilters(DEFAULT_QUERY)}
                />
              </SheetContent>
            </Sheet>
          </div>

          {results.isPending ? (
            <ProductGridSkeleton count={8} />
          ) : results.data && results.data.items.length > 0 ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {results.data.items.map((p) => (
                  <ProductCard key={p.id} product={p} score={scoreOf(p.id)} />
                ))}
              </div>
              <Pagination
                page={results.data.page}
                pageSize={results.data.pageSize}
                total={results.data.total}
                onChange={(page) => setFilters((f) => ({ ...f, page }))}
              />
            </>
          ) : (
            <Card className="items-center gap-2 p-12 text-center">
              <p className="font-medium">No matches</p>
              <p className="text-sm text-muted-foreground">
                Try loosening the filters or rephrasing your query.
              </p>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
