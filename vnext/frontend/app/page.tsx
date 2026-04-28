import Link from "next/link";

const modules = [
  {
    href: "/analysis",
    label: "Análisis Territorial",
    desc: "Diagnóstico INEGI/CONEVAL + estrategia de comunicación integrada",
    tag: "60 municipios · Datos reales · Estrategia IA",
    color: "emerald",
  },
  {
    href: "/speech",
    label: "Discurso Político",
    desc: "Crea un discurso desde cero o mejora uno existente hasta 10/10",
    tag: "Crear · Mejorar · PDF inline",
    color: "blue",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-xl">
        <div className="mb-10 text-center">
          <p className="text-xs font-bold tracking-[0.2em] text-emerald-400 uppercase mb-3">
            VoxPolítica · Tlaxcala
          </p>
          <h1 className="text-4xl font-bold text-white mb-2 leading-tight">
            Inteligencia Territorial
          </h1>
          <p className="text-slate-400 text-sm">
            60 municipios · INEGI 2020 · CONEVAL 2020 · IA estratégica
          </p>
        </div>

        <div className="grid gap-4">
          {modules.map((m) => (
            <Link
              key={m.href}
              href={m.href}
              className="group relative overflow-hidden rounded-2xl bg-slate-800 border border-slate-700 px-6 py-6 hover:border-emerald-500 hover:bg-slate-750 transition-all duration-200"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white mb-1">{m.label}</h2>
                  <p className="text-sm text-slate-400 mb-3">{m.desc}</p>
                  <span className="inline-block text-xs font-medium text-emerald-400 bg-emerald-950 border border-emerald-800 rounded-full px-3 py-0.5">
                    {m.tag}
                  </span>
                </div>
                <span className="text-slate-600 group-hover:text-emerald-400 text-2xl ml-4 mt-1 transition-colors">
                  →
                </span>
              </div>
            </Link>
          ))}
        </div>

        <p className="text-center text-xs text-slate-600 mt-8">
          VoxPolítica 2.0 · Estado de Tlaxcala, México
        </p>
      </div>
    </main>
  );
}