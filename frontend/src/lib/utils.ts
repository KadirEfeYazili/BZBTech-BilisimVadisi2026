import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind sınıflarını çakışmaları çözerek birleştirir. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
