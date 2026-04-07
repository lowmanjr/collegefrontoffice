/**
 * Shared utility functions.
 * Import formatCurrency from here — do not redefine it in individual files.
 */

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}
