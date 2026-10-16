import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Sparkles, SlidersHorizontal, RefreshCw } from "lucide-react";

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
      {
        property: "og:title",
        content: "Semantic Search — CatalogIQ AI",
      },
      {
        property: "og:description",
        content: "Natural-language product search over your catalog.",
      },
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

const DEFAULT_QUERY: ProductQuery = {
  page: 1,
  pageSize: 8,
  sort: "relevance",
};

function SearchPage() {
  const [query, setQuery] = useState("warm coat for rainy commutes under $300");
  const [filters, setFilters] = useState<ProductQuery>(DEFAULT_QUERY);

  const results = useQuery({
    queryKey: ["search", query, filters],
    queryFn: () => postSearch({ query, ...filters }),
    enabled: query.trim().length > 0,
  });

  const scoreOf = (id: string) =>
    results.data?.matches.find((match) => match.productId === id)?.score;

  const handleSearch = (value: string) => {
    const nextQuery = value.trim();
    if (!nextQuery) return;

    setQuery(nextQuery);
    setFilters((current) => ({ ...current, page: 1 }));
  };

  const handleReset = () => {
    setFilters(DEFAULT_QUERY);
  };

  // Defensive UI-level de-duplication. The API should still be fixed
  // if it returns duplicate products for the same search.
  const uniqueProducts = Array.from(
    new Map((results.data?.items ?? []).map((product) => [product.id, product])).values(),
  );

  return (
    <AppShell title="Semantic Search" description="Natural-language discovery across the catalog">
      <SearchBar
        defaultValue={query}
        onSearch={handleSearch}
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
            onChange={(nextFilters) => setFilters({ ...nextFilters, page: 1 })}
            onReset={handleReset}
          />
        </div>

        <div>
          <div className="mb-4 flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {results.isPending
                ? "Searching…"
                : results.isError
                  ? "Search unavailable"
                  : `${results.data?.total ?? 0} matches`}
            </p>

            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm" className="lg:hidden">
                  <SlidersHorizontal className="size-4" />
                  Filters
                </Button>
              </SheetTrigger>

              <SheetContent side="right" className="w-80 overflow-y-auto p-4">
                <SheetTitle>Search filters</SheetTitle>
                <Filters
                  value={filters}
                  onChange={(nextFilters) => setFilters({ ...nextFilters, page: 1 })}
                  onReset={handleReset}
                />
              </SheetContent>
            </Sheet>
          </div>

          {results.isPending ? (
            <ProductGridSkeleton count={8} />
          ) : results.isError ? (
            <Card className="flex flex-col items-center gap-3 p-12 text-center">
              <p className="font-medium">Unable to load search results</p>
              <p className="text-sm text-muted-foreground">
                Check your connection and backend server, then try again.
              </p>
              <Button variant="outline" onClick={() => void results.refetch()}>
                <RefreshCw className="size-4" />
                Retry search
              </Button>
            </Card>
          ) : uniqueProducts.length > 0 ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {uniqueProducts.map((product) => (
                  <ProductCard key={product.id} product={product} score={scoreOf(product.id)} />
                ))}
              </div>

              <Pagination
                page={results.data?.page ?? filters.page ?? 1}
                pageSize={results.data?.pageSize ?? filters.pageSize ?? 8}
                total={results.data?.total ?? 0}
                onChange={(page) => setFilters((current) => ({ ...current, page }))}
              />
            </>
          ) : (
            <Card className="items-center gap-2 p-12 text-center">
              <p className="font-medium">No matches found</p>
              <p className="text-sm text-muted-foreground">
                Try a different search or loosen the filters.
              </p>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
