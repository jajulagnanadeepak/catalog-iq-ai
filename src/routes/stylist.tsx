import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/stylist")({
  component: StylistPage,
});

function StylistPage() {
  return null;
}
