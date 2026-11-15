import React, { useState } from 'react';
import { Stage, Layer, Rect, Label, Tag, Text } from 'react-konva';
import { useStore } from '../store';

export default function VisionViewport() {
  const latime = 640;
  const inaltime = 480;

  const zoneDesenate = useStore((state) => state.zoneDesenate);
  const adaugaZona = useStore((state) => state.adaugaZona);

  const [deseneaza, setDeseneaza] = useState(false);
  const [dreptunghi, setDreptunghi] = useState(null);
  const [numeZona, setNumeZona] = useState('');

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
      nume: numeZona,
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
          placeholder="Nume zonă (ex: Masa 3)" 
          value={numeZona}
          onChange={(e) => setNumeZona(e.target.value)}
          className="flex-1 min-w-[200px] bg-slate-900 text-slate-100 placeholder-slate-500 px-3 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-emerald-400 text-sm"
        />
        <div className="flex gap-2">
          <button 
            onClick={handleSalveazaZona} 
            className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold px-4 py-2 rounded-lg text-sm transition cursor-pointer"
          >
            Salvează Zona
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
          src="https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=640&q=80" 
          alt="Camera Test" 
          className="absolute top-0 left-0 w-full h-full object-cover z-0 select-none"
        />
        
        <div className="absolute top-0 left-0 z-10 cursor-crosshair">
          <Stage 
            width={latime} 
            height={inaltime} 
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            <Layer>
              {/* Zonele deja salvate (afișate permanent cu albastru + etichetă clară) */}
              {zoneDesenate.map((zona) => (
                <React.Fragment key={zona.id}>
                  <Rect
                    x={zona.coordonate.x}
                    y={zona.coordonate.y}
                    width={zona.coordonate.width}
                    height={zona.coordonate.height}
                    fill="rgba(56, 189, 248, 0.2)"
                    stroke="#38bdf8"
                    strokeWidth={2}
                  />
                  <Label x={zona.coordonate.x} y={zona.coordonate.y}>
                    <Tag fill="#0f172a" cornerRadius={4} opacity={0.85} />
                    <Text
                      text={zona.nume}
                      fill="#38bdf8"
                      fontSize={13}
                      fontStyle="bold"
                      padding={5}
                    />
                  </Label>
                </React.Fragment>
              ))}

              {/* Dreptunghiul pe care îl desenezi în momentul de față (verde) */}
              {dreptunghi && (
                <Rect 
                  x={dreptunghi.x} 
                  y={dreptunghi.y} 
                  width={dreptunghi.width} 
                  height={dreptunghi.height} 
                  fill="rgba(16, 185, 129, 0.3)" 
                  stroke="#10b981" 
                  strokeWidth={2} 
                />
              )}
            </Layer>
          </Stage>
        </div>
      </div>

      <p className="text-xs text-slate-400 self-start">
        * Click și trage pe imagine pentru a delimita o zonă nouă. Zonele salvate rămân afișate cu albastru.
      </p>
    </div>
  );
}