import Link from "next/link";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI News Intelligence",
  description: "Real-time intelligence for offensive AI and enterprise AI adoption",
};

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/events", label: "Events" },
  { href: "/search", label: "Search" },
  { href: "/archive", label: "Archive" },
  { href: "/sources", label: "Sources" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-white/10 px-6 py-3 flex items-center gap-8">
          <Link href="/" className="font-semibold text-neutral-50">
            AI News <span className="text-sky-400">Intel</span>
          </Link>
          <nav className="flex gap-5 text-sm text-neutral-400">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className="hover:text-neutral-100">
                {item.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="px-6 py-6 max-w-6xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
