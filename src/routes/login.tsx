import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/layout/brand";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Log in — CatalogIQ AI" },
      { name: "description", content: "Access your CatalogIQ AI catalog intelligence workspace." },
      { property: "og:title", content: "Log in — CatalogIQ AI" },
      { property: "og:description", content: "Access your CatalogIQ AI workspace." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      toast.success("Welcome back to CatalogIQ AI");
      navigate({ to: "/dashboard" });
    }, 700);
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between gradient-hero p-12 text-primary-foreground lg:flex">
        <Logo />
        <div>
          <h2 className="max-w-sm text-4xl font-semibold leading-tight">
            Discovery that understands intent, not keywords.
          </h2>
          <p className="mt-4 max-w-sm text-primary-foreground/85">
            Teams using CatalogIQ AI see a 31% lift in add-to-cart rate within the first quarter.
          </p>
        </div>
        <p className="text-xs text-primary-foreground/70">© CatalogIQ AI</p>
      </div>

      <div className="flex items-center justify-center px-4 py-16">
        <Card className="w-full max-w-sm animate-rise gap-6 p-8 shadow-card">
          <div className="lg:hidden">
            <Logo />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Log in</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Enter your credentials to continue.
            </p>
          </div>

          <form className="space-y-4" onSubmit={submit}>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required placeholder="you@company.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required placeholder="••••••••" />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4" />}
              Log in
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link to="/signup" className="font-medium text-primary hover:underline">
              Create one
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
