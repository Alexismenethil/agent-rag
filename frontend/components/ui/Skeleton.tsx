"use client";

// Skeleton con brillo animado (shimmer) para estados de carga.
// Restyle "clean premium": superficie f5f5f7 con barrido sobre hairline.

export function Skeleton({
  width,
  height = 16,
  radius = 10,
  style,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number;
  style?: React.CSSProperties;
}) {
  return (
    <span
      aria-hidden
      className="skeleton-shimmer block"
      style={{
        width: width ?? "100%",
        height,
        borderRadius: radius,
        ...style,
      }}
    />
  );
}
