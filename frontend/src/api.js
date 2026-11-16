// Schimbă în false când backend-ul FastAPI al lui Duti rulează local
const USE_MOCK = true;
const API_BASE_URL = 'http://localhost:8000/api';

export const apiService = {
  // Trimite o zonă nouă către backend
  async salveazaZona(zona) {
    if (USE_MOCK) {
      // Simulăm o latență mică de rețea
      await new Promise((resolve) => setTimeout(resolve, 150));
      return { status: 'ok', data: zona };
    }

    const response = await fetch(`${API_BASE_URL}/zones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zona),
    });
    if (!response.ok) throw new Error('Eroare la salvarea zonei pe server');
    return response.json();
  },

  // Șterge o zonă de pe backend
  async stergeZona(idZona) {
    if (USE_MOCK) return { status: 'deleted', id: idZona };

    const response = await fetch(`${API_BASE_URL}/zones/${idZona}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Eroare la ștergerea zonei');
    return response.json();
  },

  // Trimite o regulă nouă către backend
  async salveazaRegula(regula) {
    if (USE_MOCK) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      return { status: 'ok', data: regula };
    }

    const response = await fetch(`${API_BASE_URL}/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(regula),
    });
    if (!response.ok) throw new Error('Eroare la salvarea regulii pe server');
    return response.json();
  },

  // Șterge o regulă de pe backend
  async stergeRegula(idRegula) {
    if (USE_MOCK) return { status: 'deleted', id: idRegula };

    const response = await fetch(`${API_BASE_URL}/rules/${idRegula}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Eroare la ștergerea regulii');
    return response.json();
  }
};