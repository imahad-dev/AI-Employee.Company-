import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Software Company",
  description: "Local-first autonomous software company dashboard"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

