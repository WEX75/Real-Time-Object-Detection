import React, { useState } from 'react';
import { useStore } from '../store';

export default function ControlPanel() {
  // Extragem zonele ca să le afișăm în meniu, și funcția de adăugare reguli
  const zoneDesenate = useStore((state) => state.zoneDesenate);
  const adaugaRegula = useStore((state) => state.adaugaRegula);

  const [obiect, setObiect] = useState('');
  const [zonaSelectata, setZonaSelectata] = useState('');

  const handleSalveazaRegula = () => {
    if (!obiect) {
      alert("Te rog să scrii un obiect (ex: cană, persoană)!");
      return;
    }
    if (!zonaSelectata) {
      alert("Te rog să selectezi o zonă!");
      return;
    }

    // Împachetăm regula și o trimitem în seif
    adaugaRegula({ id: Date.now(), obiect: obiect, zonaId: zonaSelectata });
    
    alert(`Regula pentru "${obiect}" a fost creată cu succes!`);
    setObiect('');
    setZonaSelectata('');
  };

  return (
    <div style={{ padding: '20px', border: '2px solid #ccc', borderRadius: '8px', minWidth: '300px', backgroundColor: 'white' }}>
      <h2 style={{ marginTop: 0 }}>Editor de Reguli</h2>
      
      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Ce obiect urmărim?</label>
        <input 
          type="text" 
          value={obiect}
          onChange={(e) => setObiect(e.target.value)}
          placeholder="ex: cană, rucsac, persoană" 
          style={{ width: '100%', padding: '8px', boxSizing: 'border-box', border: '1px solid #aaa', borderRadius: '4px' }}
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>În ce zonă?</label>
        <select 
          value={zonaSelectata} 
          onChange={(e) => setZonaSelectata(e.target.value)}
          style={{ width: '100%', padding: '8px', boxSizing: 'border-box', border: '1px solid #aaa', borderRadius: '4px' }}
        >
          <option value="">-- Alege o zonă --</option>
          {/* Aici populăm meniul automat cu zonele desenate pe imagine */}
          {zoneDesenate.map((zona) => (
            <option key={zona.id} value={zona.id}>
              {zona.nume}
            </option>
          ))}
        </select>
      </div>

      <button 
        onClick={handleSalveazaRegula}
        style={{ width: '100%', padding: '10px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
      >
        Creează Regula
      </button>
    </div>
  );
}