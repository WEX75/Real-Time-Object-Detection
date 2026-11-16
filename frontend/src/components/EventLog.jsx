import React from 'react';
import { useStore } from '../store';
import { redaAlarmaSonora } from '../soundAlert';

export default function EventLog() {
  const reguliActive = useStore((state) => state.reguliActive);
  const zoneDesenate = useStore((state) => state.zoneDesenate);
  const stergeRegula = useStore((state) => state.stergeRegula);
  const alerteLive = useStore((state) => state.alerteLive);
  const adaugaAlerta = useStore((state) => state.adaugaAlerta);
  const golesteAlerte = useStore((state) => state.golesteAlerte);

  const gasesteZona = (idZona) => {
    return zoneDesenate.find(z => z.id.toString() === idZona.toString());
  };

  const handleSimuleazaAlerta = () => {
    if (reguliActive.length === 0) {
      alert("Creează mai întâi cel puțin o regulă pentru a putea simula o detecție!");
      return;
    }

    const regulaAleatorie = reguliActive[Math.floor(Math.random() * reguliActive.length)];
    const zonaGasita = gasesteZona(regulaAleatorie.zonaId);
    const esteCritica = zonaGasita?.tip === 'interzisa';
    const oraCurenta = new Date().toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    if (esteCritica) {
      redaAlarmaSonora();
    }

    adaugaAlerta({
      id: Date.now(),
      obiect: regulaAleatorie.obiect,
      zona: zonaGasita ? zonaGasita.nume : 'Zonă necunoscută',
      critica: esteCritica,
      ora: oraCurenta,
      incredere: Math.floor(Math.random() * (98 - 82 + 1)) + 82
    });
  };

  return (
    <div className="flex flex-col gap-6">
      
      {/* Secțiunea 1: Reguli Active */}
      <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-xl text-slate-100">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-5 bg-sky-400 rounded-sm"></span>
            Reguli Active
          </h2>
          <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
            {reguliActive.length} active
          </span>
        </div>
        
        {reguliActive.length === 0 ? (
          <p className="text-sm text-slate-400 italic py-3 text-center border border-dashed border-slate-700 rounded-lg">
            Nicio regulă activă momentan.
          </p>
        ) : (
          <ul className="space-y-2 max-h-44 overflow-y-auto pr-1">
            {reguliActive.map((regula) => {
              const zona = gasesteZona(regula.zonaId);
              const esteInterzisa = zona?.tip === 'interzisa';
              return (
                <li 
                  key={regula.id} 
                  className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-700/80 text-sm flex items-center justify-between gap-2"
                >
                  <div className="flex items-start gap-2">
                    <span className={esteInterzisa ? "text-rose-400 mt-0.5" : "text-emerald-400 mt-0.5"}>●</span>
                    <div>
                      <strong className="text-emerald-400 font-semibold">{regula.obiect}</strong>
                      <span className="text-slate-400"> → </span>
                      <strong className={esteInterzisa ? "text-rose-400 font-semibold" : "text-sky-400 font-semibold"}>
                        {zona ? zona.nume : 'Zonă necunoscută'}
                      </strong>
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
              );
            })}
          </ul>
        )}
      </div>

      {/* Secțiunea 2: Istoric Alerte Live */}
      <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-xl text-slate-100">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-5 bg-amber-400 rounded-sm"></span>
            Alerte Live
          </h2>
          <div className="flex gap-2">
            <button
              onClick={handleSimuleazaAlerta}
              className="text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 px-2.5 py-1 rounded-md font-medium transition cursor-pointer"
            >
              ⚡ Simulează
            </button>
            {alerteLive.length > 0 && (
              <button
                onClick={golesteAlerte}
                className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-2 py-1 rounded-md transition cursor-pointer"
              >
                Curăță
              </button>
            )}
          </div>
        </div>

        {alerteLive.length === 0 ? (
          <p className="text-sm text-slate-400 italic py-3 text-center border border-dashed border-slate-700 rounded-lg">
            Nicio detecție înregistrată. Apasă „Simulează” pentru test.
          </p>
        ) : (
          <ul className="space-y-2 max-h-52 overflow-y-auto pr-1">
            {alerteLive.map((alerta) => (
              <li 
                key={alerta.id}
                className={`p-2.5 rounded-lg text-xs flex justify-between items-center border ${
                  alerta.critica 
                    ? 'bg-rose-950/50 border-rose-500/50' 
                    : 'bg-amber-950/30 border-amber-500/30'
                }`}
              >
                <div>
                  <span className={`font-bold uppercase mr-1.5 ${alerta.critica ? 'text-rose-400' : 'text-amber-400'}`}>
                    {alerta.critica ? '🔊 [INTRUZIUNE]' : '[ALERTĂ]'}
                  </span>
                  <span className="text-slate-200">
                    Detectat <strong className="text-white">{alerta.obiect}</strong> în{' '}
                    <strong className={alerta.critica ? 'text-rose-300' : 'text-sky-300'}>{alerta.zona}</strong>
                  </span>
                </div>
                <div className="text-right text-slate-400 shrink-0 ml-2">
                  <div>{alerta.ora}</div>
                  <div className="text-[10px] text-emerald-400">{alerta.incredere}% conf.</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

    </div>
  );
}