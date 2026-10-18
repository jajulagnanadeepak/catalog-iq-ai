
import { Link } from "@tanstack/react-router";
import { Heart, ImageOff, Star } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Product } from "@/lib/api/types";
import { trackShoppingEvent } from "@/lib/api/tracking";

interface ProductCardProps {
  product: Product;
  score?: number | undefined;
}

export function ProductCard({
  product,
  score,
}: ProductCardProps) {
  const handleAddToCart = () => {
    if (!product.inStock) {
      toast.error("This product is currently out of stock.");
      return;
    }

    if (!Number.isFinite(product.price) || product.price <= 0) {
      toast.error("Price is unavailable for this product.");
      return;
    }

    void trackShoppingEvent("cart", {
      id: product.id,
      category: product.category,
    });

    toast.success(`${product.name} added to cart.`);
  };

  const handleWishlist = () => {
    void trackShoppingEvent("wishlist", {
      id: product.id,
      category: product.category,
    });

    toast.success(`${product.name} added to your wishlist.`);
  };

  const formattedPrice =
    Number.isFinite(product.price) && product.price > 0
      ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: product.currency || "USD",
      }).format(product.price)
      : null;

  return (
    <Card className="group flex h-full flex-col overflow-hidden p-0 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-elevated">
      <Link
        to="/product/$productId"
        params={{ productId: product.id }}
        onClick={() => {
          void trackShoppingEvent("view", {
            id: product.id,
            category: product.category,
          });
        }}
        className="relative block aspect-[4/3] overflow-hidden bg-muted"
      >
        {product.image?.trim() ? (
          <img
            src={product.image}
            alt={product.name}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.style.display = "none";
            }}
            className="size-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div
            className="flex size-full flex-col items-center justify-center gap-2 text-muted-foreground"
            aria-label="Product image unavailable"
          >
            <ImageOff className="size-8" />
            <span className="text-xs">Image unavailable</span>
          </div>
        )}

        {score != null && Number.isFinite(score) && (
          <Badge className="absolute left-2 top-2">
            {Math.round(score * 100)}% match
          </Badge>
        )}

        {!product.inStock && (
          <Badge
            variant="secondary"
            className="absolute bottom-2 left-2"
          >
            Out of stock
          </Badge>
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">
              {product.brand || "Unknown brand"}
            </p>

            <h3 className="line-clamp-2 font-medium">
              {product.name}
            </h3>

            <p className="text-xs text-muted-foreground">
              {product.category}
            </p>
          </div>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={`Add ${product.name} to wishlist`}
            onClick={handleWishlist}
          >
            <Heart className="size-4" />
          </Button>
        </div>

        {product.rating > 0 && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Star className="size-3 fill-current" />
            <span>
              {product.rating}
              {product.reviews > 0 &&
                ` · ${product.reviews.toLocaleString()} reviews`}
            </span>
          </div>
        )}

        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <div className="flex min-w-0 items-baseline gap-2">
            {formattedPrice ? (
              <span className="font-display text-lg font-semibold">
                {formattedPrice}
              </span>
            ) : (
              <span className="text-sm text-muted-foreground">
                Price unavailable
              </span>
            )}

            {product.originalPrice != null &&
              Number.isFinite(product.originalPrice) &&
              product.originalPrice > 0 &&
              formattedPrice && (
                <span className="text-sm text-muted-foreground line-through">
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
            disabled={
              !product.inStock ||
              !Number.isFinite(product.price) ||
              product.price <= 0
            }
            onClick={handleAddToCart}
          >
            Add
          </Button>
        </div>
      </div>
    </Card>
  );
}
