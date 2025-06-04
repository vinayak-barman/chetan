import { cn } from "@/lib/utils";
import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";
import { BookIcon } from "lucide-react";

/**
 * Shared layout configurations
 *
 * you can customise layouts individually from:
 * Home Layout: app/(home)/layout.tsx
 * Docs Layout: app/docs/layout.tsx
 */
export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          id="svg1"
          width="24"
          height="24"
          version="1.1"
          viewBox="0 0 54.793 54.952"
          className="p-0.5"
        >
          <g id="layer1" transform="translate(-40.384 -56.742)">
            <path
              id="path1"
              fill="currentColor"
              strokeWidth="0.25"
              d="M56.604 73.355H92.37a2.096 2.096 111.709 0 0 1.44-3.619L80.079 56.742H46.671a6.287 6.287 135 0 0-6.287 6.287v26.778a8.32 8.32 65.795 0 0 2.797 6.222l14.069 12.487a12.6 12.6 20.795 0 0 8.369 3.178h26.036a3.522 3.522 120.487 0 0 3.08-5.23l-4.052-7.301a7.43 7.43 30.487 0 0-6.5-3.827H56.094a4.796 4.796 44.953 0 1-4.796-4.788l-.02-11.86a5.325 5.325 134.953 0 1 5.326-5.333"
            ></path>
          </g>
        </svg>
        <span className={cn("font-semibold text-lg tracking-tight")}>Chetan</span>
      </>
    ),
  },
};
