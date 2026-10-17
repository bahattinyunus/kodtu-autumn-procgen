using UnityEngine;

namespace AutumnProcGen.Entities
{
    public class Projectile : MonoBehaviour
    {
        public Vector2 Direction;
        public float Speed = 8.0f;
        public int Damage = 25;
        public float Lifetime = 1.2f;
        public bool IsPlayerOwned = true;

        private float spawnTime;

        private void Start()
        {
            spawnTime = Time.time;
            float angle = Mathf.Atan2(Direction.y, Direction.x) * Mathf.Rad2Deg;
            transform.rotation = Quaternion.Euler(0, 0, angle);
        }

        private void Update()
        {
            transform.position += (Vector3)(Direction.normalized * Speed * Time.deltaTime);

            if (Time.time - spawnTime >= Lifetime)
            {
                Destroy(gameObject);
            }
        }

        private void OnTriggerEnter2D(Collider2D collision)
        {
            if (IsPlayerOwned)
            {
                var enemy = collision.GetComponent<EnemyAI>();
                if (enemy != null)
                {
                    enemy.TakeDamage(Damage);
                    Destroy(gameObject);
                }
            }
            else
            {
                var player = collision.GetComponent<PlayerController>();
                if (player != null)
                {
                    player.TakeDamage(Damage);
                    Destroy(gameObject);
                }
            }
        }
    }
}
