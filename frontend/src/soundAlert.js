let audioCtx = null;

export async function redaAlarmaSonora() {
  try {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AudioContext();
    }

    // Așteptăm ca browserul să deblocheze redarea audio
    if (audioCtx.state === 'suspended') {
      await audioCtx.resume();
    }

    const acum = audioCtx.currentTime;

    // Generăm 2 bip-uri clare de alarmă
    [0, 0.25].forEach((delay) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(880, acum + delay);
      osc.frequency.setValueAtTime(660, acum + delay + 0.1);

      gain.gain.setValueAtTime(0.3, acum + delay);
      gain.gain.exponentialRampToValueAtTime(0.01, acum + delay + 0.2);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start(acum + delay);
      osc.stop(acum + delay + 0.21);
    });
  } catch (err) {
    console.error("Eroare la redarea alarmei sonore:", err);
  }
}