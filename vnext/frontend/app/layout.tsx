import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoxPolítica Tlaxcala",
  description: "Plataforma de inteligencia territorial para Tlaxcala",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-slate-50 font-sans antialiased">{children}</body>
    </html>
  );
}
