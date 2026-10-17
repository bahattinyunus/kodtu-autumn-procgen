using System;
using UnityEngine;

namespace AutumnProcGen.Entities
{
    public enum InteractableType
    {
        Campfire,
        Kitabe,
        BilimAgaci,
        Relic,
        Acorn,
        Companion
    }

    public class InteractiveObject : MonoBehaviour
    {
        [Header("Interaction Settings")]
        public InteractableType Type;
        public string PromptText = "[E] Etkileşime Geç";
        public float InteractRadius = 1.6f;
        public int InscriptionIndex = 0;

        public event Action<PlayerController, InteractiveObject> OnInteracted;

        public virtual void Interact(PlayerController player)
        {
            OnInteracted?.Invoke(player, this);
        }

        private void OnDrawGizmosSelected()
        {
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, InteractRadius);
        }
    }
}
