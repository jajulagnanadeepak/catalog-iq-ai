import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  Brain,
  Camera,
  Check,
  ChevronRight,
  Layers3,
  LineChart,
  MessageSquareText,
  Search,
  Shirt,
  Sparkles,
  SlidersHorizontal,
  Wallet,
  Zap,
} from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProductCard } from "@/components/catalog/product-card";
import { PRODUCTS } from "@/lib/api/mock";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      {
        title: "CatalogIQ AI — Intelligent Product Discovery",
      },
      {
        name: "description",
        content:
          "Discover products through semantic search, personalized styling, visual matching, and AI-powered shopping assistance.",
      },
      {
        property: "og:title",
        content: "CatalogIQ AI — Intelligent Product Discovery",
      },
      {
        property: "og:description",
        content: "A smarter way to discover products with AI-powered commerce intelligence.",
      },
    ],
  }),
  component: Landing,
});

const DISCOVERY_PRESETS = [
  {
    id: "coat",
    pill: "Tailored wool overcoat",
    prompt: "A tailored overcoat for winter events with structured shoulders under $350",
    productId: "p-001",
    matchScore: 0.98,
    intentReasoning:
      "Extracted: cold weather outerwear · formal occasion · structured tailoring · budget ceiling $350",
  },
  {
    id: "audio",
    pill: "ANC headphones for travel",
    prompt: "Adaptive ANC headphones with long battery life for flights under $300",
    productId: "p-003",
    matchScore: 0.96,
    intentReasoning:
      "Extracted: personal audio · travel ergonomics · adaptive active noise cancellation · sub-$300",
  },
  {
    id: "shoes",
    pill: "City runner sneakers",
    prompt: "Cushioned responsive runners for urban commutes and daily mileage",
    productId: "p-002",
    matchScore: 0.94,
    intentReasoning:
      "Extracted: athletic footwear · foam midsole responsiveness · daily urban commuting",
  },
  {
    id: "pack",
    pill: "Weatherproof commuter bag",
    prompt: "Weatherproof backpack with dedicated 16-inch laptop protection",
    productId: "p-006",
    matchScore: 0.95,
    intentReasoning:
      "Extracted: commuter bag · recycled weatherproof shell · padded laptop storage",
  },
] as const;

const CATEGORIES = ["All", "Outerwear", "Footwear", "Electronics", "Accessories", "Bags"] as const;

function Landing() {
  const navigate = useNavigate();
  const [activePresetIndex, setActivePresetIndex] = useState(0);
  const [heroSearchInput, setHeroSearchInput] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<(typeof CATEGORIES)[number]>("All");

  const currentPreset = DISCOVERY_PRESETS[activePresetIndex];
  const matchedProduct = PRODUCTS.find((p) => p.id === currentPreset.productId) ?? PRODUCTS[0];

  const filteredProducts =
    selectedCategory === "All"
      ? PRODUCTS.slice(0, 8)
      : PRODUCTS.filter((p) => p.category === selectedCategory).slice(0, 8);

  const handleHeroSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void navigate({
      to: "/search",
    });
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground antialiased">
      <Navbar />

      {/* HERO SECTION */}
      <section className="relative isolate border-b border-border/70 bg-gradient-to-b from-background via-muted/15 to-background py-16 sm:py-20 lg:py-28">
        <div className="mx-auto grid w-full max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
          {/* Left Column: Intent & Editorial Value */}
          <div className="animate-rise space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-muted/40 px-3.5 py-1 text-xs font-medium text-foreground/80 backdrop-blur-sm">
              <span className="size-2 rounded-full bg-primary" />
              <span>Retail Commerce Intelligence</span>
              <span className="text-muted-foreground/60">·</span>
              <span className="text-muted-foreground">Catalog-wide understanding</span>
            </div>

            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl text-foreground">
              Commerce discovery driven by real intent.
            </h1>

            <p className="max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              CatalogIQ replaces rigid keyword filters with deep catalog understanding. Search in
              plain words, style complete outfits, optimize budgets, and explore with an AI shopping
              assistant.
            </p>

            {/* Live Search Trigger Bar */}
            <form onSubmit={handleHeroSearchSubmit} className="mt-8">
              <div className="flex flex-col gap-2 rounded-2xl border border-border/90 bg-card p-2 shadow-card focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/20 sm:flex-row sm:items-center">
                <div className="flex flex-1 items-center gap-2.5 px-3 py-1.5">
                  <Search className="size-4 shrink-0 text-muted-foreground" />
                  <input
                    type="text"
                    value={heroSearchInput}
                    onChange={(e) => setHeroSearchInput(e.target.value)}
                    placeholder="Search by occasion, material, or vibe…"
                    className="w-full bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
                    aria-label="Search catalog in natural language"
                  />
                </div>
                <Button type="submit" className="h-10 rounded-xl px-5 text-sm font-medium">
                  Search catalog
                  <ArrowRight className="ml-1.5 size-4" />
                </Button>
              </div>
            </form>

            {/* Prompt presets */}
            <div className="space-y-2 pt-2">
              <span className="text-xs font-medium text-muted-foreground">
                Or test real intent prompts:
              </span>
              <div className="flex flex-wrap gap-2">
                {DISCOVERY_PRESETS.map((preset, index) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => {
                      setActivePresetIndex(index);
                      setHeroSearchInput(preset.prompt);
                    }}
                    className={cn(
                      "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all text-left",
                      activePresetIndex === index
                        ? "border-primary/50 bg-primary/10 text-primary shadow-xs"
                        : "border-border/80 bg-muted/30 text-muted-foreground hover:border-border hover:bg-muted/70 hover:text-foreground",
                    )}
                  >
                    {preset.pill}
                  </button>
                ))}
              </div>
            </div>

            {/* Primary actions */}
            <div className="flex flex-wrap items-center gap-3 pt-4">
              <Button asChild size="lg" className="rounded-xl px-6 text-sm font-medium">
                <Link to="/search">
                  Explore full catalog
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="rounded-xl border-border px-6 text-sm font-medium"
              >
                <Link to="/copilot">
                  <MessageSquareText className="mr-2 size-4" />
                  Open shopping copilot
                </Link>
              </Button>
            </div>

            {/* Trust points */}
            <div className="flex flex-wrap items-center gap-6 pt-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Check className="size-3.5 text-primary" />
                Semantic vector ranking
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Check className="size-3.5 text-primary" />
                Attribute & material reasoning
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Check className="size-3.5 text-primary" />
                Real-time stock validation
              </span>
            </div>
          </div>

          {/* Right Column: Live Commerce Canvas */}
          <div className="animate-rise relative">
            <Card className="overflow-hidden rounded-2xl border border-border/80 bg-card/95 p-0 shadow-elevated backdrop-blur-md">
              {/* Terminal-like header */}
              <div className="flex items-center justify-between border-b border-border/70 px-5 py-3.5 bg-muted/20">
                <div className="flex items-center gap-2.5">
                  <div className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Sparkles className="size-3.5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-foreground">Live Intent Resolution</p>
                    <p className="text-[11px] text-muted-foreground">Catalog vector engine</p>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className="gap-1 border-primary/20 bg-primary/5 text-primary text-[11px] font-medium"
                >
                  <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Active Model
                </Badge>
              </div>

              {/* Resolved Prompt Window */}
              <div className="p-5 sm:p-6 space-y-4">
                <div className="rounded-xl border border-border/80 bg-muted/30 p-3.5">
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1.5 font-medium">
                    <span>Shopper Request</span>
                    <span>12ms inference</span>
                  </div>
                  <p className="text-sm font-medium text-foreground italic">
                    “{currentPreset.prompt}”
                  </p>
                </div>

                {/* Engine Reasoning Tag */}
                <div className="rounded-lg border border-primary/20 bg-primary/[0.04] p-3 text-xs">
                  <div className="flex items-center gap-1.5 font-medium text-primary mb-1">
                    <Brain className="size-3.5" />
                    <span>Attribute Extraction</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {currentPreset.intentReasoning}
                  </p>
                </div>

                {/* Real Matched Product Snapshot */}
                <div className="space-y-2 pt-1">
                  <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                    <span>Top Catalog Match</span>
                    <span className="text-primary font-semibold">
                      {Math.round(currentPreset.matchScore * 100)}% relevance score
                    </span>
                  </div>

                  <div className="flex items-center gap-3.5 rounded-xl border border-border/70 bg-card p-3 shadow-sm hover:border-primary/30 transition-colors">
                    <div className="size-16 shrink-0 overflow-hidden rounded-lg bg-muted">
                      {matchedProduct.image ? (
                        <img
                          src={matchedProduct.image}
                          alt={matchedProduct.name}
                          className="size-full object-cover"
                        />
                      ) : (
                        <div className="flex size-full items-center justify-center text-xs text-muted-foreground">
                          No photo
                        </div>
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-muted-foreground">{matchedProduct.brand}</p>
                      <h4 className="truncate text-sm font-semibold text-foreground">
                        {matchedProduct.name}
                      </h4>
                      <p className="text-xs font-medium text-primary mt-0.5">
                        ${matchedProduct.price} {matchedProduct.currency}
                      </p>
                    </div>
                    <Button
                      asChild
                      size="sm"
                      variant="ghost"
                      className="shrink-0 size-8 p-0 rounded-lg"
                    >
                      <Link
                        to="/product/$productId"
                        params={{ productId: matchedProduct.id }}
                        aria-label={`View ${matchedProduct.name}`}
                      >
                        <ArrowUpRight className="size-4" />
                      </Link>
                    </Button>
                  </div>
                </div>

                {/* Direct Action */}
                <div className="flex items-center justify-between border-t border-border/60 pt-4 text-xs">
                  <span className="text-muted-foreground">Looking for a different aesthetic?</span>
                  <Link
                    to="/search"
                    className="font-medium text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Browse matching query
                    <ChevronRight className="size-3.5" />
                  </Link>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* DISCOVERY CAPABILITIES (Asymmetric architectural grid) */}
      <section id="capabilities" className="mx-auto w-full max-w-7xl px-4 py-20 sm:px-6 lg:py-24">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <Badge variant="outline" className="mb-3 rounded-md px-2.5 py-1 text-xs font-medium">
              Multi-modal Engine
            </Badge>
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Engineered for complex shopping decisions.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
              Different purchases require different modes of discovery. CatalogIQ unifies natural
              language, styling, budget logic, and visual similarity into one catalog layer.
            </p>
          </div>

          <Button asChild variant="ghost" className="w-fit rounded-lg text-sm">
            <Link to="/dashboard">
              Merchant dashboard
              <ArrowUpRight className="ml-1.5 size-4" />
            </Link>
          </Button>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Card 1: Semantic Search (Expanded anchor) */}
          <Card className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-card transition-all duration-300 hover:border-primary/40 hover:shadow-elevated md:col-span-2 lg:col-span-2">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Search className="size-5" />
                </div>
                <Badge variant="secondary" className="text-xs font-medium">
                  Core Search
                </Badge>
              </div>

              <div>
                <h3 className="text-xl font-semibold tracking-tight text-foreground">
                  Semantic Search & Intent Resolution
                </h3>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
                  Traditional search requires exact keyword matches and fails when shoppers express
                  needs colloquially. CatalogIQ extracts attributes like weather resistance, fabric
                  weight, and silhouette directly from catalog descriptions.
                </p>
              </div>

              {/* Visual intent comparison box */}
              <div className="grid gap-3 pt-2 sm:grid-cols-2">
                <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-3.5 text-xs">
                  <p className="font-semibold text-destructive">Traditional Keyword Search</p>
                  <p className="mt-1 text-muted-foreground">
                    Query: <span className="font-mono">“breathable waterproof formal coat”</span>
                    <br />
                    Result: <span className="italic">0 exact matches found</span>
                  </p>
                </div>
                <div className="rounded-xl border border-primary/25 bg-primary/5 p-3.5 text-xs">
                  <p className="font-semibold text-primary">CatalogIQ Semantic Search</p>
                  <p className="mt-1 text-muted-foreground">
                    Matches 3-layer merino blends with water-repellent finishing at 98% confidence.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-border/60 pt-4">
              <span className="text-xs font-medium text-muted-foreground">
                Natural-language discovery
              </span>
              <Button asChild size="sm" variant="ghost" className="gap-1.5 text-xs font-medium">
                <Link to="/search">
                  Try search
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </Card>

          {/* Card 2: AI Shopping Copilot */}
          <Card className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-card transition-all duration-300 hover:border-primary/40 hover:shadow-elevated">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <MessageSquareText className="size-5" />
                </div>
                <Badge variant="secondary" className="text-xs font-medium">
                  Conversational
                </Badge>
              </div>

              <div>
                <h3 className="text-lg font-semibold tracking-tight text-foreground">
                  AI Shopping Copilot
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Chat with an assistant that knows every specification in your catalog. Compare
                  items side-by-side with transparent reasoning you can verify.
                </p>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-border/60 pt-4">
              <span className="text-xs font-medium text-muted-foreground">
                In-depth consultations
              </span>
              <Button asChild size="sm" variant="ghost" className="gap-1.5 text-xs font-medium">
                <Link to="/copilot">
                  Launch copilot
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </Card>

          {/* Card 3: AI Stylist */}
          <Card className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-card transition-all duration-300 hover:border-primary/40 hover:shadow-elevated">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Shirt className="size-5" />
                </div>
                <Badge variant="secondary" className="text-xs font-medium">
                  Curated Looks
                </Badge>
              </div>

              <div>
                <h3 className="text-lg font-semibold tracking-tight text-foreground">
                  AI Stylist & Outfit Pairing
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Assemble cohesive wardrobes based on occasion, aesthetic direction, and budget
                  caps, avoiding clashing fabrics and palettes.
                </p>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-border/60 pt-4">
              <span className="text-xs font-medium text-muted-foreground">Occasion styling</span>
              <Button asChild size="sm" variant="ghost" className="gap-1.5 text-xs font-medium">
                <Link to="/stylist">
                  Style an outfit
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </Card>

          {/* Card 4: Budget Optimizer */}
          <Card className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-card transition-all duration-300 hover:border-primary/40 hover:shadow-elevated">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Wallet className="size-5" />
                </div>
                <Badge variant="secondary" className="text-xs font-medium">
                  Smart Allocation
                </Badge>
              </div>

              <div>
                <h3 className="text-lg font-semibold tracking-tight text-foreground">
                  Budget Optimizer
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Tell the engine what you want to spend in total. It balances hero pieces with
                  foundational essentials without breaching your limit.
                </p>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-border/60 pt-4">
              <span className="text-xs font-medium text-muted-foreground">Spend optimization</span>
              <Button asChild size="sm" variant="ghost" className="gap-1.5 text-xs font-medium">
                <Link to="/budget">
                  Optimize cart
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </Card>

          {/* Card 5: Visual Search */}
          <Card className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-card transition-all duration-300 hover:border-primary/40 hover:shadow-elevated">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <Camera className="size-5" />
                </div>
                <Badge variant="secondary" className="text-xs font-medium">
                  Image Embeddings
                </Badge>
              </div>

              <div>
                <h3 className="text-lg font-semibold tracking-tight text-foreground">
                  Visual Similarity Search
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Upload an inspiration image or photo. CatalogIQ matches color schemes, textures,
                  and silhouettes against inventory items.
                </p>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between border-t border-border/60 pt-4">
              <span className="text-xs font-medium text-muted-foreground">Visual embeddings</span>
              <Button asChild size="sm" variant="ghost" className="gap-1.5 text-xs font-medium">
                <Link to="/visual-search">
                  Upload image
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </Card>
        </div>
      </section>

      {/* CURATED CATALOG SHOWCASE WITH REAL CATEGORY FILTERING */}
      <section className="border-y border-border/70 bg-muted/20 py-20 sm:py-24">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-primary">
                <Sparkles className="size-3.5" />
                <span>Live Catalog Inventory</span>
              </div>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl text-foreground">
                Curated items ready for discovery.
              </h2>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
                Explore real products indexed in our mock store. Filter by category or search with
                natural language.
              </p>
            </div>

            <Button asChild variant="outline" className="w-fit rounded-xl border-border">
              <Link to="/search">
                Open search explorer
                <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
          </div>

          {/* Category Filter Tabs */}
          <div className="mt-8 flex flex-wrap gap-2 border-b border-border/60 pb-4">
            {CATEGORIES.map((category) => (
              <button
                key={category}
                type="button"
                onClick={() => setSelectedCategory(category)}
                className={cn(
                  "rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors",
                  selectedCategory === category
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-card text-muted-foreground border border-border hover:bg-muted hover:text-foreground",
                )}
              >
                {category}
              </button>
            ))}
          </div>

          {/* Product Grid */}
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {filteredProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>

          {filteredProducts.length === 0 && (
            <div className="mt-12 rounded-xl border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
              No products available in this category.
            </div>
          )}
        </div>
      </section>

      {/* AI SHOPPING CONCIERGE / REASONING SHOWCASE */}
      <section className="mx-auto w-full max-w-7xl px-4 py-20 sm:px-6 lg:py-24">
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <div className="space-y-6">
            <Badge variant="outline" className="rounded-md px-2.5 py-1 text-xs font-medium">
              Transparent Reasoning
            </Badge>
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl text-foreground">
              An assistant that explains why, not just what.
            </h2>
            <p className="text-base leading-relaxed text-muted-foreground">
              Unlike black-box recommendation algorithms that prioritize ad revenue, CatalogIQ
              explains the logic behind every selection: fabric weight, water resistance ratings,
              budget headroom, and style harmony.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex items-start gap-3 rounded-xl border border-border/70 bg-card p-4">
                <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <Check className="size-4" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold">Multi-criteria trade-offs</h4>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Balances price limits against premium materials without dropping key
                    requirements.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 rounded-xl border border-border/70 bg-card p-4">
                <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <Check className="size-4" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold">Verified inventory availability</h4>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Never recommends out-of-stock sizes or phantom catalog records.
                  </p>
                </div>
              </div>
            </div>

            <Button asChild size="lg" className="rounded-xl px-6 text-sm font-medium">
              <Link to="/copilot">
                Chat with the copilot
                <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
          </div>

          {/* Interactive Assistant Dialogue Card */}
          <Card className="rounded-2xl border border-border/80 bg-card p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Bot className="size-4 text-primary" />
                <span>CatalogIQ Concierge</span>
              </div>
              <Badge variant="secondary" className="text-[11px]">
                Session Verified
              </Badge>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-xl rounded-tr-xs bg-primary px-3.5 py-2.5 text-primary-foreground">
                  “I need an outfit for an outdoor autumn dinner in Zurich. Formal, warm, under
                  $450.”
                </div>
              </div>

              <div className="flex justify-start">
                <div className="max-w-[90%] rounded-xl rounded-tl-xs border border-border/80 bg-muted/40 p-3.5 space-y-2 text-foreground">
                  <p className="leading-relaxed">
                    Here is a coordinated combination built from our inventory matching cold-weather
                    formality:
                  </p>
                  <div className="rounded-lg border border-border/60 bg-card p-2.5 space-y-1">
                    <p className="font-semibold text-foreground">
                      1. Aurora Merino Overcoat ($289)
                    </p>
                    <p className="text-muted-foreground text-[11px]">
                      Chosen for structured shoulder silhouette and natural temperature regulation
                      over knitwear.
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-card p-2.5 space-y-1">
                    <p className="font-semibold text-foreground">2. Court Leather Sneaker ($132)</p>
                    <p className="text-muted-foreground text-[11px]">
                      Full-grain leather cupsole matches smart-casual dress code while keeping feet
                      protected.
                    </p>
                  </div>
                  <div className="border-t border-border/60 pt-2 flex justify-between items-center text-[11px]">
                    <span className="font-medium text-foreground">
                      Total: $421 (Under $450 limit)
                    </span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      100% Intent Match
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* CLOSING EDITORIAL CTA */}
      <section className="mx-auto w-full max-w-7xl px-4 pb-20 sm:px-6 lg:pb-24">
        <div className="relative isolate overflow-hidden rounded-3xl border border-border/80 bg-gradient-to-br from-card via-card to-muted/40 p-8 sm:p-12 lg:p-16 shadow-elevated">
          <div className="grid items-center gap-8 md:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
                <Sparkles className="size-3.5" />
                <span>Next Generation Commerce</span>
              </div>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl text-foreground">
                Give your catalog the intelligence it deserves.
              </h2>
              <p className="max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
                Discover products through natural conversation, visual matching, and multi-modal
                styling. Start exploring today.
              </p>
              <div className="flex flex-wrap gap-4 pt-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <Check className="size-3.5 text-primary" />
                  No credit card required
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Check className="size-3.5 text-primary" />
                  Live mock catalog ready
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row md:flex-col md:items-end">
              <Button
                asChild
                size="lg"
                className="h-11 rounded-xl px-6 text-sm font-medium w-full sm:w-auto"
              >
                <Link to="/search">
                  Start searching catalog
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-11 rounded-xl border-border px-6 text-sm font-medium w-full sm:w-auto"
              >
                <Link to="/signup">Create free account</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
