/**
 * Kitchen KDS Audio Alert Engine
 * Uses Web Audio API for 100% reliable, zero-asset synthesized siren chimes.
 */
class KitchenAudioAlert {
  constructor() {
    this.audioCtx = null;
    this.isPlaying = false;
    this.intervalId = null;
    this.volume = 0.8;
    this.isMuted = false;
  }

  init() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  playChime() {
    if (this.isMuted) return;
    this.init();
    if (!this.audioCtx) return;

    try {
      const now = this.audioCtx.currentTime;

      // Tone 1: 880Hz (A5)
      const osc1 = this.audioCtx.createOscillator();
      const gain1 = this.audioCtx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(880, now);
      osc1.frequency.exponentialRampToValueAtTime(1174.66, now + 0.15); // Slide up to D6
      gain1.gain.setValueAtTime(this.volume * 0.5, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

      osc1.connect(gain1);
      gain1.connect(this.audioCtx.destination);
      osc1.start(now);
      osc1.stop(now + 0.3);

      // Tone 2: 1318.51Hz (E6) high alert ding
      const osc2 = this.audioCtx.createOscillator();
      const gain2 = this.audioCtx.createGain();
      osc2.type = 'triangle';
      osc2.frequency.setValueAtTime(1318.51, now + 0.18);
      gain2.gain.setValueAtTime(this.volume * 0.7, now + 0.18);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.55);

      osc2.connect(gain2);
      gain2.connect(this.audioCtx.destination);
      osc2.start(now + 0.18);
      osc2.stop(now + 0.55);
    } catch (e) {
      console.warn("Audio chime playback error:", e);
    }
  }

  startLoop(intervalMs = 2500) {
    if (this.isPlaying) return;
    this.init();
    this.isPlaying = true;
    this.playChime();
    this.intervalId = setInterval(() => {
      this.playChime();
    }, intervalMs);
  }

  stopLoop() {
    this.isPlaying = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      this.stopLoop();
    }
    return this.isMuted;
  }
}

window.kitchenAudio = new KitchenAudioAlert();

