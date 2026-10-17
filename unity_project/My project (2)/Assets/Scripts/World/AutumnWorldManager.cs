using System.Collections.Generic;
using AutumnProcGen.Core;
using AutumnProcGen.Entities;
using AutumnProcGen.ProcGen;
using AutumnProcGen.UI;
using UnityEngine;
using UnityEngine.Tilemaps;

namespace AutumnProcGen.World
{
    public class AutumnWorldManager : MonoBehaviour
    {
        [Header("Seed & Dimensions")]
        public string Seed = "KODTU2026";
        public int MapWidth = 64;
        public int MapHeight = 64;

        [Header("Tilemaps & Grid")]
        public Grid WorldGrid;
        public Tilemap FloorTilemap;
        public Tilemap WallTilemap;

        [Header("Prefabs / Fallback Spawners")]
        public GameObject PlayerPrefab;
        public GameObject EnemyPrefab;
        public GameObject PropPrefab;
        public GameObject StructurePrefab;

        private WorldGenerationResult worldData;
        private readonly Dictionary<string, Sprite> spriteCache = new Dictionary<string, Sprite>();
        private readonly Dictionary<string, Tile> tileCache = new Dictionary<string, Tile>();

        private void Awake()
        {
            PreloadSprites();
        }

        private void Start()
        {
            EnsureSceneSetup();
            GenerateAndBuildWorld();
            StartAtmosphere();
        }

        private void PreloadSprites()
        {
            Sprite[] loaded = Resources.LoadAll<Sprite>("Sprites");
            foreach (var s in loaded)
            {
                spriteCache[s.name] = s;
            }
        }

        private Sprite GetSprite(string name)
        {
            if (spriteCache.TryGetValue(name, out Sprite s)) return s;
            Sprite loaded = Resources.Load<Sprite>("Sprites/" + name);
            if (loaded != null) spriteCache[name] = loaded;
            return loaded;
        }

        private Tile GetTileForSprite(string spriteName)
        {
            if (tileCache.TryGetValue(spriteName, out Tile cached)) return cached;
            Sprite s = GetSprite(spriteName);
            if (s == null) return null;
            Tile t = ScriptableObject.CreateInstance<Tile>();
            t.sprite = s;
            tileCache[spriteName] = t;
            return t;
        }

        private void EnsureSceneSetup()
        {
            // Camera setup
            Camera cam = Camera.main;
            if (cam == null)
            {
                var camObj = new GameObject("Main Camera", typeof(Camera), typeof(AudioListener));
                cam = camObj.GetComponent<Camera>();
                camObj.tag = "MainCamera";
            }
            cam.orthographic = true;
            cam.orthographicSize = 5.625f; // 320x180 virtual canvas with 16 PPU
            cam.backgroundColor = AutumnPalette.DeepVoid;

            if (cam.GetComponent<PixelPerfectCameraFollow>() == null)
            {
                cam.gameObject.AddComponent<PixelPerfectCameraFollow>();
            }

            // Audio Manager
            if (AudioManager.Instance == null)
            {
                var audioObj = new GameObject("AudioManager", typeof(AudioManager));
            }

            // Grid & Tilemaps
            if (WorldGrid == null)
            {
                var gridObj = new GameObject("Grid", typeof(Grid));
                WorldGrid = gridObj.GetComponent<Grid>();
                gridObj.transform.position = Vector3.zero;
            }

            if (FloorTilemap == null)
            {
                var floorObj = new GameObject("FloorTilemap", typeof(Tilemap), typeof(TilemapRenderer));
                floorObj.transform.SetParent(WorldGrid.transform, false);
                FloorTilemap = floorObj.GetComponent<Tilemap>();
                var r = floorObj.GetComponent<TilemapRenderer>();
                r.sortingOrder = -10;
            }

            if (WallTilemap == null)
            {
                var wallObj = new GameObject("WallTilemap", typeof(Tilemap), typeof(TilemapRenderer), typeof(TilemapCollider2D), typeof(Rigidbody2D));
                wallObj.transform.SetParent(WorldGrid.transform, false);
                WallTilemap = wallObj.GetComponent<Tilemap>();
                var r = wallObj.GetComponent<TilemapRenderer>();
                r.sortingOrder = -5;

                var rb = wallObj.GetComponent<Rigidbody2D>();
                rb.bodyType = RigidbodyType2D.Static;

                var col = wallObj.GetComponent<TilemapCollider2D>();
            }

            // UI HUD setup
            if (FindFirstObjectByType<AutumnHUD>() == null)
            {
                CreateSimpleHUD();
            }
        }

        private void GenerateAndBuildWorld()
        {
            worldData = AutumnProcGenPipeline.Generate(Seed, MapWidth, MapHeight);

            var hud = FindFirstObjectByType<AutumnHUD>();
            hud?.SetSeedCode(worldData.SeedCode);

            // 1. Paint Floor & Wall Tiles
            for (int y = 0; y < worldData.Height; y++)
            {
                for (int x = 0; x < worldData.Width; x++)
                {
                    Vector3Int pos = new Vector3Int(x, y, 0);

                    // Biome floor tile
                    int biome = worldData.BiomeGrid[x, y];
                    string bName = biome == 1 ? "damp" : (biome == 2 ? "amber" : "golden");
                    int variant = (x * 7 + y * 13) % 4;
                    Tile floorTile = GetTileForSprite($"floor_{bName}_{variant}");
                    if (floorTile != null) FloorTilemap.SetTile(pos, floorTile);

                    // Solid walls (Autotile 47)
                    if (worldData.WalkableGrid[x, y] == 1)
                    {
                        int blobIdx = worldData.WallBlob47[x, y];
                        Tile wallTile = GetTileForSprite($"autotile_{blobIdx:02d}");
                        if (wallTile != null) WallTilemap.SetTile(pos, wallTile);
                    }
                }
            }

            // 2. Spawn Player
            Vector3 playerPos = new Vector3(worldData.SpawnTile.x + 0.5f, worldData.SpawnTile.y + 0.5f, 0);
            SpawnPlayer(playerPos);

            // 3. Spawn Structures (Campfire, Kitabe, Bilim Agaci)
            foreach (var s in worldData.Structures)
            {
                SpawnStructure(s);
            }

            // 4. Spawn Props (Trees, Piles, Rocks)
            foreach (var p in worldData.Props)
            {
                SpawnProp(p);
            }

            // 5. Spawn Entities (Wolves, Wisps, Stalkers, Golems, Relics, Kangal)
            foreach (var e in worldData.Entities)
            {
                SpawnEntity(e);
            }

            // 6. Spawn Wind Falling Leaves Particle System
            SpawnLeafParticleSystem();
        }

        private void SpawnPlayer(Vector3 pos)
        {
            GameObject playerObj = new GameObject("Player", typeof(SpriteRenderer), typeof(CircleCollider2D), typeof(Rigidbody2D), typeof(PlayerController));
            playerObj.transform.position = pos;

            var sr = playerObj.GetComponent<SpriteRenderer>();
            sr.sprite = GetSprite("player_frame_0");
            sr.sortingOrder = 5;

            var col = playerObj.GetComponent<CircleCollider2D>();
            col.radius = 0.35f;

            var controller = playerObj.GetComponent<PlayerController>();
            controller.SpriteRenderer = sr;
            controller.WalkFrames = new Sprite[]
            {
                GetSprite("player_frame_0"),
                GetSprite("player_frame_1"),
                GetSprite("player_frame_2")
            };

            // Set camera target
            var camFollow = Camera.main.GetComponent<PixelPerfectCameraFollow>();
            if (camFollow != null) camFollow.Target = playerObj.transform;
        }

        private void SpawnStructure(StructureSpawnInfo s)
        {
            GameObject sObj = new GameObject($"Structure_{s.StructureType}", typeof(SpriteRenderer), typeof(CircleCollider2D), typeof(InteractiveObject));
            sObj.transform.position = new Vector3(s.Position.x, s.Position.y, 0);

            var sr = sObj.GetComponent<SpriteRenderer>();
            sr.sortingOrder = 2;

            var col = sObj.GetComponent<CircleCollider2D>();
            col.isTrigger = true;
            col.radius = 1.0f;

            var io = sObj.GetComponent<InteractiveObject>();
            io.InteractRadius = 1.6f;

            switch (s.StructureType)
            {
                case "campfire":
                    sr.sprite = GetSprite("campfire_0");
                    io.Type = InteractableType.Campfire;
                    io.PromptText = "[E] Kamp Atesinde Isin & Dinlen";
                    break;
                case "kitabe":
                    sr.sprite = GetSprite("kitabe");
                    io.Type = InteractableType.Kitabe;
                    io.InscriptionIndex = s.ExtraData;
                    io.PromptText = "[E] ODTU Tarihsel Kitabesini Oku";
                    break;
                case "bilim_agaci":
                    sr.sprite = GetSprite("bilim_agaci");
                    io.Type = InteractableType.BilimAgaci;
                    io.PromptText = "[E] ODTU Bilim Agaci Mesalesini Yak (Zafer)";
                    col.radius = 1.8f;
                    io.InteractRadius = 2.2f;
                    break;
            }
        }

        private void SpawnProp(PlacedProp p)
        {
            GameObject propObj = new GameObject($"Prop_{p.kind}", typeof(SpriteRenderer));
            propObj.transform.position = new Vector3(p.x, p.y, 0);

            var sr = propObj.GetComponent<SpriteRenderer>();
            sr.sprite = GetSprite($"{p.kind}_{p.variant}");
            sr.sortingOrder = Mathf.RoundToInt(-p.y * 10); // Y-sort

            // If it's a solid tree or rock, add a small base obstacle collider
            if (p.kind.StartsWith("tree") || p.kind == "stone")
            {
                var col = propObj.AddComponent<CircleCollider2D>();
                col.radius = p.kind.StartsWith("tree") ? 0.35f : 0.25f;
                col.offset = new Vector2(0, -0.3f);
            }
        }

        private void SpawnEntity(EntitySpawnInfo e)
        {
            if (e.EntityType == "relic" || e.EntityType == "acorn")
            {
                GameObject colObj = new GameObject($"Item_{e.EntityType}", typeof(SpriteRenderer), typeof(CircleCollider2D), typeof(InteractiveObject));
                colObj.transform.position = new Vector3(e.Position.x, e.Position.y, 0);

                var sr = colObj.GetComponent<SpriteRenderer>();
                sr.sprite = GetSprite($"{e.EntityType}_0");
                sr.sortingOrder = 1;

                var col = colObj.GetComponent<CircleCollider2D>();
                col.isTrigger = true;
                col.radius = 0.8f;

                var io = colObj.GetComponent<InteractiveObject>();
                io.Type = e.EntityType == "relic" ? InteractableType.Relic : InteractableType.Acorn;
                io.PromptText = e.EntityType == "relic" ? "[E] Varlik Hatirasini Topla" : "[E] Mese Palamudunu Al";
            }
            else if (e.EntityType == "companion")
            {
                GameObject dogObj = new GameObject("ODTU_Kangali", typeof(SpriteRenderer), typeof(CircleCollider2D), typeof(InteractiveObject));
                dogObj.transform.position = new Vector3(e.Position.x, e.Position.y, 0);

                var sr = dogObj.GetComponent<SpriteRenderer>();
                sr.sprite = GetSprite("companion_0");
                sr.sortingOrder = 3;

                var col = dogObj.GetComponent<CircleCollider2D>();
                col.isTrigger = true;
                col.radius = 1.0f;

                var io = dogObj.GetComponent<InteractiveObject>();
                io.Type = InteractableType.Companion;
                io.PromptText = "[E] Bozkir Kangalini Sev";
            }
            else
            {
                // Shadow enemy
                GameObject enemyObj = new GameObject($"Enemy_{e.EntityType}", typeof(SpriteRenderer), typeof(CircleCollider2D), typeof(Rigidbody2D), typeof(EnemyAI));
                enemyObj.transform.position = new Vector3(e.Position.x, e.Position.y, 0);

                var sr = enemyObj.GetComponent<SpriteRenderer>();
                sr.sprite = GetSprite($"{e.EntityType}_0");
                sr.sortingOrder = 4;

                var col = enemyObj.GetComponent<CircleCollider2D>();
                col.radius = 0.4f;

                var ai = enemyObj.GetComponent<EnemyAI>();
                ai.EnemyType = e.EntityType;
                ai.SpriteRenderer = sr;
                ai.Frames = new Sprite[]
                {
                    GetSprite($"{e.EntityType}_0"),
                    GetSprite($"{e.EntityType}_1")
                };
            }
        }

        private void SpawnLeafParticleSystem()
        {
            GameObject partObj = new GameObject("WindLeavesParticles", typeof(ParticleSystem));
            partObj.transform.position = new Vector3(MapWidth / 2, MapHeight / 2, -1);

            var ps = partObj.GetComponent<ParticleSystem>();
            var main = ps.main;
            main.startLifetime = 8.0f;
            main.startSpeed = 2.5f;
            main.startSize = 0.15f;
            main.startColor = AutumnPalette.SunlitBirch;
            main.maxParticles = 300;

            var emission = ps.emission;
            emission.rateOverTime = 35.0f;

            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(MapWidth, MapHeight, 1);

            var vel = ps.velocityOverLifetime;
            vel.enabled = true;
            vel.x = new ParticleSystem.MinMaxCurve(1.5f, 3.0f);
            vel.y = new ParticleSystem.MinMaxCurve(-0.8f, -0.2f);
        }

        private void StartAtmosphere()
        {
            AudioManager.Instance?.PlayAmbience("wind_ambience", 0.4f);
            AudioManager.Instance?.PlayMusic("autumn_theme", 0.6f);
        }

        private void CreateSimpleHUD()
        {
            GameObject hudCanvas = new GameObject("AutumnHUD_Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster), typeof(AutumnHUD));
            var c = hudCanvas.GetComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;

            var cs = hudCanvas.GetComponent<CanvasScaler>();
            cs.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            cs.referenceResolution = new Vector2(1280, 720);

            var hud = hudCanvas.GetComponent<AutumnHUD>();

            // Top Status Panel
            var statusPanel = new GameObject("StatusPanel", typeof(RectTransform));
            statusPanel.transform.SetParent(hudCanvas.transform, false);
            var rect = statusPanel.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0, 1);
            rect.anchorMax = new Vector2(0, 1);
            rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -24);
            rect.sizeDelta = new Vector2(300, 100);

            // Seed Text
            var seedObj = new GameObject("SeedCodeText", typeof(Text));
            seedObj.transform.SetParent(statusPanel.transform, false);
            var seedText = seedObj.GetComponent<Text>();
            seedText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            seedText.fontSize = 18;
            seedText.color = AutumnPalette.SunlitBirch;
            seedText.text = "TOHUM: KODTU-2026-FALL";
            var seedRect = seedObj.GetComponent<RectTransform>();
            seedRect.anchoredPosition = new Vector2(0, 0);
            seedRect.sizeDelta = new Vector2(300, 26);
            hud.SeedCodeText = seedText;

            // Prompt Text (center bottom)
            var promptObj = new GameObject("PromptText", typeof(Text));
            promptObj.transform.SetParent(hudCanvas.transform, false);
            var promptText = promptObj.GetComponent<Text>();
            promptText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            promptText.fontSize = 24;
            promptText.color = AutumnPalette.PaleSunbeam;
            promptText.alignment = TextAnchor.MiddleCenter;
            var promptRect = promptObj.GetComponent<RectTransform>();
            promptRect.anchorMin = new Vector2(0.5f, 0.2f);
            promptRect.anchorMax = new Vector2(0.5f, 0.2f);
            promptRect.sizeDelta = new Vector2(600, 40);
            hud.PromptText = promptText;

            // Dialog Panel
            var dialogObj = new GameObject("DialogPanel", typeof(Image));
            dialogObj.transform.SetParent(hudCanvas.transform, false);
            var dialogImg = dialogObj.GetComponent<Image>();
            dialogImg.color = new Color(AutumnPalette.DeepVoid.r, AutumnPalette.DeepVoid.g, AutumnPalette.DeepVoid.b, 0.92f);
            var dRect = dialogObj.GetComponent<RectTransform>();
            dRect.anchorMin = new Vector2(0.5f, 0.22f);
            dRect.anchorMax = new Vector2(0.5f, 0.22f);
            dRect.sizeDelta = new Vector2(760, 200);

            var titleObj = new GameObject("TitleText", typeof(Text));
            titleObj.transform.SetParent(dialogObj.transform, false);
            var tText = titleObj.GetComponent<Text>();
            tText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            tText.fontSize = 20;
            tText.color = AutumnPalette.SunlitBirch;
            tText.text = "ODTU TARIH KITABESI";
            var tRect = titleObj.GetComponent<RectTransform>();
            tRect.anchoredPosition = new Vector2(0, 70);
            tRect.sizeDelta = new Vector2(700, 30);
            hud.DialogTitleText = tText;

            var bodyObj = new GameObject("BodyText", typeof(Text));
            bodyObj.transform.SetParent(dialogObj.transform, false);
            var bText = bodyObj.GetComponent<Text>();
            bText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            bText.fontSize = 17;
            bText.color = AutumnPalette.AutumnMist;
            var bRect = bodyObj.GetComponent<RectTransform>();
            bRect.anchoredPosition = new Vector2(0, -10);
            bRect.sizeDelta = new Vector2(700, 110);
            hud.DialogBodyText = bText;

            dialogObj.SetActive(false);
            hud.DialogPanel = dialogObj;
        }
    }
}
