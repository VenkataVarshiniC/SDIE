export function formatUsd(value: string | number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function formatCompactUsd(value: number): string {
  return `$${(value / 1_000_000).toFixed(1)}m`;
}
