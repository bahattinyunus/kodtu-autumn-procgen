using System.Collections.Generic;
using UnityEngine;

namespace AutumnProcGen.Core
{
    public class AudioManager : MonoBehaviour
    {
        public static AudioManager Instance { get; private set; }

        [Header("Audio Sources")]
        public AudioSource musicSource;
        public AudioSource ambientSource;
        public AudioSource sfxSource;

        private readonly Dictionary<string, AudioClip> clipCache = new Dictionary<string, AudioClip>();

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;

            if (musicSource == null) musicSource = gameObject.AddComponent<AudioSource>();
            if (ambientSource == null) ambientSource = gameObject.AddComponent<AudioSource>();
            if (sfxSource == null) sfxSource = gameObject.AddComponent<AudioSource>();

            musicSource.loop = true;
            ambientSource.loop = true;
            sfxSource.playOnAwake = false;

            LoadAllAudioClips();
        }

        private void LoadAllAudioClips()
        {
            AudioClip[] loaded = Resources.LoadAll<AudioClip>("Audio");
            foreach (var clip in loaded)
            {
                clipCache[clip.name] = clip;
            }
        }

        public void RegisterClip(string name, AudioClip clip)
        {
            if (clip != null)
                clipCache[name] = clip;
        }

        public void PlayMusic(string name, float volume = 0.6f)
        {
            if (clipCache.TryGetValue(name, out AudioClip clip))
            {
                musicSource.clip = clip;
                musicSource.volume = volume;
                musicSource.Play();
            }
        }

        public void PlayAmbience(string name, float volume = 0.4f)
        {
            if (clipCache.TryGetValue(name, out AudioClip clip))
            {
                ambientSource.clip = clip;
                ambientSource.volume = volume;
                ambientSource.Play();
            }
        }

        public void PlaySFX(string name, float volume = 0.8f, float pitch = 1.0f)
        {
            if (clipCache.TryGetValue(name, out AudioClip clip))
            {
                sfxSource.pitch = pitch;
                sfxSource.PlayOneShot(clip, volume);
            }
        }

        public void PlayFootstep()
        {
            string[] steps = { "leaf_crunch_1", "leaf_crunch_2", "leaf_crunch_3" };
            string chosen = steps[Random.Range(0, steps.Length)];
            PlaySFX(chosen, 0.4f, Random.Range(0.9f, 1.1f));
        }

        public void PlaySlash()
        {
            PlaySFX("slash_ember", 0.7f, Random.Range(0.95f, 1.1f));
        }

        public void PlayHit()
        {
            PlaySFX("hit_hurt", 0.8f, Random.Range(0.9f, 1.05f));
        }

        public void PlayKitabeChime()
        {
            PlaySFX("kitabe_chime", 0.9f, 1.0f);
        }

        public void PlayHarvest()
        {
            PlaySFX("harvest_chime", 0.85f, 1.0f);
        }

        public void PlayVictory()
        {
            PlaySFX("bilim_chime", 1.0f, 1.0f);
        }
    }
}
