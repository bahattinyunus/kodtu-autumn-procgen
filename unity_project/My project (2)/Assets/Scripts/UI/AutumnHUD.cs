using System.Collections;
using AutumnProcGen.Core;
using AutumnProcGen.Entities;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace AutumnProcGen.UI
{
    public class AutumnHUD : MonoBehaviour
    {
        [Header("Bars")]
        public Image HealthBarFill;
        public Image HeatBarFill;
        public Image StaminaBarFill;

        [Header("Texts")]
        public Text ObjectiveText;
        public Text PromptText;
        public Text SeedCodeText;

        [Header("Kitabe Dialog Modal")]
        public GameObject DialogPanel;
        public Text DialogTitleText;
        public Text DialogBodyText;

        [Header("End Screens")]
        public GameObject VictoryPanel;
        public GameObject GameOverPanel;

        private PlayerController player;
        private Coroutine typewriterRoutine;

        private void Start()
        {
            player = FindFirstObjectByType<PlayerController>();
            if (player != null)
            {
                player.OnHealthChanged += UpdateHealth;
                player.OnHeatChanged += UpdateHeat;
                player.OnStaminaChanged += UpdateStamina;
                player.OnInteractPromptAvailable += ShowPrompt;
                player.OnInteractPromptLost += HidePrompt;
                player.OnPlayerDied += ShowGameOver;
                player.OnVictoryReached += ShowVictory;
            }

            if (DialogPanel != null) DialogPanel.SetActive(false);
            if (VictoryPanel != null) VictoryPanel.SetActive(false);
            if (GameOverPanel != null) GameOverPanel.SetActive(false);
            if (PromptText != null) PromptText.text = "";
        }

        private void OnDestroy()
        {
            if (player != null)
            {
                player.OnHealthChanged -= UpdateHealth;
                player.OnHeatChanged -= UpdateHeat;
                player.OnStaminaChanged -= UpdateStamina;
                player.OnInteractPromptAvailable -= ShowPrompt;
                player.OnInteractPromptLost -= HidePrompt;
                player.OnPlayerDied -= ShowGameOver;
                player.OnVictoryReached -= ShowVictory;
            }
        }

        private void Update()
        {
            // Close dialog modal with E or Escape
            if (DialogPanel != null && DialogPanel.activeSelf)
            {
                if (Input.GetKeyDown(KeyCode.E) || Input.GetKeyDown(KeyCode.Escape))
                {
                    DialogPanel.SetActive(false);
                }
            }
        }

        public void SetSeedCode(string code)
        {
            if (SeedCodeText != null)
                SeedCodeText.text = $"TOHUM: {code}";
        }

        private void UpdateHealth(int current, int max)
        {
            if (HealthBarFill != null)
                HealthBarFill.fillAmount = (float)current / max;
        }

        private void UpdateHeat(float current, float max)
        {
            if (HeatBarFill != null)
                HeatBarFill.fillAmount = current / max;
        }

        private void UpdateStamina(float current, float max)
        {
            if (StaminaBarFill != null)
                StaminaBarFill.fillAmount = current / max;
        }

        private void ShowPrompt(InteractiveObject io)
        {
            if (PromptText != null)
            {
                PromptText.text = io.PromptText;
                PromptText.gameObject.SetActive(true);
            }

            if (io.Type == InteractableType.Kitabe)
            {
                ShowKitabeDialog(io.InscriptionIndex);
            }
        }

        private void HidePrompt()
        {
            if (PromptText != null)
            {
                PromptText.text = "";
                PromptText.gameObject.SetActive(false);
            }
        }

        public void ShowKitabeDialog(int inscriptionIndex)
        {
            if (DialogPanel == null) return;

            int idx = Mathf.Clamp(inscriptionIndex, 0, StoryData.Inscriptions.Length - 1);
            var data = StoryData.Inscriptions[idx];

            DialogPanel.SetActive(true);
            if (DialogTitleText != null) DialogTitleText.text = data.Title;

            if (typewriterRoutine != null) StopCoroutine(typewriterRoutine);
            typewriterRoutine = StartCoroutine(TypewriterRoutine(data.Content));
        }

        private IEnumerator TypewriterRoutine(string fullText)
        {
            if (DialogBodyText == null) yield break;

            DialogBodyText.text = "";
            for (int i = 0; i < fullText.Length; i++)
            {
                DialogBodyText.text += fullText[i];
                if (i % 2 == 0)
                {
                    AudioManager.Instance?.PlaySFX("dialogue_blip", 0.15f, 1.2f);
                }
                yield return new WaitForSeconds(0.015f);
            }
        }

        private void ShowVictory()
        {
            if (VictoryPanel != null) VictoryPanel.SetActive(true);
        }

        private void ShowGameOver()
        {
            if (GameOverPanel != null) GameOverPanel.SetActive(true);
        }

        public void RestartGame()
        {
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
        }
    }
}
