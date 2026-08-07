import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATEGORIES } from "@/lib/api/mock";
import type { ProductQuery } from "@/lib/api/types";

export function Filters({
  value,
  onChange,
  onReset,
}: {
  value: ProductQuery;
  onChange: (next: ProductQuery) => void;
  onReset: () => void;
}) {
  const maxPrice = value.maxPrice ?? 700;

  return (
    <Card className="h-fit gap-5 p-5 shadow-card">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Filters</h2>
        <Button variant="ghost" size="sm" onClick={onReset}>
          Reset
        </Button>
      </div>

      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Category</Label>
        <Select
          value={value.category ?? "All"}
          onValueChange={(category) => onChange({ ...value, category, page: 1 })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All categories</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground">Max price</Label>
          <Badge variant="secondary">${maxPrice}</Badge>
        </div>
        <Slider
          value={[maxPrice]}
          min={40}
          max={700}
          step={10}
          onValueChange={([v]) => onChange({ ...value, maxPrice: v ?? 700, page: 1 })}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground">Minimum rating</Label>
          <Badge variant="secondary">{(value.minRating ?? 0).toFixed(1)}★</Badge>
        </div>
        <Slider
          value={[value.minRating ?? 0]}
          min={0}
          max={5}
          step={0.1}
          onValueChange={([v]) => onChange({ ...value, minRating: v ?? 0, page: 1 })}
        />
      </div>

      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Sort by</Label>
        <Select
          value={value.sort ?? "relevance"}
          onValueChange={(sort) => onChange({ ...value, sort: sort as NonNullable<ProductQuery["sort"]>, page: 1 })}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="relevance">Relevance</SelectItem>
            <SelectItem value="price-asc">Price: low to high</SelectItem>
            <SelectItem value="price-desc">Price: high to low</SelectItem>
            <SelectItem value="rating">Top rated</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </Card>
  );
}
