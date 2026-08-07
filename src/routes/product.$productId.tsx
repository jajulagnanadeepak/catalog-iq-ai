import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Heart, ShoppingBag, Star, Truck } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ProductCard } from "@/components/catalog/product-card";
import { PanelSkeleton, ProductGridSkeleton } from "@/components/catalog/skeletons";
import { getProduct, getProducts } from "@/lib/api/services";

export const Route = createFileRoute("/product/$productId")({
  head: () => ({
    meta: [
      { title: "Product details — CatalogIQ AI" },
      {
        name: "description",
        content: "Full product detail with AI-matched alternatives and complementary items.",
      },
      { property: "og:title", content: "Product details — CatalogIQ AI" },
      { property: "og:description", content: "Product detail and AI-matched alternatives." },
    ],
  }),
  component: ProductPage,
});

function ProductPage() {
  const { productId } = Route.useParams();
  const product = useQuery({ queryKey: ["product", productId], queryFn: () => getProduct(productId) });
  const related = useQuery({
    queryKey: ["products", "related", productId],
    queryFn: () => getProducts({ pageSize: 4, sort: "rating" }),
  });

  const p = product.data;

  return (
    <AppShell title={p?.name ?? "Product"} description={p?.brand}>
      {product.isPending || !p ? (
        <PanelSkeleton />
      ) : (
        <>
          <div className="grid gap-8 lg:grid-cols-2">
            <Card className="overflow-hidden p-0 shadow-card">
              <img src={p.image} alt={p.name} className="aspect-[4/3] w-full object-cover" />
            </Card>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{p.brand}</p>
              <h2 className="mt-2 text-3xl font-semibold">{p.name}</h2>
              <div className="mt-3 flex items-center gap-3 text-sm">
                <span className="flex items-center gap-1 text-warning">
                  <Star className="size-4 fill-current" /> {p.rating.toFixed(1)}
                </span>
                <span className="text-muted-foreground">{p.reviews} reviews</span>
                <Badge variant={p.inStock ? "secondary" : "outline"}>
                  {p.inStock ? "In stock" : "Out of stock"}
                </Badge>
              </div>

              <div className="mt-6 flex items-end gap-3">
                <span className="font-display text-3xl font-semibold">${p.price.toFixed(0)}</span>
                {p.originalPrice && (
                  <span className="pb-1 text-sm text-muted-foreground line-through">
                    ${p.originalPrice.toFixed(0)}
                  </span>
                )}
              </div>

              <p className="mt-6 text-muted-foreground">{p.description}</p>

              <Separator className="my-6" />

              <div className="space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground">Colours</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {p.colors.map((c) => (
                      <Badge key={c} variant="outline">
                        {c}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Sizes</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {p.sizes.map((s) => (
                      <Badge key={s} variant="outline">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" onClick={() => toast.success(`${p.name} added to cart`)}>
                  <ShoppingBag className="size-4" /> Add to cart
                </Button>
                <Button size="lg" variant="outline" onClick={() => toast("Saved to wishlist")}>
                  <Heart className="size-4" /> Save
                </Button>
                <Button asChild size="lg" variant="ghost">
                  <Link to="/copilot">Ask the copilot</Link>
                </Button>
              </div>

              <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
                <Truck className="size-4" /> Free delivery and 30-day returns
              </p>
            </div>
          </div>

          <div className="mt-12">
            <h2 className="mb-4 text-base font-semibold">You may also like</h2>
            {related.isPending ? (
              <ProductGridSkeleton count={4} />
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {related.data?.items
                  .filter((r) => r.id !== p.id)
                  .map((r) => <ProductCard key={r.id} product={r} />)}
              </div>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}
