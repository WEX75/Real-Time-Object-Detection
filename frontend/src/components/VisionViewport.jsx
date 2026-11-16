import React, { useState } from 'react';
import { Stage, Layer, Rect, Label, Tag, Text } from 'react-konva';
import { useStore } from '../store';

const LIVE_STREAM_URL = 'http://localhost:8000/api/video_feed';
const FALLBACK_IMAGE_URL = 'https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=640&q=80';

export default function VisionViewport() {
  const latime = 640;
  const inaltime = 480;

  const zoneDesenate = useStore((state) => state.zoneDesenate);
  const adaugaZona = useStore((state) => state.adaugaZona);
  const stergeZona = useStore((state) => state.stergeZona);

  const [deseneaza, setDeseneaza] = useState(false);
  const [dreptunghi, setDreptunghi] = useState(null);
  const [numeZona, setNumeZona] = useState('');
  const [tipZona, setTipZona] = useState('normala'); // 'normala' | 'interzisa'
  const [folosesteFallback, setFolosesteFallback] = useState(false);

  const handleMouseDown = (e) => {
    if (dreptunghi !== null) return;
    setDeseneaza(true);
    const poz = e.target.getStage().getPointerPosition();
    setDreptunghi({ x: poz.x, y: poz.y, width: 0, height: 0 });
  };

  const handleMouseMove = (e) => {
    if (!deseneaza) return;
    const poz = e.target.getStage().getPointerPosition();
    setDreptunghi((dreptVechi) => ({
      ...dreptVechi,
      width: poz.x - dreptVechi.x,
      height: poz.y - dreptVechi.y,
    }));
  };

  const handleMouseUp = () => {
    setDeseneaza(false);
  };

  const stergeDesen = () => {
    setDreptunghi(null);
  };

  const handleSalveazaZona = () => {
    if (!dreptunghi || dreptunghi.width === 0 || dreptunghi.height === 0) {
      alert("Desenează un dreptunghi (click și trage pe imagine)!");
      return;
    }
    if (numeZona.trim() === '') {
      alert("Introdu un nume pentru zonă!");
      return;
    }

    const coordonateFinale = {
      x: dreptunghi.width < 0 ? dreptunghi.x + dreptunghi.width : dreptunghi.x,
      y: dreptunghi.height < 0 ? dreptunghi.y + dreptunghi.height : dreptunghi.y,
      width: Math.abs(dreptunghi.width),
      height: Math.abs(dreptunghi.height)
    };

    adaugaZona({
      id: Date.now(),
      nume: numeZona.trim(),
      tip: tipZona,
      coordonate: coordonateFinale
    });

    setDreptunghi(null);
    setNumeZona('');
  };

  return (
    <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-xl flex flex-col items-center gap-4">
      
      {/* Bara de control pentru zone */}
      <div className="w-full flex flex-wrap gap-2 justify-between items-center">
        <input 
          type="text" 
          placeholder="Nume zonă (ex: Casă Marcat)" 
          value={numeZona}
          onChange={(e) => setNumeZona(e.target.value)}
          className="flex-1 min-w-[160px] bg-slate-900 text-slate-100 placeholder-slate-500 px-3 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-emerald-400 text-sm"
        />

        <select
          value={tipZona}
          onChange={(e) => setTipZona(e.target.value)}
          className="bg-slate-900 text-slate-100 px-3 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-emerald-400 text-sm"
        >
          <option value="normala">🔵 Zonă Normală</option>
          <option value="interzisa">🔴 Zonă Interzisă (Alarmă)</option>
        </select>

        <div className="flex gap-2">
          <button 
            onClick={handleSalveazaZona} 
            className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold px-4 py-2 rounded-lg text-sm transition cursor-pointer"
          >
            Salvează
          </button>
          <button 
            onClick={stergeDesen} 
            className="bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/40 font-medium px-3 py-2 rounded-lg text-sm transition cursor-pointer"
          >
            Anulează
          </button>
        </div>
      </div>

      {/* Containerul video + canvas */}
      <div className="relative rounded-lg overflow-hidden border border-slate-600 shadow-inner" style={{ width: latime, height: inaltime }}>
        <img 
          src={folosesteFallback ? FALLBACK_IMAGE_URL : LIVE_STREAM_URL}
          onError={() => {
            if (!folosesteFallback) setFolosesteFallback(true);
          }}
          alt="Camera Feed" 
          className="absolute top-0 left-0 w-full h-full object-cover z-0 select-none"
        />
        
        <div className="absolute top-2 right-2 z-20 pointer-events-none">
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${folosesteFallback ? 'bg-slate-900/80 text-amber-400 border border-amber-500/30' : 'bg-rose-600 text-white'}`}>
            {folosesteFallback ? 'Offline • Imagine Test' : '● LIVE'}
          </span>
        </div>

        <div className="absolute top-0 left-0 z-10 cursor-crosshair">
          <Stage 
            width={latime} 
            height={inaltime} 
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            <Layer>
              {zoneDesenate.map((zona) => {
                const esteInterzisa = zona.tip === 'interzisa';
                return (
                  <React.Fragment key={zona.id}>
                    <Rect
                      x={zona.coordonate.x}
                      y={zona.coordonate.y}
                      width={zona.coordonate.width}
                      height={zona.coordonate.height}
                      fill={esteInterzisa ? "rgba(244, 63, 94, 0.25)" : "rgba(56, 189, 248, 0.2)"}
                      stroke={esteInterzisa ? "#f43f5e" : "#38bdf8"}
                      strokeWidth={2}
                    />
                    <Label x={zona.coordonate.x} y={zona.coordonate.y}>
                      <Tag fill="#0f172a" cornerRadius={4} opacity={0.9} />
                      <Text
                        text={esteInterzisa ? `🔊 ${zona.nume}` : zona.nume}
                        fill={esteInterzisa ? "#fb7185" : "#38bdf8"}
                        fontSize={13}
                        fontStyle="bold"
                        padding={5}
                      />
                    </Label>
                  </React.Fragment>
                );
              })}

              {dreptunghi && (
                <Rect 
                  x={dreptunghi.x} 
                  y={dreptunghi.y} 
                  width={dreptunghi.width} 
                  height={dreptunghi.height} 
                  fill={tipZona === 'interzisa' ? "rgba(244, 63, 94, 0.3)" : "rgba(16, 185, 129, 0.3)"} 
                  stroke={tipZona === 'interzisa' ? "#f43f5e" : "#10b981"} 
                  strokeWidth={2} 
                />
              )}
            </Layer>
          </Stage>
        </div>
      </div>

      {/* Lista zonelor salvate cu buton de ștergere */}
      <div className="w-full flex flex-wrap items-center justify-between gap-2 pt-1">
        <p className="text-xs text-slate-400">
          * Zonele roșii declanșează alarmă sonoră la detecție.
        </p>
        {zoneDesenate.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {zoneDesenate.map((zona) => {
              const esteInterzisa = zona.tip === 'interzisa';
              return (
                <span 
                  key={zona.id} 
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
                    esteInterzisa 
                      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30' 
                      : 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                  }`}
                >
                  {esteInterzisa && '🔊'} {zona.nume}
                  <button
                    onClick={() => stergeZona(zona.id)}
                    title="Șterge zona"
                    className="hover:text-white font-bold ml-1 cursor-pointer"
                  >
                    ✕
                  </button>
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}