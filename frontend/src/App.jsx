import React from 'react';
import VisionViewport from './components/VisionViewport';
import ControlPanel from './components/ControlPanel';
import EventLog from './components/EventLog'; // Importăm noul panou

function App() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6', padding: '30px', display: 'flex', gap: '30px', justifyContent: 'center', alignItems: 'flex-start' }}>
      
      {/* Stânga: Video și desen */}
      <VisionViewport />
      
      {/* Dreapta: Panoul de control deasupra, log-ul dedesubt */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <ControlPanel />
        <EventLog />
      </div>
      
    </div>
  );
}

export default App;