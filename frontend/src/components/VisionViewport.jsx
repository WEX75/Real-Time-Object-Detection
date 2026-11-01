import React, { useState } from 'react';
import { Stage, Layer, Rect } from 'react-konva';
import { useStore } from '../store';

export default function VisionViewport() {
  const latime = 640;
  const inaltime = 480;

  const adaugaZona = useStore((state) => state.adaugaZona);
  
  // Starea pentru desenul curent
  const [deseneaza, setDeseneaza] = useState(false);
  const [dreptunghi, setDreptunghi] = useState(null); // Va stoca {x, y, width, height}
  const [numeZona, setNumeZona] = useState('');

  // 1. Când apeși pe mouse (începi să desenezi)
  const handleMouseDown = (e) => {
    // Dacă avem deja un dreptunghi desenat, nu lăsăm utilizatorul să mai facă altul
    // până nu îl salvează sau îl șterge.
    if (dreptunghi !== null) return; 

    setDeseneaza(true);
    const poz = e.target.getStage().getPointerPosition();
    // Inițializăm un dreptunghi cu lățime și înălțime zero în punctul de click
    setDreptunghi({ x: poz.x, y: poz.y, width: 0, height: 0 });
  };

  // 2. Când miști mouse-ul (tragi de margini)
  const handleMouseMove = (e) => {
    if (!deseneaza) return;
    
    const poz = e.target.getStage().getPointerPosition();
    
    setDreptunghi((dreptVechi) => ({
      ...dreptVechi,
      // Calculăm noua lățime și înălțime pe baza poziției actuale a mouse-ului
      width: poz.x - dreptVechi.x,
      height: poz.y - dreptVechi.y,
    }));
  };

  // 3. Când eliberezi mouse-ul (ai terminat forma)
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

    // Normalizăm coordonatele în caz că a tras de la dreapta la stânga (lățime negativă)
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
    alert(`Zona "${numeZona}" a fost salvată!`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '15px' }}>
      
      <div style={{ display: 'flex', gap: '10px' }}>
        <input 
          type="text" 
          placeholder="Nume zonă (ex: Bar)" 
          value={numeZona}
          onChange={(e) => setNumeZona(e.target.value)}
          style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
        />
        <button onClick={handleSalveazaZona} style={{ padding: '8px 16px', cursor: 'pointer', backgroundColor: '#22c55e', color: 'white', border: 'none', borderRadius: '4px' }}>
          Salvează Zona
        </button>
        <button onClick={stergeDesen} style={{ padding: '8px 16px', cursor: 'pointer', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px' }}>
          Șterge
        </button>
      </div>

      <div style={{ position: 'relative', width: latime, height: inaltime, border: '2px solid #ccc' }}>
        <img 
          src="https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=640&q=80" 
          alt="Camera Test" 
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 0 }}
        />
        
        <div style={{ position: 'absolute', top: 0, left: 0, zIndex: 10, cursor: 'crosshair' }}>
          <Stage 
            width={latime} 
            height={inaltime} 
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            <Layer>
              {dreptunghi && (
                <Rect 
                  x={dreptunghi.x} 
                  y={dreptunghi.y} 
                  width={dreptunghi.width} 
                  height={dreptunghi.height} 
                  fill="rgba(0, 255, 0, 0.3)" 
                  stroke="#00ff00" 
                  strokeWidth={2} 
                />
              )}
            </Layer>
          </Stage>
        </div>
      </div>
      
    </div>
  );
}