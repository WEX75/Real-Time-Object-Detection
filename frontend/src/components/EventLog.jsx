import React from 'react';
import { useStore } from '../store';

export default function EventLog() {
  // Tragem regulile și zonele din seif
  const reguliActive = useStore((state) => state.reguliActive);
  const zoneDesenate = useStore((state) => state.zoneDesenate);

  // Funcție mică pentru a găsi numele zonei (ex: "Masa 3") folosind ID-ul ei
  const gasesteNumeZona = (idZona) => {
    const zona = zoneDesenate.find(z => z.id.toString() === idZona.toString());
    return zona ? zona.nume : 'Zonă necunoscută';
  };

  return (
    <div style={{ padding: '20px', border: '2px solid #ccc', borderRadius: '8px', minWidth: '300px', backgroundColor: 'white', marginTop: '20px' }}>
      <h2 style={{ marginTop: 0 }}>Reguli & Alerte</h2>
      
      {reguliActive.length === 0 ? (
        <p style={{ color: '#666', fontStyle: 'italic' }}>Nicio regulă creată încă.</p>
      ) : (
        <ul style={{ listStyleType: 'none', padding: 0 }}>
          {reguliActive.map((regula, index) => (
            <li key={index} style={{ padding: '10px', borderBottom: '1px solid #eee', marginBottom: '5px' }}>
              📡 Sistemul caută: <strong>{regula.obiect}</strong> în zona <strong>{gasesteNumeZona(regula.zonaId)}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}