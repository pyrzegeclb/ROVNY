/** Displays the supplied brand sheet without modifying the source artwork. */
export function BrandMark({ className = '' }: { className?: string }) {
  return <span className={`brand-mark ${className}`} role="img" aria-label="ROVNY logosu" />;
}
