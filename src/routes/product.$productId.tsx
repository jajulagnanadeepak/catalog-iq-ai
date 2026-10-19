import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Heart, ShoppingBag, Star, Truck } from "lucide-react";
import { toast } from "sonner";
import { useEffect, useRef } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ProductCard } from "@/components/catalog/product-card";
import { PanelSkeleton, ProductGridSkeleton } from "@/components/catalog/skeletons";

import { getProduct, getProducts } from "@/lib/api/services";
import { trackShoppingEvent } from "@/lib/api/tracking";
import { useCart, useWishlist } from "@/lib/store/cart-wishlist";

export const Route = createFileRoute("/product/$productId")({
  head: () => ({
    meta: [
      { title: "Product details — CatalogIQ AI" },
      {
        name: "description",
        content: "Full product detail with AI-matched alternatives and complementary items.",
      },
      {
        property: "og:title",
        content: "Product details — CatalogIQ AI",
      },
      {
        property: "og:description",
        content: "Product detail and AI-matched alternatives.",
      },
    ],
  }),
  component: ProductPage,
});

function ProductPage() {
  const { productId } = Route.useParams();

  const product = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getProduct(productId),
  });

  const related = useQuery({
    queryKey: ["products", "related", productId],
    queryFn: () => getProducts({ pageSize: 4, sort: "rating" }),
  });

  const p = product.data;

  // Prevent duplicate view events while this component remains mounted.
  const trackedViewKey = useRef<string | null>(null);

  const currentId = p?.id;
  const currentCategory = p?.category;

  useEffect(() => {
    if (!currentId) return;

    const viewKey = `${currentId}:${currentCategory ?? ""}`;

    if (trackedViewKey.current === viewKey) return;

    trackedViewKey.current = viewKey;

    void trackShoppingEvent("view", {
      id: currentId,
      category: currentCategory,
    });
  }, [currentId, currentCategory]);

  const { addItem: addToCart } = useCart();
  const { isWishlisted: checkWishlisted, toggle: toggleWishlist } = useWishlist();
  const isWishlisted = p ? checkWishlisted(p.id) : false;

  const handleAddToCart = () => {
    if (!p) return;

    if (!p.inStock) {
      toast.error("This product is currently out of stock.");
      return;
    }

    addToCart(p, 1);

    void trackShoppingEvent("cart", {
      id: p.id,
      category: p.category,
    });

    toast.success(`${p.name} added to cart`);
  };

  const handleSaveToWishlist = () => {
    if (!p) return;

    const result = toggleWishlist(p);

    void trackShoppingEvent("wishlist", {
      id: p.id,
      category: p.category,
    });

    toast.success(
      result.isWishlisted
        ? `${p.name} added to your wishlist`
        : `${p.name} removed from your wishlist`,
    );
  };

  if (product.isError) {
    return (
      <AppShell title="Product unavailable" description="We couldn't load this product.">
        <Card className="p-6">
          <p className="text-muted-foreground">
            There was a problem loading this product. Please try again.
          </p>

          <Button className="mt-4" onClick={() => void product.refetch()}>
            Retry
          </Button>
        </Card>
      </AppShell>
    );
  }

  return (
    <AppShell title={p?.name ?? "Product"} description={p?.brand}>
      {product.isPending || !p ? (
        <PanelSkeleton />
      ) : (
        <>
          <div className="grid gap-8 lg:grid-cols-2">
            <Card className="overflow-hidden p-0 shadow-card">
              {p.image ? (
                <img
                  src={p.image}
                  alt={p.name}
                  className="aspect-[4/3] w-full object-cover"
                  onError={(event) => {
                    event.currentTarget.style.visibility = "hidden";
                  }}
                />
              ) : (
                <div className="flex aspect-[4/3] items-center justify-center bg-muted text-muted-foreground">
                  Image unavailable
                </div>
              )}
            </Card>

            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{p.brand}</p>

              <h2 className="mt-2 text-3xl font-semibold">{p.name}</h2>

              <div className="mt-3 flex items-center gap-3 text-sm">
                <span className="flex items-center gap-1 text-warning">
                  <Star className="size-4 fill-current" />
                  {(p.rating ?? 0).toFixed(1)}
                </span>

                <span className="text-muted-foreground">{p.reviews ?? 0} reviews</span>

                <Badge variant={p.inStock ? "secondary" : "outline"}>
                  {p.inStock ? "In stock" : "Out of stock"}
                </Badge>
              </div>

              <div className="mt-6 flex items-end gap-3">
                <span className="font-display text-3xl font-semibold">
                  {new Intl.NumberFormat("en-US", {
                    style: "currency",
                    currency: p.currency || "USD",
                  }).format(p.price ?? 0)}
                </span>

                {p.originalPrice != null && (
                  <span className="pb-1 text-sm text-muted-foreground line-through">
                    {new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: p.currency || "USD",
                    }).format(p.originalPrice)}
                  </span>
                )}
              </div>

              <p className="mt-6 text-muted-foreground">{p.description}</p>

              <Separator className="my-6" />

              <div className="space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground">Colours</p>

                  <div className="mt-2 flex flex-wrap gap-2">
                    {(p.colors ?? []).map((color) => (
                      <Badge key={color} variant="outline">
                        {color}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-muted-foreground">Sizes</p>

                  <div className="mt-2 flex flex-wrap gap-2">
                    {(p.sizes ?? []).map((size) => (
                      <Badge key={size} variant="outline">
                        {size}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" disabled={!p.inStock} onClick={handleAddToCart}>
                  <ShoppingBag className="size-4" />
                  Add to cart
                </Button>

                <Button
                  size="lg"
                  variant={isWishlisted ? "secondary" : "outline"}
                  onClick={handleSaveToWishlist}
                  className={
                    isWishlisted ? "text-rose-500 border-rose-200 hover:text-rose-600" : ""
                  }
                >
                  <Heart
                    className={`size-4 ${isWishlisted ? "fill-rose-500 text-rose-500" : ""}`}
                  />
                  {isWishlisted ? "Saved" : "Save"}
                </Button>

                <Button asChild size="lg" variant="ghost">
                  <Link to="/copilot">Ask the copilot</Link>
                </Button>
              </div>

              <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
                <Truck className="size-4" />
                Free delivery and 30-day returns
              </p>
            </div>
          </div>

          <div className="mt-12">
            <h2 className="mb-4 text-base font-semibold">You may also like</h2>

            {related.isPending ? (
              <ProductGridSkeleton count={4} />
            ) : related.isError ? (
              <p className="text-sm text-muted-foreground">Related products could not be loaded.</p>
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {(related.data?.items ?? [])
                  .filter((item) => item.id !== p.id)
                  .map((item) => (
                    <ProductCard key={item.id} product={item} />
                  ))}
              </div>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}
