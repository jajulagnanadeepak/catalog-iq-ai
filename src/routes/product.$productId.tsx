import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/product/$productId")({
  component: ProductPage,
});

function ProductPage() {
  return null;
}
