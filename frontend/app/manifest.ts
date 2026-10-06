import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/worship-mix",
    name: "Worship Mix",
    short_name: "Worship Mix",
    description: "AI co-pilot for worship mixing and mastering, on any console.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#09090c",
    theme_color: "#09090c",
    orientation: "any",
    categories: ["music", "utilities"],
    icons: [],
  };
}
