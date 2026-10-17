using System;
using System.Collections.Generic;
using AutumnProcGen.Core;
using UnityEngine;

namespace AutumnProcGen.Entities
{
    [RequireComponent(typeof(Rigidbody2D))]
    [RequireComponent(typeof(Collider2D))]
    public class PlayerController : MonoBehaviour
    {
        [Header("Movement & Stamina")]
        public float WalkSpeed = 3.5f;
        public float RunSpeed = 5.5f;
        public float MaxStamina = 100.0f;
        public float CurrentStamina = 100.0f;
        public float StaminaDrainRate = 25.0f;
        public float StaminaRecoverRate = 20.0f;

        [Header("Health & Lantern Heat")]
        public int MaxHealth = 100;
        public int CurrentHealth = 100;
        public float MaxLanternHeat = 100.0f;
        public float CurrentLanternHeat = 100.0f;
        public float HeatDecayRate = 1.8f; // Heat lost per second in the chill

        [Header("Combat")]
        public GameObject ProjectilePrefab;
        public float AttackCooldown = 0.35f;
        private float lastAttackTime = -10.0f;

        [Header("Sprites & Visuals")]
        public SpriteRenderer SpriteRenderer;
        public Sprite[] WalkFrames; // 3 frames

        [Header("Inventory / Objectives")]
        public int RelicsCollected = 0;
        public int AcornsCollected = 0;
        public int ReadKitabeCount = 0;

        private Rigidbody2D rb;
        private Vector2 moveInput;
        private Vector2 lastFacingDirection = Vector2.right;
        private float walkAnimTimer = 0.0f;
        private int currentFrame = 0;
        private float footstepTimer = 0.0f;
        private float frostDamageTimer = 0.0f;

        public event Action<InteractiveObject> OnInteractPromptAvailable;
        public event Action OnInteractPromptLost;
        public event Action<int, int> OnHealthChanged;
        public event Action<float, float> OnHeatChanged;
        public event Action<float, float> OnStaminaChanged;
        public event Action OnPlayerDied;
        public event Action OnVictoryReached;

        private InteractiveObject nearestInteractable;

        private void Awake()
        {
            rb = GetComponent<Rigidbody2D>();
            rb.gravityScale = 0;
            rb.freezeRotation = true;
            if (SpriteRenderer == null) SpriteRenderer = GetComponent<SpriteRenderer>();
        }

        private void Start()
        {
            CurrentHealth = MaxHealth;
            CurrentLanternHeat = MaxLanternHeat;
            CurrentStamina = MaxStamina;
            OnHealthChanged?.Invoke(CurrentHealth, MaxHealth);
            OnHeatChanged?.Invoke(CurrentLanternHeat, MaxLanternHeat);
            OnStaminaChanged?.Invoke(CurrentStamina, MaxStamina);
        }

        private void Update()
        {
            HandleInput();
            HandleLanternHeatAndChill();
            UpdateAnimation();
            DetectInteractables();
        }

        private void FixedUpdate()
        {
            bool isSprinting = Input.GetKey(KeyCode.LeftShift) && moveInput.sqrMagnitude > 0.01f && CurrentStamina > 5.0f;
            float speed = isSprinting ? RunSpeed : WalkSpeed;

            if (isSprinting)
            {
                CurrentStamina = Mathf.Max(0.0f, CurrentStamina - StaminaDrainRate * Time.fixedDeltaTime);
            }
            else
            {
                CurrentStamina = Mathf.Min(MaxStamina, CurrentStamina + StaminaRecoverRate * Time.fixedDeltaTime);
            }
            OnStaminaChanged?.Invoke(CurrentStamina, MaxStamina);

            rb.linearVelocity = moveInput * speed;

            if (moveInput.sqrMagnitude > 0.01f)
            {
                footstepTimer += Time.fixedDeltaTime;
                float stepInterval = isSprinting ? 0.28f : 0.42f;
                if (footstepTimer >= stepInterval)
                {
                    footstepTimer = 0.0f;
                    AudioManager.Instance?.PlayFootstep();
                }
            }
        }

        private void HandleInput()
        {
            float h = Input.GetAxisRaw("Horizontal");
            float v = Input.GetAxisRaw("Vertical");
            moveInput = new Vector2(h, v).normalized;

            if (moveInput.sqrMagnitude > 0.01f)
            {
                lastFacingDirection = moveInput;
                if (SpriteRenderer != null)
                {
                    if (h > 0.05f) SpriteRenderer.flipX = false;
                    else if (h < -0.05f) SpriteRenderer.flipX = true;
                }
            }

            // Attack (Space or Left Click)
            if ((Input.GetKeyDown(KeyCode.Space) || Input.GetMouseButtonDown(0)) && Time.time - lastAttackTime >= AttackCooldown)
            {
                Attack();
            }

            // Interact (E)
            if (Input.GetKeyDown(KeyCode.E) && nearestInteractable != null)
            {
                PerformInteraction(nearestInteractable);
            }
        }

        private void Attack()
        {
            lastAttackTime = Time.time;
            AudioManager.Instance?.PlaySlash();

            Vector2 spawnPos = (Vector2)transform.position + lastFacingDirection * 0.4f;

            if (ProjectilePrefab != null)
            {
                GameObject projObj = Instantiate(ProjectilePrefab, spawnPos, Quaternion.identity);
                var proj = projObj.GetComponent<Projectile>();
                if (proj != null)
                {
                    proj.Direction = lastFacingDirection;
                    proj.IsPlayerOwned = true;
                }
            }
            else
            {
                // Fallback direct raycast attack in facing direction
                RaycastHit2D hit = Physics2D.CircleCast(transform.position, 0.6f, lastFacingDirection, 1.2f);
                if (hit.collider != null)
                {
                    var enemy = hit.collider.GetComponent<EnemyAI>();
                    if (enemy != null)
                    {
                        enemy.TakeDamage(30);
                    }
                }
            }
        }

        private void HandleLanternHeatAndChill()
        {
            // Deplete lantern heat
            CurrentLanternHeat = Mathf.Max(0.0f, CurrentLanternHeat - HeatDecayRate * Time.deltaTime);
            OnHeatChanged?.Invoke(CurrentLanternHeat, MaxLanternHeat);

            // If lantern goes dark, freezing damage occurs!
            if (CurrentLanternHeat <= 0.01f)
            {
                frostDamageTimer += Time.deltaTime;
                if (frostDamageTimer >= 1.5f)
                {
                    frostDamageTimer = 0.0f;
                    TakeDamage(6);
                }
            }
            else
            {
                frostDamageTimer = 0.0f;
            }
        }

        public void RestoreHeat(float amount)
        {
            CurrentLanternHeat = Mathf.Min(MaxLanternHeat, CurrentLanternHeat + amount);
            OnHeatChanged?.Invoke(CurrentLanternHeat, MaxLanternHeat);
        }

        public void TakeDamage(int damage)
        {
            CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
            AudioManager.Instance?.PlayHit();
            OnHealthChanged?.Invoke(CurrentHealth, MaxHealth);

            if (CurrentHealth <= 0)
            {
                OnPlayerDied?.Invoke();
            }
        }

        private void UpdateAnimation()
        {
            if (WalkFrames == null || WalkFrames.Length == 0 || SpriteRenderer == null) return;

            if (moveInput.sqrMagnitude > 0.01f)
            {
                walkAnimTimer += Time.deltaTime;
                if (walkAnimTimer >= 0.16f)
                {
                    walkAnimTimer = 0.0f;
                    currentFrame = (currentFrame + 1) % WalkFrames.Length;
                    SpriteRenderer.sprite = WalkFrames[currentFrame];
                }
            }
            else
            {
                currentFrame = 0;
                SpriteRenderer.sprite = WalkFrames[0];
            }
        }

        private void DetectInteractables()
        {
            Collider2D[] colliders = Physics2D.OverlapCircleAll(transform.position, 1.8f);
            InteractiveObject best = null;
            float bestDist = float.MaxValue;

            foreach (var col in colliders)
            {
                var io = col.GetComponent<InteractiveObject>();
                if (io != null)
                {
                    float d = Vector2.Distance(transform.position, io.transform.position);
                    if (d <= io.InteractRadius && d < bestDist)
                    {
                        bestDist = d;
                        best = io;
                    }
                }
            }

            if (best != nearestInteractable)
            {
                nearestInteractable = best;
                if (nearestInteractable != null)
                {
                    OnInteractPromptAvailable?.Invoke(nearestInteractable);
                }
                else
                {
                    OnInteractPromptLost?.Invoke();
                }
            }
        }

        private void PerformInteraction(InteractiveObject io)
        {
            switch (io.Type)
            {
                case InteractableType.Campfire:
                    RestoreHeat(100.0f);
                    CurrentHealth = Mathf.Min(MaxHealth, CurrentHealth + 25);
                    OnHealthChanged?.Invoke(CurrentHealth, MaxHealth);
                    AudioManager.Instance?.PlaySFX("campfire_sizzle", 0.9f);
                    break;

                case InteractableType.Kitabe:
                    RestoreHeat(25.0f);
                    ReadKitabeCount++;
                    AudioManager.Instance?.PlayKitabeChime();
                    break;

                case InteractableType.Relic:
                    RelicsCollected++;
                    RestoreHeat(35.0f);
                    AudioManager.Instance?.PlayHarvest();
                    Destroy(io.gameObject);
                    break;

                case InteractableType.Acorn:
                    AcornsCollected++;
                    RestoreHeat(15.0f);
                    AudioManager.Instance?.PlaySFX("harvest_chime", 0.6f, 1.2f);
                    Destroy(io.gameObject);
                    break;

                case InteractableType.Companion:
                    AudioManager.Instance?.PlaySFX("companion_bark", 0.9f);
                    RestoreHeat(20.0f);
                    break;

                case InteractableType.BilimAgaci:
                    AudioManager.Instance?.PlayVictory();
                    OnVictoryReached?.Invoke();
                    break;
            }

            io.Interact(this);
        }
    }
}
