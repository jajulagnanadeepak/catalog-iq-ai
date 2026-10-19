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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const search = useMutation({
    mutationFn: postVisualSearch,
    onError: () => toast.error("Couldn't analyse that image. Please try another."),
  });

  function handleFile(file?: File | null) {
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      toast.error("Please upload a valid image file (JPG, PNG, WebP).");
      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      toast.error("Image file size must be 8MB or smaller.");
      return;
    }

    setSelectedFile(file);
    setPreview(URL.createObjectURL(file));
    search.mutate(file);
  }

  const handleRetry = () => {
    if (selectedFile) {
      search.mutate(selectedFile);
    }
  };

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
                <p className="text-xs text-muted-foreground">JPG, PNG, or WebP up to 8MB</p>
              </>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          <Button variant="outline" onClick={() => inputRef.current?.click()}>
            <Camera className="size-4" /> Choose image
          </Button>

          {search.data && search.data.detected && search.data.detected.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-border/60">
              <span className="text-xs font-medium text-muted-foreground">
                Detected attributes:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {search.data.detected.map((d) => (
                  <Badge key={d} variant="secondary">
                    {d}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </Card>

        <div>
          <h2 className="mb-4 text-base font-semibold">Visual matches</h2>
          {search.isPending ? (
            <ProductGridSkeleton count={4} />
          ) : search.isError ? (
            <Card className="flex flex-col items-center gap-3 p-12 text-center shadow-card">
              <Camera className="size-8 text-destructive" />
              <div className="space-y-1">
                <p className="font-semibold text-foreground">Failed to analyze image</p>
                <p className="max-w-sm text-sm text-muted-foreground">
                  An error occurred while comparing with catalog items.
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={handleRetry}>
                Try again
              </Button>
            </Card>
          ) : search.data ? (
            search.data.items && search.data.items.length > 0 ? (
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {search.data.items.map((p) => (
                  <ProductCard
                    key={p.id}
                    product={p}
                    score={(p as Product & { similarity?: number }).similarity}
                  />
                ))}
              </div>
            ) : (
              <Card className="flex flex-col items-center gap-2 p-16 text-center shadow-card">
                <Camera className="size-8 text-muted-foreground" />
                <p className="font-medium">No visual matches found</p>
                <p className="max-w-sm text-sm text-muted-foreground">
                  We couldn't find items similar to this image. Try an image with clearer focus or
                  lighting.
                </p>
              </Card>
            )
          ) : (
            <Card className="flex flex-col items-center gap-2 p-16 text-center shadow-card">
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
