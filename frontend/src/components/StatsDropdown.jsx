import React, { useState } from 'react';
import { useStore } from '../store';

export default function StatsDropdown() {
  const [deschis, setDeschis] = useState(false);
  const statistici = useStore((state) => state.statistici);
  const reseteazaStatistici = useStore((state) => state.reseteazaStatistici);

  const listaStatistici = Object.values(statistici);
  const totalGeneral = listaStatistici.reduce((acc, item) => acc + item.total, 0);

  return (
    <div className="relative">
      {/* Butonul compact afișat în antet */}
      <button
        onClick={() => setDeschis(!deschis)}
        className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 rounded-full border border-slate-600 text-xs font-medium transition cursor-pointer shadow-sm"
      >
        <span>📊 Catalog Contoare</span>
        <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-bold">
          {totalGeneral}
        </span>
        <span className="text-slate-400 text-[10px] ml-0.5">
          {deschis ? '▲' : '▼'}
        </span>
      </button>

      {/* Meniul derulant care plutește peste interfață */}
      {deschis && (
        <div className="absolute right-0 mt-2 w-80 bg-slate-800 border border-slate-600 rounded-xl shadow-2xl z-50 p-4 text-slate-100">
          <div className="flex justify-between items-center pb-2.5 mb-3 border-b border-slate-700">
            <h3 className="text-sm font-semibold text-white">
              Catalog Detecții Cumulate
            </h3>
            {listaStatistici.length > 0 && (
              <button
                onClick={reseteazaStatistici}
                className="text-[11px] text-rose-400 hover:text-rose-300 underline cursor-pointer"
              >
                Resetează tot
              </button>
            )}
          </div>

          {listaStatistici.length === 0 ? (
            <p className="text-xs text-slate-400 italic text-center py-4">
              Nicio detecție contorizată încă. Creează o regulă și apasă „Simulează” pentru a vedea contoarele.
            </p>
          ) : (
            <ul className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {listaStatistici.map((item, idx) => (
                <li
                  key={idx}
                  className="flex items-center justify-between bg-slate-900/90 px-3 py-2 rounded-lg border border-slate-700/80 text-xs"
                >
                  <div>
                    <div className="font-semibold text-emerald-400 capitalize">
                      {item.obiect}
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Zonă: <span className="text-sky-300">{item.zona}</span>
                    </div>
                  </div>
                  <span className="bg-slate-800 text-white font-bold text-sm px-2.5 py-1 rounded-md border border-slate-600">
                    {item.total}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}