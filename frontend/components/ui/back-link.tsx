import Link from "next/link";

export function BackLink() {
  return (
    <Link
      href="/"
      className="group inline-flex items-center gap-1.5 text-sm text-muted hover:text-parchment transition-colors w-fit"
    >
      <span className="inline-block transition-transform duration-200 ease-out group-hover:-translate-x-1">
        ←
      </span>
      Back to overview
    </Link>
  );
}
