import React, { useState } from 'react';
import { useStore } from '../store';

export default function ControlPanel() {
  const zoneDesenate = useStore((state) => state.zoneDesenate);
  const adaugaRegula = useStore((state) => state.adaugaRegula);

  const [obiect, setObiect] = useState('');
  const [zonaSelectata, setZonaSelectata] = useState('');

  const handleSalveazaRegula = () => {
    if (!obiect.trim()) {
      alert("Scrie un obiect (ex: cană, rucsac, persoană)!");
      return;
    }
    if (!zonaSelectata) {
      alert("Selectează o zonă!");
      return;
    }

    adaugaRegula({ id: Date.now(), obiect: obiect.trim(), zonaId: zonaSelectata });
    setObiect('');
    setZonaSelectata('');
  };

  return (
    <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-xl text-slate-100">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span className="w-2 h-5 bg-emerald-400 rounded-sm"></span>
        Editor de Reguli
      </h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1.5">
            Ce obiect urmărim?
          </label>
          <input 
            type="text" 
            value={obiect}
            onChange={(e) => setObiect(e.target.value)}
            placeholder="ex: cană, rucsac, persoană" 
            className="w-full bg-slate-900 text-slate-100 placeholder-slate-500 px-3 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-emerald-400 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1.5">
            În ce zonă?
          </label>
          <select 
            value={zonaSelectata} 
            onChange={(e) => setZonaSelectata(e.target.value)}
            className="w-full bg-slate-900 text-slate-100 px-3 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-emerald-400 text-sm"
          >
            <option value="">-- Alege o zonă salvată --</option>
            {zoneDesenate.map((zona) => (
              <option key={zona.id} value={zona.id}>
                {zona.nume}
              </option>
            ))}
          </select>
        </div>

        <button 
          onClick={handleSalveazaRegula}
          className="w-full bg-sky-500 hover:bg-sky-600 text-slate-950 font-semibold py-2.5 rounded-lg text-sm transition cursor-pointer shadow-md"
        >
          + Creează Regula
        </button>
      </div>
    </div>
  );
}