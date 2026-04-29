import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoxPolítica · Tlaxcala",
  description:
    "Plataforma de inteligencia territorial: análisis demográfico estratégico y discurso político de alto impacto para los 60 municipios de Tlaxcala.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className="bg-ink">
      <body className="min-h-screen bg-ink font-body text-slate-200 antialiased selection:bg-sky-500/30">
        {children}
      </body>
    </html>
  );
}
