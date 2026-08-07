import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Brain,
  Camera,
  LineChart,
  MessageSquareText,
  Search,
  Shirt,
  Sparkles,
  Wallet,
} from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProductCard } from "@/components/catalog/product-card";
import { PRODUCTS } from "@/lib/api/mock";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CatalogIQ AI — AI-powered product discovery for commerce" },
      {
        name: "description",
        content:
          "Semantic search, an AI shopping copilot, visual search and budget optimisation on top of your existing product catalog.",
      },
      { property: "og:title", content: "CatalogIQ AI — AI-powered product discovery" },
      {
        property: "og:description",
        content: "Turn your catalog into an intelligent shopping assistant with CatalogIQ AI.",
      },
    ],
  }),
  component: Landing,
});

const features = [
  {
    icon: Search,
    title: "Semantic Search",
    body: "Natural-language queries resolved against catalog embeddings, not keyword tables.",
    to: "/search",
  },
  {
    icon: MessageSquareText,
    title: "Shopping Copilot",
    body: "A conversational agent that narrows, compares and explains every recommendation.",
    to: "/copilot",
  },
  {
    icon: Shirt,
    title: "AI Stylist",
    body: "Complete looks assembled from occasion, style and body-type signals.",
    to: "/stylist",
  },
  {
    icon: Wallet,
    title: "Budget Optimizer",
    body: "Maximise basket value against a hard budget ceiling across categories.",
    to: "/budget",
  },
  {
    icon: Camera,
    title: "Visual Search",
    body: "Upload any image and match it against the catalog by shape, colour and texture.",
    to: "/visual-search",
  },
  {
    icon: LineChart,
    title: "Seasonal Intelligence",
    body: "Climate and trend signals surfaced as ready-to-merchandise collections.",
    to: "/seasonal",
  },
] as const;

function Landing() {
  return (
    <div className="min-h-screen">
      <Navbar />

      <section className="relative overflow-hidden surface-glow">
        <div className="mx-auto grid w-full max-w-7xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
          <div className="animate-rise">
            <Badge variant="secondary" className="gap-1.5">
              <Sparkles className="size-3.5" /> Catalog intelligence, live
            </Badge>
            <h1 className="mt-6 text-4xl font-semibold leading-[1.05] sm:text-6xl">
              Your catalog,{" "}
              <span className="text-gradient">finally able to answer questions</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg text-muted-foreground">
              CatalogIQ AI layers semantic search, styling, visual matching and budget optimisation
              over the products you already sell — no re-platforming required.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/signup">
                  Start free <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/dashboard">View live dashboard</Link>
              </Button>
            </div>
            <dl className="mt-12 grid max-w-md grid-cols-3 gap-6">
              {[
                ["128k", "SKUs indexed"],
                ["82ms", "p95 latency"],
                ["+31%", "conversion lift"],
              ].map(([value, label]) => (
                <div key={label}>
                  <dt className="font-display text-2xl font-semibold">{value}</dt>
                  <dd className="text-xs text-muted-foreground">{label}</dd>
                </div>
              ))}
            </dl>
          </div>

          <Card className="animate-rise gap-4 p-6 shadow-elevated">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Brain className="size-4 text-primary" /> Live query trace
            </div>
            <div className="rounded-lg border border-border bg-muted/40 p-4 font-mono text-xs">
              <p className="text-muted-foreground">POST /search</p>
              <p className="mt-2">
                {"{"} "query": "warm coat for a rainy commute under $300" {"}"}
              </p>
              <p className="mt-3 text-primary">→ intent: product_discovery (0.94)</p>
              <p className="text-primary">→ filters: category=Outerwear, price&lt;=300</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {PRODUCTS.slice(0, 2).map((p) => (
                <ProductCard key={p.id} product={p} score={0.93} />
              ))}
            </div>
          </Card>
        </div>
      </section>

      <section id="features" className="mx-auto w-full max-w-7xl px-4 py-20 sm:px-6">
        <h2 className="max-w-2xl text-3xl font-semibold sm:text-4xl">
          Eight AI surfaces, one catalog index
        </h2>
        <p className="mt-4 max-w-xl text-muted-foreground">
          Every module reads from the same product graph, so recommendations stay consistent across
          search, chat and styling.
        </p>

        <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <Link key={f.title} to={f.to}>
              <Card className="h-full gap-3 p-6 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-elevated">
                <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                  <f.icon className="size-5" />
                </span>
                <h3 className="text-lg font-semibold">{f.title}</h3>
                <p className="text-sm text-muted-foreground">{f.body}</p>
                <span className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary">
                  Explore <ArrowRight className="size-3.5" />
                </span>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-4 pb-20 sm:px-6">
        <div className="flex items-end justify-between gap-4">
          <h2 className="text-2xl font-semibold sm:text-3xl">Trending in the index</h2>
          <Button asChild variant="ghost">
            <Link to="/search">
              Browse all <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {PRODUCTS.slice(2, 6).map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-4 pb-24 sm:px-6">
        <Card className="items-center gap-4 gradient-hero p-12 text-center text-primary-foreground shadow-elevated">
          <h2 className="text-3xl font-semibold sm:text-4xl">Ready to make your catalog think?</h2>
          <p className="max-w-xl text-primary-foreground/85">
            Connect your product feed and go live with semantic discovery in an afternoon.
          </p>
          <Button asChild size="lg" variant="secondary">
            <Link to="/signup">Create your workspace</Link>
          </Button>
        </Card>
      </section>

      <Footer />
    </div>
  );
}
