import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Heart, ImageOff, Star } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Product } from "@/lib/api/types";
import { trackShoppingEvent } from "@/lib/api/tracking";
import { useCart, useWishlist } from "@/lib/store/cart-wishlist";

interface ProductCardProps {
  product: Product;
  score?: number | undefined;
}

export function ProductCard({ product, score }: ProductCardProps) {
  const { isWishlisted: checkWishlist, toggle: toggleWishlist } = useWishlist();
  const { addItem: addToCart } = useCart();
  const isWishlisted = checkWishlist(product.id);
  const [justAdded, setJustAdded] = useState(false);

  const handleAddToCart = () => {
    if (!product.inStock) {
      toast.error("This product is currently out of stock.");
      return;
    }

    if (!Number.isFinite(product.price) || product.price <= 0) {
      toast.error("Price is unavailable for this product.");
      return;
    }

    addToCart(product, 1);

    void trackShoppingEvent("cart", {
      id: product.id,
      category: product.category,
    });

    setJustAdded(true);
    setTimeout(() => setJustAdded(false), 1600);
    toast.success(`${product.name} added to cart.`);
  };

  const handleWishlist = () => {
    const result = toggleWishlist(product);
    void trackShoppingEvent("wishlist", {
      id: product.id,
      category: product.category,
    });

    toast.success(
      result.isWishlisted
        ? `${product.name} added to your wishlist.`
        : `${product.name} removed from your wishlist.`,
    );
  };

  const formattedPrice =
    Number.isFinite(product.price) && product.price > 0
      ? new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: product.currency || "USD",
        }).format(product.price)
      : null;

  return (
    <Card className="group relative flex h-full flex-col overflow-hidden rounded-xl border border-border/80 bg-card p-0 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-elevated">
      <Link
        to="/product/$productId"
        params={{ productId: product.id }}
        onClick={() => {
          void trackShoppingEvent("view", {
            id: product.id,
            category: product.category,
          });
        }}
        className="relative block aspect-[4/3] w-full overflow-hidden bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {product.image?.trim() ? (
          <img
            src={product.image}
            alt={product.name}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.style.display = "none";
            }}
            className="size-full object-cover object-center transition-transform duration-500 will-change-transform group-hover:scale-[1.04]"
          />
        ) : (
          <div
            className="flex size-full flex-col items-center justify-center gap-2 text-muted-foreground"
            aria-label="Product image unavailable"
          >
            <ImageOff className="size-8 stroke-[1.5]" />
            <span className="text-xs font-medium">Image unavailable</span>
          </div>
        )}

        {score != null && Number.isFinite(score) && (
          <Badge className="absolute left-2.5 top-2.5 border-0 bg-primary/90 text-primary-foreground shadow-sm backdrop-blur-sm text-xs font-medium px-2 py-0.5">
            {Math.round(score * 100)}% match
          </Badge>
        )}

        {!product.inStock && (
          <Badge
            variant="secondary"
            className="absolute bottom-2.5 left-2.5 bg-background/90 text-muted-foreground backdrop-blur-sm text-xs font-medium"
          >
            Out of stock
          </Badge>
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium tracking-tight text-foreground/80">
                {product.brand || "CatalogIQ"}
              </span>
              <span>·</span>
              <span>{product.category}</span>
            </div>

            <h3 className="mt-1 line-clamp-2 text-sm font-semibold tracking-tight text-foreground transition-colors group-hover:text-primary">
              <Link
                to="/product/$productId"
                params={{ productId: product.id }}
                className="focus-visible:underline focus-visible:outline-none"
              >
                {product.name}
              </Link>
            </h3>
          </div>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={cn(
              "size-8 shrink-0 rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
              isWishlisted && "text-rose-500 hover:text-rose-600 fill-rose-500",
            )}
            aria-label={
              isWishlisted
                ? `Remove ${product.name} from wishlist`
                : `Add ${product.name} to wishlist`
            }
            onClick={handleWishlist}
          >
            <Heart className={cn("size-4", isWishlisted && "fill-rose-500 text-rose-500")} />
          </Button>
        </div>

        {product.tags && product.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {product.tags.slice(0, 2).map((t) => (
              <span
                key={t}
                className="rounded-md bg-muted/60 px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {product.rating > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Star className="size-3.5 fill-amber-400 text-amber-400" />
            <span className="font-medium text-foreground">{product.rating}</span>
            {product.reviews > 0 && <span>({product.reviews.toLocaleString()})</span>}
          </div>
        )}

        <div className="mt-auto flex items-center justify-between gap-3 border-t border-border/50 pt-3">
          <div className="flex min-w-0 items-baseline gap-2">
            {formattedPrice ? (
              <span className="font-display text-base font-semibold text-foreground">
                {formattedPrice}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">Price unavailable</span>
            )}

            {product.originalPrice != null &&
              Number.isFinite(product.originalPrice) &&
              product.originalPrice > 0 &&
              formattedPrice && (
                <span className="text-xs text-muted-foreground line-through">
                  {new Intl.NumberFormat("en-US", {
                    style: "currency",
                    currency: product.currency || "USD",
                  }).format(product.originalPrice)}
                </span>
              )}
          </div>

          <Button
            type="button"
            size="sm"
            variant={justAdded ? "secondary" : "default"}
            disabled={!product.inStock || !Number.isFinite(product.price) || product.price <= 0}
            onClick={handleAddToCart}
            className="h-8 rounded-lg px-3 text-xs font-medium"
          >
            {justAdded ? "Added" : "Add to bag"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
