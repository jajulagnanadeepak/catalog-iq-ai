import { Sparkles, Star } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { Recommendation } from "@/lib/api/types";

export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  if (!recommendation || !recommendation.product) {
    return null;
  }

  const { product, title, reason, ranking_score } = recommendation;
  const currency = product.currency || "USD";
  const formattedPrice =
    Number.isFinite(product.price) && product.price > 0
      ? new Intl.NumberFormat("en-US", {
          style: "currency",
          currency,
        }).format(product.price)
      : null;

  const rating =
    typeof product.rating === "number" && Number.isFinite(product.rating)
      ? product.rating.toFixed(1)
      : null;
  const score =
    typeof ranking_score === "number" && Number.isFinite(ranking_score) ? ranking_score : 0.8;

  return (
    <Card className="flex gap-4 p-4 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-elevated">
      <Link
        to="/product/$productId"
        params={{ productId: product.id }}
        className="size-20 shrink-0 overflow-hidden rounded-lg bg-muted"
      >
        <img
          src={product.image}
          alt={product.name}
          loading="lazy"
          className="size-full object-cover"
        />
      </Link>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
          <Sparkles className="size-3.5" />
          {title}
        </div>

        <Link
          to="/product/$productId"
          params={{ productId: product.id }}
          className="mt-1 block line-clamp-1 font-medium hover:underline"
        >
          {product.name}
        </Link>

        <p className="mt-1 text-xs text-muted-foreground">
          {product.brand} · {product.category}
        </p>

        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{reason}</p>

        <div className="mt-2 flex flex-wrap items-center gap-3">
          {rating && (
            <div className="flex items-center gap-1 text-sm">
              <Star className="size-3.5 fill-current text-yellow-500" />
              <span>{rating}</span>
            </div>
          )}

          {formattedPrice && <span className="text-sm font-semibold">{formattedPrice}</span>}
        </div>

        <div className="mt-3 flex items-center gap-3">
          <Progress value={Math.max(0, Math.min(100, score * 100))} className="h-1.5" />
          <span className="shrink-0 text-xs text-muted-foreground">
            Ranking score: {Math.round(score * 100)}/100
          </span>
        </div>
      </div>
    </Card>
  );
}
