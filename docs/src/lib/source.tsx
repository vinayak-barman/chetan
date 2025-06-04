import { docs } from "@/.source";
import { loader } from "fumadocs-core/source";

import { icons } from "lucide-react";
import { createElement } from "react";

import { ChetanIcon, MCPIcon, RAGIcon, RingTopology, ZerveIcon } from "./icons";

export function icon(
  icon: string | undefined,
  props: React.SVGProps<SVGSVGElement> = { height: 20, width: 20 }
) {
  if (!icon) {
    // You may set a default icon
    return;
  }

  switch (icon) {
    case "MCP":
      return <MCPIcon {...props} />;
    case "RAG":
      return <RAGIcon {...props} />;
    case "Chetan":
      return <ChetanIcon {...props} />;
    case "Zerve":
      return <ZerveIcon {...props} />;
    case "RingTopology":
      return <RingTopology {...props} />;
  }

  if (icon in icons) return createElement(icons[icon as keyof typeof icons]);
}

// `loader()` also assign a URL to your pages
// See https://fumadocs.vercel.app/docs/headless/source-api for more info
export const source = loader({
  baseUrl: "/docs",
  source: docs.toFumadocsSource(),
  icon: icon,
});
