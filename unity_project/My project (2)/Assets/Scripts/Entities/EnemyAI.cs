using System;
using System.Collections;
using AutumnProcGen.Core;
using UnityEngine;

namespace AutumnProcGen.Entities
{
    public enum EnemyState
    {
        Wander,
        Chase,
        Attack,
        Dead
    }

    [RequireComponent(typeof(Rigidbody2D))]
    [RequireComponent(typeof(Collider2D))]
    public class EnemyAI : MonoBehaviour
    {
        [Header("Stats")]
        public string EnemyType = "wolf"; // wolf, wisp, stalker, golem
        public int MaxHealth = 40;
        public int CurrentHealth = 40;
        public int AttackDamage = 15;
        public float MoveSpeed = 2.4f;
        public float AggroRadius = 6.0f;
        public float AttackRange = 1.1f;
        public float AttackCooldown = 1.2f;

        [Header("Sprites")]
        public SpriteRenderer SpriteRenderer;
        public Sprite[] Frames;

        private Rigidbody2D rb;
        private Transform playerTarget;
        private EnemyState state = EnemyState.Wander;
        private float lastAttackTime = -10.0f;
        private Vector2 wanderTarget;
        private float wanderTimer = 0.0f;
        private float animTimer = 0.0f;
        private int currentFrame = 0;

        private void Awake()
        {
            rb = GetComponent<Rigidbody2D>();
            rb.gravityScale = 0;
            rb.freezeRotation = true;
            if (SpriteRenderer == null) SpriteRenderer = GetComponent<SpriteRenderer>();

            SetupStatsByType();
        }

        private void Start()
        {
            CurrentHealth = MaxHealth;
            var player = FindFirstObjectByType<PlayerController>();
            if (player != null) playerTarget = player.transform;
            PickNewWanderTarget();
        }

        private void SetupStatsByType()
        {
            switch (EnemyType)
            {
                case "wolf":
                    MaxHealth = 35;
                    MoveSpeed = 3.6f;
                    AttackDamage = 18;
                    AggroRadius = 7.0f;
                    break;
                case "wisp":
                    MaxHealth = 20;
                    MoveSpeed = 2.2f;
                    AttackDamage = 10;
                    AggroRadius = 5.5f;
                    break;
                case "stalker":
                    MaxHealth = 50;
                    MoveSpeed = 2.8f;
                    AttackDamage = 22;
                    AggroRadius = 6.0f;
                    break;
                case "golem":
                    MaxHealth = 90;
                    MoveSpeed = 1.6f;
                    AttackDamage = 35;
                    AggroRadius = 4.5f;
                    break;
                case "lynx":
                    MaxHealth = 40;
                    MoveSpeed = 3.5f;
                    AttackDamage = 20;
                    AggroRadius = 7.5f;
                    break;
            }
        }

        private void Update()
        {
            if (state == EnemyState.Dead) return;

            UpdateAnimation();

            if (playerTarget == null)
            {
                var p = FindFirstObjectByType<PlayerController>();
                if (p != null) playerTarget = p.transform;
                return;
            }

            float dist = Vector2.Distance(transform.position, playerTarget.position);

            if (dist <= AttackRange && Time.time - lastAttackTime >= AttackCooldown)
            {
                PerformAttack();
            }
            else if (dist <= AggroRadius)
            {
                state = EnemyState.Chase;
            }
            else
            {
                state = EnemyState.Wander;
            }
        }

        private void FixedUpdate()
        {
            if (state == EnemyState.Dead)
            {
                rb.linearVelocity = Vector2.zero;
                return;
            }

            if (state == EnemyState.Chase && playerTarget != null)
            {
                Vector2 dir = ((Vector2)playerTarget.position - (Vector2)transform.position).normalized;
                rb.linearVelocity = dir * MoveSpeed;
                FlipSprite(dir.x);
            }
            else if (state == EnemyState.Wander)
            {
                wanderTimer += Time.fixedDeltaTime;
                if (wanderTimer >= 3.0f || Vector2.Distance(transform.position, wanderTarget) < 0.4f)
                {
                    wanderTimer = 0.0f;
                    PickNewWanderTarget();
                }
                Vector2 dir = (wanderTarget - (Vector2)transform.position).normalized;
                rb.linearVelocity = dir * (MoveSpeed * 0.5f);
                FlipSprite(dir.x);
            }
        }

        private void FlipSprite(float dirX)
        {
            if (SpriteRenderer != null)
            {
                if (dirX > 0.05f) SpriteRenderer.flipX = false;
                else if (dirX < -0.05f) SpriteRenderer.flipX = true;
            }
        }

        private void PickNewWanderTarget()
        {
            wanderTarget = (Vector2)transform.position + UnityEngine.Random.insideUnitCircle * 3.5f;
        }

        private void PerformAttack()
        {
            lastAttackTime = Time.time;
            state = EnemyState.Attack;

            if (playerTarget != null)
            {
                var player = playerTarget.GetComponent<PlayerController>();
                if (player != null)
                {
                    player.TakeDamage(AttackDamage);
                }
            }
        }

        public void TakeDamage(int damage)
        {
            if (state == EnemyState.Dead) return;

            CurrentHealth -= damage;
            StartCoroutine(DamageFlashRoutine());
            AudioManager.Instance?.PlayHit();

            if (CurrentHealth <= 0)
            {
                Die();
            }
        }

        private IEnumerator DamageFlashRoutine()
        {
            if (SpriteRenderer != null)
            {
                Color original = SpriteRenderer.color;
                SpriteRenderer.color = AutumnPalette.SunlitBirch;
                yield return new WaitForSeconds(0.12f);
                if (SpriteRenderer != null)
                    SpriteRenderer.color = original;
            }
        }

        private void Die()
        {
            state = EnemyState.Dead;
            rb.linearVelocity = Vector2.zero;

            // Replenish player lantern heat slightly on defeating shadow
            var player = FindFirstObjectByType<PlayerController>();
            player?.RestoreHeat(15.0f);

            Destroy(gameObject, 0.2f);
        }

        private void UpdateAnimation()
        {
            if (Frames == null || Frames.Length < 2 || SpriteRenderer == null) return;

            animTimer += Time.deltaTime;
            if (animTimer >= 0.22f)
            {
                animTimer = 0.0f;
                currentFrame = (currentFrame + 1) % Frames.Length;
                SpriteRenderer.sprite = Frames[currentFrame];
            }
        }
    }
}
