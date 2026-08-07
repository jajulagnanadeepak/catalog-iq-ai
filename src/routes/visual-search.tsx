import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Camera, Upload } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProductCard } from "@/components/catalog/product-card";
import { ProductGridSkeleton } from "@/components/catalog/skeletons";
import { postVisualSearch } from "@/lib/api/services";

export const Route = createFileRoute("/visual-search")({
  head: () => ({
    meta: [
      { title: "Visual Search — CatalogIQ AI" },
      {
        name: "description",
        content: "Upload an image and match it against the catalog by shape, colour and texture.",
      },
      { property: "og:title", content: "Visual Search — CatalogIQ AI" },
      { property: "og:description", content: "Image-based product matching across your catalog." },
    ],
  }),
  component: VisualSearchPage,
});

function VisualSearchPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const search = useMutation({
    mutationFn: postVisualSearch,
    onError: () => toast.error("Couldn't analyse that image"),
  });

  function handleFile(file?: File | null) {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    search.mutate(file);
  }

  return (
    <AppShell title="Visual Search" description="Find catalog matches from any image">
      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card className="h-fit gap-4 p-6 shadow-card">
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFile(e.dataTransfer.files?.[0]);
            }}
            className="grid cursor-pointer place-items-center gap-3 rounded-xl border-2 border-dashed border-border p-10 text-center transition-colors hover:border-primary/60"
          >
            {preview ? (
              <img
                src={preview}
                alt="Uploaded reference"
                className="max-h-56 w-full rounded-lg object-cover"
              />
            ) : (
              <>
                <Upload className="size-7 text-muted-foreground" />
                <p className="text-sm font-medium">Drop an image or click to upload</p>
                <p className="text-xs text-muted-foreground">JPG or PNG, up to 8MB</p>
              </>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          <Button variant="outline" onClick={() => inputRef.current?.click()}>
            <Camera className="size-4" /> Choose image
          </Button>

          {search.data && (
            <div className="flex flex-wrap gap-2">
              {search.data.detected.map((d) => (
                <Badge key={d} variant="secondary">
                  {d}
                </Badge>
              ))}
            </div>
          )}
        </Card>

        <div>
          <h2 className="mb-4 text-base font-semibold">Visual matches</h2>
          {search.isPending ? (
            <ProductGridSkeleton count={4} />
          ) : search.data ? (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {search.data.items.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          ) : (
            <Card className="items-center gap-2 p-16 text-center shadow-card">
              <Camera className="size-8 text-muted-foreground" />
              <p className="font-medium">No image analysed yet</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Upload a reference photo to find visually similar items in the catalog.
              </p>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
