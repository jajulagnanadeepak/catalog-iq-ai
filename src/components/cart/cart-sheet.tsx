import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Minus, Plus, ShoppingBag, Trash2, ArrowRight } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useCart } from "@/lib/store/cart-wishlist";

export function CartSheet() {
  const { items, count, total, updateQuantity, removeItem, clear } = useCart();
  const [isOpen, setIsOpen] = useState(false);

  const formattedTotal = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(total);

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative size-9 rounded-lg text-muted-foreground hover:text-foreground"
          aria-label={`Shopping cart with ${count} items`}
        >
          <ShoppingBag className="size-4" />
          {count > 0 && (
            <Badge className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground leading-none">
              {count > 99 ? "99+" : count}
            </Badge>
          )}
        </Button>
      </SheetTrigger>

      <SheetContent side="right" className="flex w-full flex-col sm:max-w-md p-6">
        <SheetHeader className="pb-4">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-lg font-semibold">
              <ShoppingBag className="size-5 text-primary" />
              <span>Cart ({count})</span>
            </SheetTitle>
            {items.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => clear()}
                className="h-8 text-xs text-muted-foreground hover:text-destructive"
              >
                Clear all
              </Button>
            )}
          </div>
        </SheetHeader>

        <Separator />

        {items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <div className="grid size-14 place-items-center rounded-full bg-muted/60 text-muted-foreground">
              <ShoppingBag className="size-6 stroke-[1.5]" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">Your cart is empty</p>
              <p className="text-xs text-muted-foreground">
                Items you add from the catalog will appear here.
              </p>
            </div>
            <Button asChild size="sm" className="mt-2" onClick={() => setIsOpen(false)}>
              <Link to="/search">Explore products</Link>
            </Button>
          </div>
        ) : (
          <div className="flex flex-1 flex-col justify-between overflow-hidden">
            <div className="flex-1 overflow-y-auto py-4 space-y-3 pr-1">
              {items.map(({ product, quantity }) => (
                <div
                  key={product.id}
                  className="flex gap-3 rounded-lg border border-border/60 bg-card p-3 shadow-sm"
                >
                  <Link
                    to="/product/$productId"
                    params={{ productId: product.id }}
                    onClick={() => setIsOpen(false)}
                    className="relative size-16 shrink-0 overflow-hidden rounded-md bg-muted/40"
                  >
                    {product.image ? (
                      <img
                        src={product.image}
                        alt={product.name}
                        className="size-full object-cover"
                      />
                    ) : (
                      <div className="grid size-full place-items-center text-xs text-muted-foreground">
                        N/A
                      </div>
                    )}
                  </Link>

                  <div className="flex flex-1 flex-col justify-between min-w-0">
                    <div className="flex items-start justify-between gap-1">
                      <Link
                        to="/product/$productId"
                        params={{ productId: product.id }}
                        onClick={() => setIsOpen(false)}
                        className="truncate text-xs font-semibold text-foreground hover:text-primary transition-colors"
                      >
                        {product.name}
                      </Link>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeItem(product.id)}
                        className="size-6 text-muted-foreground hover:text-destructive"
                        aria-label={`Remove ${product.name}`}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>

                    <div className="flex items-center justify-between text-xs mt-2">
                      <span className="font-semibold text-foreground">
                        ${(product.price * quantity).toFixed(2)}
                      </span>

                      <div className="flex items-center gap-1.5 border border-border/60 rounded-md p-0.5">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => updateQuantity(product.id, quantity - 1)}
                          className="size-5 rounded text-muted-foreground"
                          aria-label="Decrease quantity"
                        >
                          <Minus className="size-3" />
                        </Button>
                        <span className="w-5 text-center text-xs font-medium">{quantity}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => updateQuantity(product.id, quantity + 1)}
                          className="size-5 rounded text-muted-foreground"
                          aria-label="Increase quantity"
                        >
                          <Plus className="size-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-border/70 pt-4 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Subtotal</span>
                <span className="font-bold text-foreground text-base">{formattedTotal}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Taxes and shipping calculated at checkout.
              </p>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <Button asChild variant="outline" size="sm" onClick={() => setIsOpen(false)}>
                  <Link to="/budget">Optimize budget</Link>
                </Button>
                <Button
                  size="sm"
                  className="gap-1.5"
                  onClick={() => {
                    setIsOpen(false);
                  }}
                >
                  <span>Checkout</span>
                  <ArrowRight className="size-3.5" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
