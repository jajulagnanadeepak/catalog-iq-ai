import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Shirt, Sparkles } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProductCard } from "@/components/catalog/product-card";
import { PanelSkeleton } from "@/components/catalog/skeletons";
import { postStylist } from "@/lib/api/services";

export const Route = createFileRoute("/stylist")({
  head: () => ({
    meta: [
      { title: "AI Stylist — CatalogIQ AI" },
      {
        name: "description",
        content:
          "Generate complete looks from occasion, style and budget signals using the CatalogIQ AI stylist.",
      },
      { property: "og:title", content: "AI Stylist — CatalogIQ AI" },
      { property: "og:description", content: "Complete outfits assembled by AI from your catalog." },
    ],
  }),
  component: StylistPage,
});

const OCCASIONS = ["Everyday", "Work", "Evening", "Travel", "Wedding guest"];
const STYLES = ["Minimal", "Classic", "Street", "Utility", "Romantic"];
const BODY_TYPES = ["Rectangle", "Athletic", "Pear", "Hourglass", "Oval"];

function StylistPage() {
  const [occasion, setOccasion] = useState("Evening");
  const [style, setStyle] = useState("Minimal");
  const [bodyType, setBodyType] = useState("Athletic");
  const [budget, setBudget] = useState("800");
  const [notes, setNotes] = useState("");

  const looks = useMutation({ mutationFn: postStylist });

  function submit(e: FormEvent) {
    e.preventDefault();
    looks.mutate({ occasion, style, bodyType, budget: Number(budget) || 0, notes });
  }

  return (
    <AppShell title="AI Stylist" description="Occasion-aware outfit generation">
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit gap-5 p-6 shadow-card">
          <div className="flex items-center gap-2">
            <Shirt className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Style brief</h2>
          </div>

          <form className="space-y-4" onSubmit={submit}>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Occasion</Label>
              <Select value={occasion} onValueChange={setOccasion}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OCCASIONS.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Style</Label>
              <Select value={style} onValueChange={setStyle}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STYLES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Body type</Label>
              <Select value={bodyType} onValueChange={setBodyType}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BODY_TYPES.map((b) => (
                    <SelectItem key={b} value={b}>
                      {b}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="budget" className="text-xs text-muted-foreground">
                Budget (USD)
              </Label>
              <Input
                id="budget"
                inputMode="numeric"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes" className="text-xs text-muted-foreground">
                Notes
              </Label>
              <Textarea
                id="notes"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Avoid bright colours, prefer natural fabrics…"
              />
            </div>

            <Button type="submit" className="w-full" disabled={looks.isPending}>
              <Sparkles className="size-4" />
              {looks.isPending ? "Styling…" : "Generate looks"}
            </Button>
          </form>
        </Card>

        <div className="space-y-8">
          {looks.isPending && <PanelSkeleton />}

          {!looks.isPending && !looks.data && (
            <Card className="items-center gap-2 p-16 text-center shadow-card">
              <Shirt className="size-8 text-muted-foreground" />
              <p className="font-medium">No looks yet</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Fill in the brief and the stylist will assemble complete outfits from in-stock
                catalog items.
              </p>
            </Card>
          )}

          {looks.data?.map((look) => (
            <div key={look.id}>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold">{look.title}</h2>
                  <p className="max-w-2xl text-sm text-muted-foreground">{look.summary}</p>
                </div>
                <Badge variant="secondary">Look total ${look.total.toFixed(0)}</Badge>
              </div>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {look.items.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
