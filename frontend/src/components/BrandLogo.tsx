export function BrandLogo({ className = "" }: { className?: string }) {
  return (
    <span className={`brand-logo ${className}`}>
      <img
        src="/brand/elqovanta-ev-logo.png"
        alt="Elqovanta EV"
        width="2172"
        height="724"
      />
    </span>
  );
}
