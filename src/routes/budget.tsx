import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { PiggyBank, Wallet } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PanelSkeleton } from "@/components/catalog/skeletons";
import { ProductCard } from "@/components/catalog/product-card";
import { postBudget } from "@/lib/api/services";
import { CATEGORIES } from "@/lib/api/mock";
import type { BudgetPayload } from "@/lib/api/types";

export const Route = createFileRoute("/budget")({
  head: () => ({
    meta: [
      { title: "Budget Optimizer — CatalogIQ AI" },
      {
        name: "description",
        content:
          "Allocate a fixed budget across categories and let CatalogIQ AI maximise value per dollar.",
      },
      { property: "og:title", content: "Budget Optimizer — CatalogIQ AI" },
      { property: "og:description", content: "Budget-aware basket optimisation across categories." },
    ],
  }),
  component: BudgetPage,
});

function BudgetPage() {
  const [budget, setBudget] = useState("600");
  const [priority, setPriority] = useState<BudgetPayload["priority"]>("balanced");
  const [categories, setCategories] = useState<string[]>(["Tops", "Footwear", "Bags"]);

  const optimize = useMutation({ mutationFn: postBudget });

  function toggle(cat: string) {
    setCategories((c) => (c.includes(cat) ? c.filter((x) => x !== cat) : [...c, cat]));
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    optimize.mutate({ budget: Number(budget) || 0, categories, priority });
  }

  const result = optimize.data;
  const usedPct = result ? Math.min(100, (result.spent / Math.max(1, result.budget)) * 100) : 0;

  return (
    <AppShell title="Budget Optimizer" description="Maximise basket value against a hard ceiling">
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit gap-5 p-6 shadow-card">
          <div className="flex items-center gap-2">
            <Wallet className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Constraints</h2>
          </div>

          <form className="space-y-5" onSubmit={submit}>
            <div className="space-y-2">
              <Label htmlFor="budget" className="text-xs text-muted-foreground">
                Total budget (USD)
              </Label>
              <Input
                id="budget"
                inputMode="numeric"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Optimise for</Label>
              <Select
                value={priority}
                onValueChange={(v) => setPriority(v as BudgetPayload["priority"])}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="value">Best value</SelectItem>
                  <SelectItem value="quality">Highest quality</SelectItem>
                  <SelectItem value="balanced">Balanced</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <Label className="text-xs text-muted-foreground">Categories</Label>
              <div className="space-y-2.5">
                {CATEGORIES.map((c) => (
                  <label key={c} className="flex items-center gap-2 text-sm">
                    <Checkbox checked={categories.includes(c)} onCheckedChange={() => toggle(c)} />
                    {c}
                  </label>
                ))}
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={optimize.isPending}>
              <PiggyBank className="size-4" />
              {optimize.isPending ? "Optimising…" : "Optimise basket"}
            </Button>
          </form>
        </Card>

        <div className="space-y-6">
          {optimize.isPending && <PanelSkeleton />}

          {!optimize.isPending && !result && (
            <Card className="items-center gap-2 p-16 text-center shadow-card">
              <PiggyBank className="size-8 text-muted-foreground" />
              <p className="font-medium">No plan yet</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Set a budget and pick categories — the optimizer will assemble the highest-value
                basket that fits.
              </p>
            </Card>
          )}

          {result && (
            <>
              <Card className="gap-4 p-6 shadow-card">
                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    ["Budget", `$${result.budget.toFixed(0)}`],
                    ["Allocated", `$${result.spent.toFixed(0)}`],
                    ["Remaining", `$${result.saved.toFixed(0)}`],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <p className="text-xs text-muted-foreground">{label}</p>
                      <p className="font-display text-2xl font-semibold">{value}</p>
                    </div>
                  ))}
                </div>
                <Progress value={usedPct} />
                <p className="text-xs text-muted-foreground">
                  {usedPct.toFixed(0)}% of budget allocated across {result.allocations.length}{" "}
                  categories.
                </p>
              </Card>

              <div>
                <h2 className="mb-4 text-base font-semibold">Allocation</h2>
                <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                  {result.allocations.map((a) => (
                    <div key={a.category} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{a.category}</span>
                        <Badge variant="secondary">${a.amount.toFixed(0)}</Badge>
                      </div>
                      <ProductCard product={a.product} />
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
