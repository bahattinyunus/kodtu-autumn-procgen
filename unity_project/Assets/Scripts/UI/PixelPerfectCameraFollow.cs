using UnityEngine;

namespace AutumnProcGen.UI
{
    public class PixelPerfectCameraFollow : MonoBehaviour
    {
        public Transform Target;
        public float SmoothSpeed = 8.0f;
        public float PixelsPerUnit = 16.0f;

        private float shakeDuration = 0.0f;
        private float shakeMagnitude = 0.15f;

        private void LateUpdate()
        {
            if (Target == null)
            {
                var p = FindFirstObjectByType<Entities.PlayerController>();
                if (p != null) Target = p.transform;
                return;
            }

            Vector3 targetPos = new Vector3(Target.position.x, Target.position.y, -10.0f);

            if (shakeDuration > 0.0f)
            {
                targetPos += (Vector3)(Random.insideUnitCircle * shakeMagnitude);
                shakeDuration -= Time.deltaTime;
            }

            Vector3 smoothed = Vector3.Lerp(transform.position, targetPos, SmoothSpeed * Time.deltaTime);

            // Pixel snap to avoid sub-pixel jitter
            if (PixelsPerUnit > 0)
            {
                smoothed.x = Mathf.Round(smoothed.x * PixelsPerUnit) / PixelsPerUnit;
                smoothed.y = Mathf.Round(smoothed.y * PixelsPerUnit) / PixelsPerUnit;
            }

            transform.position = smoothed;
        }

        public void TriggerShake(float duration = 0.2f, float magnitude = 0.2f)
        {
            shakeDuration = duration;
            shakeMagnitude = magnitude;
        }
    }
}
