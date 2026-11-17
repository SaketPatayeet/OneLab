// Formatting only: all financial calculations belong to the Python service.
export const label = (s) =>
  s.replaceAll("_", " ").replace(/^./, (x) => x.toUpperCase());
export const amount = (v, c) =>
  `${c} ${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
