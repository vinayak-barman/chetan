"use client";
import { type ButtonHTMLAttributes, useState } from "react";
import dynamic from "next/dynamic";
import { cn } from "fumadocs-ui/components/api";
import { Button, buttonVariants } from "@/components/ui/button";

// lazy load the dialog
const SearchAI = dynamic(() => import("./search"), { ssr: false });

/**
 * The trigger component for AI search dialog.
 *
 * Use it like a normal button component.
 */
export function AISearchTrigger(
  props: ButtonHTMLAttributes<HTMLButtonElement>
) {
  const [open, setOpen] = useState<boolean>();

  return (
    <>
      {open !== undefined ? (
        <SearchAI open={open} onOpenChange={setOpen} />
      ) : null}
      <Button
        {...props}
        onClick={() => setOpen(true)}
        size={"lg"}
        variant={"secondary"}
        className={cn(
          "fixed bottom-4 right-4 z-10 gap-2 rounded-xl text-foreground bg-muted/20 shadow-md backdrop-blur-lg md:bottom-8 md:right-8 hover:bg-foreground hover:text-background cursor-pointer",
          props.className
        )}
      />
    </>
  );
}
