import React from 'react';
import VisionViewport from './components/VisionViewport';
import ControlPanel from './components/ControlPanel';
import EventLog from './components/EventLog';
import StatsDropdown from './components/StatsDropdown';

function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 font-sans">
      
      {/* Antetul (Header-ul) aplicației */}
      <header className="max-w-6xl mx-auto mb-8 pb-4 border-b border-slate-700 flex flex-wrap gap-4 justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-emerald-400">
            VIGILO <span className="text-slate-400 font-normal text-lg">| Monitorizare Inteligentă</span>
          </h1>
          <p className="text-sm text-slate-400">Definire zone de interes și reguli de detecție în timp real</p>
        </div>
        
        <div className="flex items-center gap-3">
          <StatsDropdown />
          <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs font-medium text-slate-300">Cameră Activă (Mod Test)</span>
          </div>
        </div>
      </header>

      {/* Conținutul principal */}
      <main className="max-w-6xl mx-auto flex flex-col lg:flex-row gap-8 justify-center items-start">
        <VisionViewport />
        
        <div className="w-full lg:w-96 flex flex-col gap-6 text-slate-900">
          <ControlPanel />
          <EventLog />
        </div>
      </main>

    </div>
  );
}

export default App;