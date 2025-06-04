import * as icons from "lucide-react";
import React from "react";
import { icon, source } from "./source";

export function stringToIcon(
  iconName?: string,
  props: React.SVGProps<SVGSVGElement> = {height: 20, width: 20}
): React.ReactElement | undefined {

  return icon(iconName, props)
}