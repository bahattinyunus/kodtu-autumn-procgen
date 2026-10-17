"""
Procedural Audio Synthesizer & Pitch-Shifted SFX Engine.

Generates authentic 16-bit retro `.wav` sound effects for:
- Crisp autumn leaf footsteps (granular noise bursts + band-pass envelope + pitch-shifting)
- Damp mud footsteps
- Solar Ember lantern sweep
- Harvest Relic chime (warm pentatonic autumn chord)
- Shrine portal awakening
- Melancholic autumn wind ambience
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
import wave
import numpy as np
import pygame

SAMPLE_RATE = 22050


def _save_wav_int16(filepath: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Saves a normalized float [-1.0, 1.0] array as a 16-bit mono PCM WAV file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())


def synth_leaf_crunch(seed_offset: int = 0, pitch_factor: float = 1.0) -> np.ndarray:
    """
    Synthesizes a crunchy dry autumn leaf rustle/footstep using micro-granular crackle
    impulses modulated by a crisp high-frequency envelope.
    """
    rng = np.random.default_rng(1042 + seed_offset)
    duration = int(SAMPLE_RATE * (0.14 / pitch_factor))
    t = np.linspace(0.0, 1.0, duration, endpoint=False)

    # White noise with sharp crackle spikes
    noise = rng.normal(0.0, 1.0, duration)
    crackle_mask = (rng.random(duration) > 0.72).astype(np.float64)
    burstEnv = np.sin(t * np.pi) * np.exp(-t * 5.5)
    sub_bursts = 0.5 + 0.5 * np.sin(2.0 * np.pi * (18.0 + seed_offset * 3.0) * t)

    # Differentiate to emphasize high-frequency dry leaf snap
    diff_noise = np.diff(noise, prepend=noise[0])
    signal = (diff_noise * 0.65 + noise * crackle_mask * 0.85) * burstEnv * sub_bursts
    return signal * 0.42


def synth_mud_step() -> np.ndarray:
    """Synthesizes a soft, damp soil footstep for high-moisture biomes."""
    rng = np.random.default_rng(2026)
    duration = int(SAMPLE_RATE * 0.11)
    t = np.linspace(0.0, 0.11, duration, endpoint=False)
    env = np.exp(-t * 32.0)
    thump = np.sin(2.0 * np.pi * (140.0 * np.exp(-t * 14.0)) * t)
    squelch = np.convolve(rng.normal(0.0, 0.3, duration), np.ones(8) / 8.0, mode="same")
    return (thump * 0.6 + squelch * 0.4) * env * 0.38


def synth_ember_sweep() -> np.ndarray:
    """Synthesizes a warm golden lantern flame sweep + wind whoosh."""
    rng = np.random.default_rng(3099)
    duration = int(SAMPLE_RATE * 0.22)
    t = np.linspace(0.0, 0.22, duration, endpoint=False)
    env = np.sin(np.pi * (t / 0.22)) * np.exp(-t * 6.0)
    freq_sweep = np.linspace(380.0, 190.0, duration)
    tone = np.sin(2.0 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE)
    whoosh = np.convolve(rng.normal(0.0, 0.6, duration), np.ones(5) / 5.0, mode="same")
    return (tone * 0.45 + whoosh * 0.55) * env * 0.45


def synth_harvest_chime() -> np.ndarray:
    """Synthesizes a crystalline autumn arpeggio (D minor / Dorian fifth + ninth)."""
    duration = int(SAMPLE_RATE * 0.48)
    t = np.linspace(0.0, 0.48, duration, endpoint=False)
    freqs = [587.33, 880.0, 1174.66, 1318.51]  # D5, A5, D6, E6
    signal = np.zeros(duration, dtype=np.float64)
    for i, f in enumerate(freqs):
        start_t = i * 0.055
        mask = t >= start_t
        local_t = np.maximum(0.0, t - start_t)
        env = mask * np.exp(-local_t * 7.5)
        signal += (np.sin(2.0 * np.pi * f * local_t) + 0.3 * np.sin(4.0 * np.pi * f * local_t)) * env
    return signal * 0.22


def synth_portal_activate() -> np.ndarray:
    """Synthesizes a deep resonant shrine awakening chord."""
    duration = int(SAMPLE_RATE * 0.85)
    t = np.linspace(0.0, 0.85, duration, endpoint=False)
    env = np.sin(np.pi * np.minimum(1.0, t / 0.85)) * np.exp(-t * 1.8)
    chord = (
        np.sin(2.0 * np.pi * 220.0 * t)
        + 0.7 * np.sin(2.0 * np.pi * 329.63 * t)
        + 0.5 * np.sin(2.0 * np.pi * 440.0 * t)
        + 0.4 * np.sin(2.0 * np.pi * 659.25 * (t + 0.02 * np.sin(12.0 * t)))
    )
    return chord * env * 0.20


def synth_hit_hurt() -> np.ndarray:
    """Synthesizes a crisp 16-bit impact sound."""
    rng = np.random.default_rng(77)
    duration = int(SAMPLE_RATE * 0.16)
    t = np.linspace(0.0, 0.16, duration, endpoint=False)
    env = np.exp(-t * 22.0)
    drop = np.sin(2.0 * np.pi * (240.0 * np.exp(-t * 18.0)) * t)
    noise = rng.uniform(-0.6, 0.6, duration)
    return (drop * 0.7 + noise * 0.3) * env * 0.45


def synth_wind_ambience() -> np.ndarray:
    """Synthesizes a seamless 4-second melancholic autumn breeze + distant chime loop."""
    rng = np.random.default_rng(8492)
    duration = int(SAMPLE_RATE * 4.0)
    t = np.linspace(0.0, 4.0, duration, endpoint=False)
    raw = rng.normal(0.0, 0.25, duration)
    # Moving-average low-pass filter to create soft wind murmur
    kernel = np.hanning(64)
    kernel /= kernel.sum()
    wind = np.convolve(raw, kernel, mode="same")
    mod = 0.55 + 0.45 * np.sin(2.0 * np.pi * 0.25 * t)
    drone = 0.06 * np.sin(2.0 * np.pi * 146.83 * t) + 0.04 * np.sin(2.0 * np.pi * 220.0 * t)
    fade = np.ones(duration, dtype=np.float64)
    fade_len = int(SAMPLE_RATE * 0.25)
    fade[:fade_len] = np.linspace(0.0, 1.0, fade_len)
    fade[-fade_len:] = np.linspace(1.0, 0.0, fade_len)
    return (wind * mod + drone) * fade * 0.35


def synth_dialogue_blip() -> np.ndarray:
    """Synthesizes an authentic retro dialogue text blip for the typewriter effect."""
    rng = np.random.default_rng(42)
    duration = int(SAMPLE_RATE * 0.04)
    t = np.linspace(0.0, 0.04, duration, endpoint=False)
    env = np.sin(np.pi * (t / 0.04)) * np.exp(-t * 40.0)
    freq = 520.0 + rng.uniform(-40.0, 40.0)
    tone = np.sin(2.0 * np.pi * freq * t) + 0.3 * np.sin(4.0 * np.pi * freq * t)
    return tone * env * 0.18


def synth_deflect_clash() -> np.ndarray:
    """Synthesizes a sharp metallic/crystalline parry clash sound (Enter the Gungeon / Sekiro style)."""
    duration = int(SAMPLE_RATE * 0.28)
    t = np.linspace(0.0, 0.28, duration, endpoint=False)
    env = np.exp(-t * 18.0)
    f1, f2, f3 = 1480.0, 2217.0, 3322.0
    ring = (
        np.sin(2.0 * np.pi * f1 * t)
        + 0.7 * np.sin(2.0 * np.pi * f2 * t)
        + 0.5 * np.sin(2.0 * np.pi * f3 * t)
    )
    spark = np.random.default_rng(999).normal(0.0, 0.5, duration) * np.exp(-t * 65.0)
    return (ring * 0.65 + spark * 0.35) * env * 0.40


def synth_level_up() -> np.ndarray:
    """Synthesizes a triumphant golden autumn fanfare chord when unlocking ODTÜ boons."""
    duration = int(SAMPLE_RATE * 0.65)
    t = np.linspace(0.0, 0.65, duration, endpoint=False)
    notes = [440.0, 554.37, 659.25, 880.0]  # A Major chord: A4, C#5, E5, A5
    signal = np.zeros(duration, dtype=np.float64)
    for i, freq in enumerate(notes):
        st = i * 0.08
        mask = t >= st
        lt = np.maximum(0.0, t - st)
        env = mask * np.exp(-lt * 5.5) * np.sin(np.pi * np.minimum(1.0, lt / 0.1))
        signal += (np.sin(2.0 * np.pi * freq * lt) + 0.25 * np.sin(4.0 * np.pi * freq * lt)) * env
    return signal * 0.26


def synth_kitabe_chime() -> np.ndarray:
    """Synthesizes a mystical metallic Hitit rune chime for historical ODTÜ steles."""
    duration = int(SAMPLE_RATE * 0.75)
    t = np.linspace(0.0, 0.75, duration, endpoint=False)
    env = np.exp(-t * 4.2)
    bell = (
        np.sin(2.0 * np.pi * 528.0 * t)
        + 0.65 * np.sin(2.0 * np.pi * 792.0 * t)
        + 0.40 * np.sin(2.0 * np.pi * 1056.0 * t)
        + 0.25 * np.sin(2.0 * np.pi * 1584.0 * t)
        + 0.15 * np.sin(2.0 * np.pi * 2112.0 * t)
    )
    shimmer = 0.5 + 0.5 * np.sin(2.0 * np.pi * 6.0 * t)
    return (bell * shimmer) * env * 0.28


def synth_water_splash() -> np.ndarray:
    """Synthesizes a soft liquid splash / droplet ripple for Eymir wetlands and boardwalks."""
    rng = np.random.default_rng(505)
    duration = int(SAMPLE_RATE * 0.14)
    t = np.linspace(0.0, 0.14, duration, endpoint=False)
    env = np.sin(np.pi * np.minimum(1.0, t / 0.03)) * np.exp(-t * 26.0)
    sweep = np.linspace(620.0, 310.0, duration)
    drip = np.sin(2.0 * np.pi * np.cumsum(sweep) / SAMPLE_RATE)
    splash = np.convolve(rng.normal(0.0, 0.4, duration), np.ones(6) / 6.0, mode="same")
    return (drip * 0.55 + splash * 0.45) * env * 0.35


def synth_autumn_theme() -> np.ndarray:
    """
    Synthesizes an 8-second seamless looping 16-bit autumn soundtrack in D Dorian:
    - Warm analog sub-drone & cello bassline (D2 -> Bb1 -> C2 -> A1)
    - Melancholic chord swells with subtle tape vibrato
    - Gentle pentatonic harp / kalimba arpeggio (D4, F4, G4, A4, C5, D5)
    - Seamless crossfade boundary for artifact-free infinite loop.
    """
    duration = int(SAMPLE_RATE * 8.0)
    t = np.linspace(0.0, 8.0, duration, endpoint=False)
    music = np.zeros(duration, dtype=np.float64)

    # 4 Chords across 8 seconds (2.0s per chord)
    chords = [
        # D minor
        ([73.42, 146.83, 220.00, 293.66], [293.66, 349.23, 440.00, 523.25]),
        # Bb Major 7
        ([58.27, 116.54, 174.61, 220.00], [293.66, 349.23, 440.00, 587.33]),
        # C Major / E
        ([65.41, 130.81, 196.00, 261.63], [329.63, 392.00, 523.25, 659.25]),
        # A minor
        ([55.00, 110.00, 164.81, 220.00], [261.63, 329.63, 440.00, 523.25]),
    ]

    for ci, (bass_notes, arp_notes) in enumerate(chords):
        c_start = ci * 2.0
        c_end = c_start + 2.0
        mask = (t >= c_start) & (t < c_end)
        lt = t[mask] - c_start
        chord_env = np.sin(np.pi * (lt / 2.0)) ** 1.5

        # Bass drone & warm 2nd harmonic
        for bi, bn in enumerate(bass_notes):
            vibrato = 1.0 + 0.003 * np.sin(2.0 * np.pi * 4.5 * lt)
            drone = np.sin(2.0 * np.pi * bn * vibrato * lt)
            music[mask] += drone * chord_env * (0.16 / (bi + 1))

        # Arpeggiated melody notes
        for ai, an in enumerate(arp_notes):
            arp_t0 = ai * 0.45
            if arp_t0 < 2.0:
                sub_mask = (lt >= arp_t0)
                sub_t = lt[sub_mask] - arp_t0
                note_env = np.exp(-sub_t * 3.8) * np.sin(np.pi * np.minimum(1.0, sub_t / 0.02))
                music_idx = np.where(mask)[0][sub_mask]
                music[music_idx] += (
                    np.sin(2.0 * np.pi * an * sub_t)
                    + 0.3 * np.sin(4.0 * np.pi * an * sub_t)
                ) * note_env * 0.12

    # Equal-power crossfade over 0.35s to make loop perfectly seamless
    cf_len = int(SAMPLE_RATE * 0.35)
    cf_in = np.linspace(0.0, 1.0, cf_len)
    cf_out = 1.0 - cf_in
    blended = music.copy()
    blended[:cf_len] = music[:cf_len] * cf_in + music[-cf_len:] * cf_out
    blended[-cf_len:] = blended[:cf_len]

    return np.clip(blended * 0.48, -1.0, 1.0)


def synth_campfire_sizzle() -> np.ndarray:
    """Synthesizes sizzling embers and roasted chestnut pop at the campfire."""
    rng = np.random.default_rng(777)
    duration = int(SAMPLE_RATE * 0.38)
    t = np.linspace(0.0, 0.38, duration, endpoint=False)
    env = np.sin(np.pi * np.minimum(1.0, t / 0.04)) * np.exp(-t * 8.5)
    hiss = rng.normal(0.0, 0.35, duration) * np.exp(-t * 12.0)
    crackle = (rng.random(duration) > 0.88).astype(np.float64) * rng.normal(0.0, 0.6, duration)
    pop = np.sin(2.0 * np.pi * 320.0 * np.exp(-t * 24.0) * t) * np.exp(-t * 30.0)
    return (hiss * 0.45 + crackle * 0.35 + pop * 0.55) * env * 0.38


def synth_blade_dance() -> np.ndarray:
    """Synthesizes an omni-directional sonic flurry for the Bozkır Kılıç Dansı finisher."""
    duration = int(SAMPLE_RATE * 0.45)
    t = np.linspace(0.0, 0.45, duration, endpoint=False)
    env = np.sin(np.pi * (t / 0.45)) * np.exp(-t * 3.5)
    sweep1 = np.linspace(880.0, 220.0, duration)
    sweep2 = np.linspace(440.0, 110.0, duration)
    tone1 = np.sin(2.0 * np.pi * np.cumsum(sweep1) / SAMPLE_RATE)
    tone2 = np.sin(2.0 * np.pi * np.cumsum(sweep2) / SAMPLE_RATE)
    noise = np.random.default_rng(888).normal(0.0, 0.4, duration) * env
    return (tone1 * 0.4 + tone2 * 0.3 + noise * 0.3) * env * 0.45


def synth_boss_roar() -> np.ndarray:
    """Synthesizes a low-frequency guttural primal roar for the Enraged Warden phase transition."""
    rng = np.random.default_rng(999)
    duration = int(SAMPLE_RATE * 0.85)
    t = np.linspace(0.0, 0.85, duration, endpoint=False)
    env = np.sin(np.pi * np.minimum(1.0, t / 0.12)) * np.exp(-t * 2.8)
    sweep = np.linspace(95.0, 48.0, duration)
    growl = np.sin(2.0 * np.pi * np.cumsum(sweep) / SAMPLE_RATE)
    sub = np.sin(2.0 * np.pi * 38.0 * t)
    noise = rng.normal(0.0, 0.45, duration) * np.exp(-t * 4.0)
    return (growl * 0.5 + sub * 0.35 + noise * 0.25) * env * 0.55


def synth_parry_spark() -> np.ndarray:
    """Synthesizes an ultra-crisp golden parry/clash spark for perfect frame deflections."""
    duration = int(SAMPLE_RATE * 0.22)
    t = np.linspace(0.0, 0.22, duration, endpoint=False)
    env = np.exp(-t * 18.0)
    spark1 = np.sin(2.0 * np.pi * 1760.0 * t)
    spark2 = np.sin(2.0 * np.pi * 2640.0 * t)
    ping = np.sin(2.0 * np.pi * 3520.0 * np.exp(-t * 12.0) * t)
    return (spark1 * 0.4 + spark2 * 0.3 + ping * 0.4) * env * 0.42


def synth_devrim_overdrive() -> np.ndarray:
    """
    Synthesizes a resonant, cinematic brass horn and fiery harmonic crescendo
    when unleashing ODTÜ Devrim Overdrive Mode.
    """
    duration = int(SAMPLE_RATE * 1.25)
    t = np.linspace(0.0, 1.25, duration, endpoint=False)
    # Pitch sweep from D3 (146.8 Hz) up to A4 (440 Hz) and D5 (587.3 Hz)
    f0 = 146.83 + (440.0 - 146.83) * (t / 1.25) ** 1.8
    phase = 2.0 * np.pi * np.cumsum(f0) / SAMPLE_RATE

    # Rich harmonic spectrum (horn/brass synthesis with odd & even partials)
    h1 = np.sin(phase)
    h2 = 0.60 * np.sin(2.0 * phase)
    h3 = 0.35 * np.sin(3.0 * phase)
    h4 = 0.20 * np.sin(4.0 * phase)

    # Sub-bass rumble
    sub = 0.40 * np.sin(2.0 * np.pi * 73.41 * t)

    # Shimmering golden chorused sparkle
    sparkle = 0.15 * np.sin(2.0 * np.pi * 880.0 * (1.0 + 0.05 * np.sin(2.0 * np.pi * 7.0 * t)) * t)

    env = np.minimum(t / 0.12, 1.0) * np.exp(-t * 1.8)
    wave = (h1 + h2 + h3 + h4 + sub + sparkle) * env * 0.58
    return wave


def synth_alchemy_chime() -> np.ndarray:
    """
    Synthesizes a crystalline pentatonic transmutation chime [D5, F#5, A5, D6, F#6]
    for Bozkır Simya Ocağı (Acorn Transmutation Crucible).
    """
    duration = int(SAMPLE_RATE * 0.65)
    wave = np.zeros(duration, dtype=np.float32)
    pitches = [587.33, 739.99, 880.00, 1174.66, 1479.98]
    for idx, f in enumerate(pitches):
        start_offset = int(idx * 0.075 * SAMPLE_RATE)
        sub_len = duration - start_offset
        if sub_len <= 0:
            continue
        t_sub = np.linspace(0.0, sub_len / SAMPLE_RATE, sub_len, endpoint=False)
        env = np.exp(-t_sub * 7.5)
        chime = (np.sin(2.0 * np.pi * f * t_sub) + 0.35 * np.sin(2.0 * np.pi * 2.0 * f * t_sub)) * env
        wave[start_offset:] += chime * 0.18
    return wave


def synth_raven_screech() -> np.ndarray:
    """
    Synthesizes a predatory avian screech for Bozkır Kuzgunu (Steppe Raven)
    using frequency-modulated harmonic overtones and rapid pitch decay.
    """
    duration = int(SAMPLE_RATE * 0.42)
    t = np.linspace(0.0, 0.42, duration, endpoint=False)
    # Pitch descent from 2200 Hz down to 880 Hz
    f0 = 2200.0 * np.exp(-t * 3.2)
    fm = 40.0 * np.sin(2.0 * np.pi * 35.0 * t)
    phase = 2.0 * np.pi * np.cumsum(f0 + fm) / SAMPLE_RATE
    carrier = np.sin(phase) + 0.5 * np.sin(2.0 * phase) + 0.25 * np.sin(3.0 * phase)
    noise = np.random.uniform(-0.15, 0.15, duration)
    env = np.sin(np.pi * (t / 0.42)) ** 0.8
    wave = (carrier + noise) * env * 0.38
    return wave


def synth_spring_splash() -> np.ndarray:
    """
    Synthesizes a bubbling subterranean mineral water droplet surge
    for Eymir Şifa Pınarı (Sacred Healing Springs).
    """
    duration = int(SAMPLE_RATE * 0.55)
    wave = np.zeros(duration, dtype=np.float32)
    # Staggered bubbling droplets
    bubble_freqs = [440.0, 523.25, 659.25, 880.0, 1046.50]
    for idx, f in enumerate(bubble_freqs):
        offset = int(idx * 0.08 * SAMPLE_RATE)
        sub_len = duration - offset
        if sub_len <= 0:
            continue
        t_sub = np.linspace(0.0, sub_len / SAMPLE_RATE, sub_len, endpoint=False)
        # Upward chirping bubble pitch
        f_chirp = f * (1.0 + 1.2 * (t_sub * 4.0))
        phase = 2.0 * np.pi * np.cumsum(f_chirp) / SAMPLE_RATE
        env = np.exp(-t_sub * 16.0)
        bubble = np.sin(phase) * env
        wave[offset:] += bubble * 0.22
    return wave


def synth_bilim_chime() -> np.ndarray:
    """
    Synthesizes a deep, resonant celestial tubular bell chord (D4, A4, F#5, A5)
    for the ODTÜ Bilim Ağacı Anıtı Activation Ceremony.
    """
    duration = int(SAMPLE_RATE * 1.4)
    wave = np.zeros(duration, dtype=np.float32)
    pitches = [293.66, 440.0, 739.99, 880.0]
    for idx, f in enumerate(pitches):
        offset = int(idx * 0.04 * SAMPLE_RATE)
        sub_len = duration - offset
        if sub_len <= 0:
            continue
        t_sub = np.linspace(0.0, sub_len / SAMPLE_RATE, sub_len, endpoint=False)
        env = np.exp(-t_sub * 4.2)
        harmonic = (
            np.sin(2.0 * np.pi * f * t_sub)
            + 0.45 * np.sin(2.0 * np.pi * 2.0 * f * t_sub)
            + 0.20 * np.sin(2.0 * np.pi * 3.0 * f * t_sub)
        ) * env
        wave[offset:] += harmonic * 0.24
    return wave


def synth_distant_thunder() -> np.ndarray:
    """
    Synthesizes a low-frequency rolling sub-bass thunder rumble
    resonating across the autumn steppe over Lake Eymir.
    """
    duration = int(SAMPLE_RATE * 1.6)
    t = np.linspace(0.0, 1.6, duration, endpoint=False)
    # Filtered low noise + rolling sub-bass wave
    f_sub = 55.0 + 15.0 * np.sin(2.0 * np.pi * 3.5 * t)
    sub = np.sin(2.0 * np.pi * f_sub * t) * np.exp(-t * 1.5)
    noise = np.random.uniform(-0.35, 0.35, duration)
    # Low-pass rolling envelope
    roll = (np.sin(np.pi * (t / 1.6)) ** 1.5) * np.exp(-t * 0.8)
    wave = (sub * 0.65 + noise * 0.35) * roll * 0.50
    return wave


def ensure_audio_assets(audio_dir: Path) -> Dict[str, Path]:
    """Generates and saves all `.wav` audio files into `assets/audio/` if not already present."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    files: Dict[str, Path] = {
        "leaf_crunch_1": audio_dir / "leaf_crunch_1.wav",
        "leaf_crunch_2": audio_dir / "leaf_crunch_2.wav",
        "leaf_crunch_3": audio_dir / "leaf_crunch_3.wav",
        "mud_step": audio_dir / "mud_step.wav",
        "water_splash": audio_dir / "water_splash.wav",
        "slash_ember": audio_dir / "slash_ember.wav",
        "harvest_chime": audio_dir / "harvest_chime.wav",
        "portal_activate": audio_dir / "portal_activate.wav",
        "kitabe_chime": audio_dir / "kitabe_chime.wav",
        "hit_hurt": audio_dir / "hit_hurt.wav",
        "wind_ambience": audio_dir / "wind_ambience.wav",
        "autumn_theme": audio_dir / "autumn_theme.wav",
        "campfire_sizzle": audio_dir / "campfire_sizzle.wav",
        "blade_dance": audio_dir / "blade_dance.wav",
        "boss_roar": audio_dir / "boss_roar.wav",
        "parry_spark": audio_dir / "parry_spark.wav",
        "dialogue_blip": audio_dir / "dialogue_blip.wav",
        "deflect_clash": audio_dir / "deflect_clash.wav",
        "level_up": audio_dir / "level_up.wav",
        "devrim_overdrive": audio_dir / "devrim_overdrive.wav",
        "alchemy_chime": audio_dir / "alchemy_chime.wav",
        "raven_screech": audio_dir / "raven_screech.wav",
        "spring_splash": audio_dir / "spring_splash.wav",
        "bilim_chime": audio_dir / "bilim_chime.wav",
        "distant_thunder": audio_dir / "distant_thunder.wav",
    }

    if not files["leaf_crunch_1"].exists():
        _save_wav_int16(files["leaf_crunch_1"], synth_leaf_crunch(0, 0.92))
    if not files["leaf_crunch_2"].exists():
        _save_wav_int16(files["leaf_crunch_2"], synth_leaf_crunch(1, 1.02))
    if not files["leaf_crunch_3"].exists():
        _save_wav_int16(files["leaf_crunch_3"], synth_leaf_crunch(2, 1.14))
    if not files["mud_step"].exists():
        _save_wav_int16(files["mud_step"], synth_mud_step())
    if not files["water_splash"].exists():
        _save_wav_int16(files["water_splash"], synth_water_splash())
    if not files["slash_ember"].exists():
        _save_wav_int16(files["slash_ember"], synth_ember_sweep())
    if not files["harvest_chime"].exists():
        _save_wav_int16(files["harvest_chime"], synth_harvest_chime())
    if not files["portal_activate"].exists():
        _save_wav_int16(files["portal_activate"], synth_portal_activate())
    if not files["kitabe_chime"].exists():
        _save_wav_int16(files["kitabe_chime"], synth_kitabe_chime())
    if not files["autumn_theme"].exists():
        _save_wav_int16(files["autumn_theme"], synth_autumn_theme())
    if not files["campfire_sizzle"].exists():
        _save_wav_int16(files["campfire_sizzle"], synth_campfire_sizzle())
    if not files["blade_dance"].exists():
        _save_wav_int16(files["blade_dance"], synth_blade_dance())
    if not files["boss_roar"].exists():
        _save_wav_int16(files["boss_roar"], synth_boss_roar())
    if not files["parry_spark"].exists():
        _save_wav_int16(files["parry_spark"], synth_parry_spark())
    if not files["hit_hurt"].exists():
        _save_wav_int16(files["hit_hurt"], synth_hit_hurt())
    if not files["wind_ambience"].exists():
        _save_wav_int16(files["wind_ambience"], synth_wind_ambience())
    if not files["dialogue_blip"].exists():
        _save_wav_int16(files["dialogue_blip"], synth_dialogue_blip())
    if not files["deflect_clash"].exists():
        _save_wav_int16(files["deflect_clash"], synth_deflect_clash())
    if not files["level_up"].exists():
        _save_wav_int16(files["level_up"], synth_level_up())
    if not files["devrim_overdrive"].exists():
        _save_wav_int16(files["devrim_overdrive"], synth_devrim_overdrive())
    if not files["alchemy_chime"].exists():
        _save_wav_int16(files["alchemy_chime"], synth_alchemy_chime())
    if not files["raven_screech"].exists():
        _save_wav_int16(files["raven_screech"], synth_raven_screech())
    if not files["spring_splash"].exists():
        _save_wav_int16(files["spring_splash"], synth_spring_splash())
    if not files["bilim_chime"].exists():
        _save_wav_int16(files["bilim_chime"], synth_bilim_chime())
    if not files["distant_thunder"].exists():
        _save_wav_int16(files["distant_thunder"], synth_distant_thunder())

    return files


class SoundEngine:
    """
    Runtime audio manager supporting procedural pitch-shifted leaf rustling
    and graceful fallback in headless test environments.
    """

    def __init__(self, audio_dir: Path, enabled: bool = True) -> None:
        self.enabled = enabled
        self.muted = False
        self.master_volume = 1.0
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.leaf_variants: List[pygame.mixer.Sound] = []
        self._step_counter = 0

        files = ensure_audio_assets(audio_dir)
        if not self.enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            for name, path in files.items():
                self.sounds[name] = pygame.mixer.Sound(str(path))
            self.leaf_variants = [
                self.sounds["leaf_crunch_1"],
                self.sounds["leaf_crunch_2"],
                self.sounds["leaf_crunch_3"],
            ]
        except Exception:
            self.enabled = False

    def toggle_mute(self) -> bool:
        """Toggles audio mute state. Returns True if now muted."""
        self.muted = not self.muted
        target_vol = 0.0 if self.muted else self.master_volume
        if self.enabled:
            for name, snd in self.sounds.items():
                try:
                    if name == "autumn_theme":
                        snd.set_volume(0.65 * target_vol)
                    elif name == "wind_ambience":
                        snd.set_volume(0.40 * target_vol)
                    else:
                        snd.set_volume(target_vol)
                except Exception:
                    pass
        return self.muted

    def set_master_volume(self, volume: float) -> None:
        """Sets master volume between 0.0 and 1.0."""
        self.master_volume = max(0.0, min(1.0, volume))
        if not self.muted and self.enabled:
            for name, snd in self.sounds.items():
                try:
                    if name == "autumn_theme":
                        snd.set_volume(0.65 * self.master_volume)
                    elif name == "wind_ambience":
                        snd.set_volume(0.40 * self.master_volume)
                    else:
                        snd.set_volume(self.master_volume)
                except Exception:
                    pass

    def play_leaf_crunch(self) -> None:
        if not self.enabled or self.muted or not self.leaf_variants:
            return
        snd = self.leaf_variants[self._step_counter % len(self.leaf_variants)]
        self._step_counter += 1
        snd.play()

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        snd: Optional[pygame.mixer.Sound] = self.sounds.get(name)
        if snd is not None:
            snd.play()

    def start_ambience(self) -> None:
        if not self.enabled:
            return
        amb = self.sounds.get("wind_ambience")
        if amb is not None:
            amb.play(loops=-1)

    def start_music(self) -> None:
        """Starts the seamless procedural autumn musical soundtrack on loop."""
        if not self.enabled:
            return
        theme = self.sounds.get("autumn_theme")
        if theme is not None:
            theme.set_volume(0.65)
            theme.play(loops=-1)
