import { cn } from 'fumadocs-ui/components/api';
import './global.css';
import { DM_Mono, Inter, Space_Grotesk } from 'next/font/google';
import type { ReactNode } from 'react';
import { RootProvider } from 'fumadocs-ui/provider';

import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";


import { AISearchTrigger } from "@/components/ai";

import { MessageCircle } from 'lucide-react';
import { BorderBeam } from '@/components/magicui/border-beam';

const inter = Inter({
  subsets: ['latin'],
});

const codeFont = DM_Mono({
  subsets: ["latin"],
  variable: "--default-mono-font-family",
  display: "swap",
  weight: "400",
});

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={cn(inter.className, codeFont.variable)}
      suppressHydrationWarning
    >
      <head>
        <link rel="icon" href="/chetan.ico" sizes="any" />
      </head>
      <body className="flex flex-col min-h-screen bg-background">
        <Analytics />
        <SpeedInsights />
        <RootProvider
          search={{
            enabled: true,
            options: {
              defaultTag: "examples",
              tags: [
                {
                  name: "Framework",
                  value: "framework",
                },
                {
                  name: "Guide",
                  value: "guide",
                },
                {
                  name: "Examples",
                  value: "examples",
                },
              ],
            },
          }}
        >
          {children}
          <AISearchTrigger className="overflow-hidden border">
            <BorderBeam
              duration={6}
              size={200}
              className="from-transparent via-pink-500 to-transparent"
            />
            <BorderBeam
              duration={6}
              delay={3}
              size={200}
              className="from-transparent via-indigo-500 to-transparent"
            />
            <MessageCircle className="size-4" />
            Ask Agent
          </AISearchTrigger>
        </RootProvider>
      </body>
    </html>
  );
}
