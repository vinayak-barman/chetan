import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import { baseOptions } from '@/app/layout.config';
import { source } from '@/lib/source';
import { RootToggle } from "fumadocs-ui/components/layout/root-toggle";
import { BookIcon } from 'lucide-react';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      githubUrl='https://github.com/snayu-ai/chetan'
      {...baseOptions}
    >
      {children}
    </DocsLayout>
  );
}
