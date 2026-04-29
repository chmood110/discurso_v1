import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Tiny class-name helper used across the design system.
 * Combines clsx (conditional classes) with tailwind-merge (last-class-wins
 * conflict resolution) so consumers can override variant defaults without
 * fighting class duplication.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
