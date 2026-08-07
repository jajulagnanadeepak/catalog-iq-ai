import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/layout/brand";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create your workspace — CatalogIQ AI" },
      {
        name: "description",
        content: "Sign up for CatalogIQ AI and connect your product catalog in minutes.",
      },
      { property: "og:title", content: "Create your workspace — CatalogIQ AI" },
      { property: "og:description", content: "Connect your product catalog in minutes." },
    ],
  }),
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      toast.success("Workspace created — welcome aboard");
      navigate({ to: "/dashboard" });
    }, 800);
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center px-4 py-16">
        <Card className="w-full max-w-sm animate-rise gap-6 p-8 shadow-card">
          <Logo />
          <div>
            <h1 className="text-2xl font-semibold">Create your workspace</h1>
            <p className="mt-1 text-sm text-muted-foreground">Free for the first 10k queries.</p>
          </div>

          <form className="space-y-4" onSubmit={submit}>
            <div className="space-y-2">
              <Label htmlFor="name">Full name</Label>
              <Input id="name" required placeholder="Ada Rivers" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Work email</Label>
              <Input id="email" type="email" required placeholder="you@company.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required placeholder="At least 8 characters" />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4" />}
              Create account
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-primary hover:underline">
              Log in
            </Link>
          </p>
        </Card>
      </div>

      <div className="hidden flex-col justify-between gradient-hero p-12 text-primary-foreground lg:flex">
        <div />
        <div>
          <h2 className="max-w-sm text-4xl font-semibold leading-tight">
            Ship AI discovery without touching your storefront stack.
          </h2>
          <ul className="mt-8 space-y-3 text-primary-foreground/90">
            {["Semantic + visual search", "Conversational shopping copilot", "Budget-aware bundling"].map(
              (item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="size-1.5 rounded-full bg-primary-foreground" />
                  {item}
                </li>
              ),
            )}
          </ul>
        </div>
        <p className="text-xs text-primary-foreground/70">© CatalogIQ AI</p>
      </div>
    </div>
  );
}
