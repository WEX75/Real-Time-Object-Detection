import React from 'react';
import { useStore } from '../store';

export default function EventLog() {
  const reguliActive = useStore((state) => state.reguliActive);
  const zoneDesenate = useStore((state) => state.zoneDesenate);
  const stergeRegula = useStore((state) => state.stergeRegula);

  const gasesteNumeZona = (idZona) => {
    const zona = zoneDesenate.find(z => z.id.toString() === idZona.toString());
    return zona ? zona.nume : 'Zonă necunoscută';
  };

  return (
    <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-xl text-slate-100">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="w-2 h-5 bg-sky-400 rounded-sm"></span>
          Reguli & Alerte
        </h2>
        <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
          {reguliActive.length} active
        </span>
      </div>
      
      {reguliActive.length === 0 ? (
        <p className="text-sm text-slate-400 italic py-4 text-center border border-dashed border-slate-700 rounded-lg">
          Nicio regulă activă momentan.
        </p>
      ) : (
        <ul className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
          {reguliActive.map((regula) => (
            <li 
              key={regula.id} 
              className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/80 text-sm flex items-center justify-between gap-2"
            >
              <div className="flex items-start gap-2.5">
                <span className="text-emerald-400 mt-0.5">●</span>
                <div>
                  <span className="text-slate-300">Monitorizare </span>
                  <strong className="text-emerald-400 font-semibold">{regula.obiect}</strong>
                  <span className="text-slate-300"> în zona </span>
                  <strong className="text-sky-400 font-semibold">{gasesteNumeZona(regula.zonaId)}</strong>
                </div>
              </div>
              <button
                onClick={() => stergeRegula(regula.id)}
                title="Șterge regula"
                className="text-slate-500 hover:text-rose-400 px-1.5 py-0.5 rounded transition cursor-pointer font-bold"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}