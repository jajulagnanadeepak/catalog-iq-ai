import { Link } from "@tanstack/react-router";
import { Heart, Star } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Product } from "@/lib/api/types";

export function ProductCard({
  product,
  score,
}: {
  product: Product;
  score?: number | undefined;
}) {
  return (
    <Card className="group flex h-full flex-col overflow-hidden p-0 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-elevated">
      <Link
        to="/product/$productId"
        params={{ productId: product.id }}
        className="relative block aspect-[4/3] overflow-hidden bg-muted"
      >
        <img
          src={product.image}
          alt={product.name}
          loading="lazy"
          className="size-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        {score != null && (
          <Badge className="absolute left-3 top-3 bg-primary/90">
            {Math.round(score * 100)}% match
          </Badge>
        )}
        {!product.inStock && (
          <Badge variant="secondary" className="absolute right-3 top-3">
            Out of stock
          </Badge>
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{product.brand}</p>
            <Link
              to="/product/$productId"
              params={{ productId: product.id }}
              className="line-clamp-1 font-medium hover:underline"
            >
              {product.name}
            </Link>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            aria-label="Save item"
            onClick={() => toast.success(`${product.name} saved to your wishlist`)}
          >
            <Heart className="size-4" />
          </Button>
        </div>

        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Star className="size-3.5 fill-chart-4 text-chart-4" />
          {product.rating} · {product.reviews.toLocaleString()} reviews
        </div>

        <div className="mt-auto flex items-center justify-between pt-2">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-lg font-semibold">${product.price}</span>
            {product.originalPrice && (
              <span className="text-xs text-muted-foreground line-through">
                ${product.originalPrice}
              </span>
            )}
          </div>
          <Button size="sm" onClick={() => toast.success(`${product.name} added to cart`)}>
            Add
          </Button>
        </div>
      </div>
    </Card>
  );
}
