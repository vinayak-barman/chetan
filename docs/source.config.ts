import { defineDocs, defineConfig } from 'fumadocs-mdx/config';
import { rehypeCodeDefaultOptions } from "fumadocs-core/mdx-plugins";
import { remarkMermaid } from "@theguild/remark-mermaid";
 
export const docs = defineDocs({
  dir: 'content/docs',
});

export default defineConfig({
  mdxOptions: {
    rehypeCodeOptions: {
      themes: {
        light: "catppuccin-latte",
        dark: "houston",
      },
      transformers: [...(rehypeCodeDefaultOptions.transformers ?? [])],
    },
    remarkPlugins: [remarkMermaid],
  },
});
