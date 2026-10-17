using System;
using System.Collections.Generic;
using AutumnProcGen.Core;
using UnityEngine;

namespace AutumnProcGen.ProcGen
{
    public class EntitySpawnInfo
    {
        public Vector2 Position;
        public string EntityType;
        public int Variant;

        public EntitySpawnInfo(Vector2 pos, string type, int variant = 0)
        {
            Position = pos;
            EntityType = type;
            Variant = variant;
        }
    }

    public class StructureSpawnInfo
    {
        public Vector2 Position;
        public string StructureType;
        public int ExtraData;

        public StructureSpawnInfo(Vector2 pos, string type, int extraData = 0)
        {
            Position = pos;
            StructureType = type;
            ExtraData = extraData;
        }
    }

    public class WorldGenerationResult
    {
        public int Width;
        public int Height;
        public string SeedCode;

        public float[,] Elevation;
        public float[,] Moisture;
        public int[,] BiomeGrid; // 1 = Damp, 2 = Amber, 3 = Golden
        public int[,] WalkableGrid; // 0 = Walkable, 1 = Wall
        public int[,] WallBlob47; // 0..46 autotile index

        public Vector2IntCoord SpawnTile;
        public Vector2IntCoord ShrineTile;
        public Vector2IntCoord BilimAgaciTile;

        public List<PlacedProp> Props;
        public List<StructureSpawnInfo> Structures;
        public List<EntitySpawnInfo> Entities;
    }

    public static class AutumnProcGenPipeline
    {
        public static WorldGenerationResult Generate(string seed = "KODTU2026", int width = 64, int height = 64)
        {
            var rng = new Xoshiro256(seed);
            var simplex = new SimplexNoise2D(rng);
            var moistureSimplex = new SimplexNoise2D(new Xoshiro256(rng.NextUInt64().ToString()));

            var result = new WorldGenerationResult
            {
                Width = width,
                Height = height,
                SeedCode = rng.SeedCode,
                Elevation = new float[width, height],
                Moisture = new float[width, height],
                BiomeGrid = new int[width, height],
                WallBlob47 = new int[width, height],
                Props = new List<PlacedProp>(),
                Structures = new List<StructureSpawnInfo>(),
                Entities = new List<EntitySpawnInfo>()
            };

            // Stage 1: Noise & Biomes
            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    float elev = (simplex.SampleFbm(x * 0.05f, y * 0.05f, 4) + 1.0f) * 0.5f;
                    float moist = (moistureSimplex.SampleFbm(x * 0.04f, y * 0.04f, 3) + 1.0f) * 0.5f;

                    result.Elevation[x, y] = Mathf.Clamp01(elev);
                    result.Moisture[x, y] = Mathf.Clamp01(moist);

                    if (moist < 0.38f)
                        result.BiomeGrid[x, y] = 1; // Damp Decay
                    else if (moist < 0.68f)
                        result.BiomeGrid[x, y] = 2; // Burnt Amber
                    else
                        result.BiomeGrid[x, y] = 3; // Golden Corridor
                }
            }

            // Stage 2: Cellular Automata & Topology
            result.WalkableGrid = CellularAutomata.SculptConnectedTopology(
                result.Elevation, rng, width, height, 0.54f, 4, 16);

            // Find Spawn tile near center
            int cx = width / 2;
            int cy = height / 2;
            result.SpawnTile = new Vector2IntCoord(cx, cy);
            if (result.WalkableGrid[cx, cy] == 1)
            {
                int bestD = int.MaxValue;
                for (int y = 3; y < height - 3; y++)
                {
                    for (int x = 3; x < width - 3; x++)
                    {
                        if (result.WalkableGrid[x, y] == 0)
                        {
                            int d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy);
                            if (d2 < bestD)
                            {
                                bestD = d2;
                                result.SpawnTile = new Vector2IntCoord(x, y);
                            }
                        }
                    }
                }
            }

            // Dijkstra & Farthest tile (Bilim Agaci / Final Monument)
            int[,] dijkstra = CellularAutomata.ComputeDijkstra(
                result.WalkableGrid, width, height, result.SpawnTile, out Vector2IntCoord farthest);
            result.BilimAgaciTile = farthest;
            result.ShrineTile = new Vector2IntCoord((result.SpawnTile.x + farthest.x) / 2, (result.SpawnTile.y + farthest.y) / 2);
            if (result.WalkableGrid[result.ShrineTile.x, result.ShrineTile.y] == 1)
            {
                result.ShrineTile = result.SpawnTile;
            }

            // Stage 3: Autotile Wall Blobs (0..46)
            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    if (result.WalkableGrid[x, y] == 1)
                    {
                        result.WallBlob47[x, y] = AutotileMasks.CalculateBlobIndex(
                            result.WalkableGrid, x, y, width, height, 1);
                    }
                }
            }

            // Stage 4: Structures (Campfire at spawn, Bilim Agaci, Kitabes)
            // Campfire near spawn
            result.Structures.Add(new StructureSpawnInfo(
                new Vector2(result.SpawnTile.x + 1.5f, result.SpawnTile.y), "campfire"));

            // Companion Kangal Dog near spawn
            result.Entities.Add(new EntitySpawnInfo(
                new Vector2(result.SpawnTile.x - 1.2f, result.SpawnTile.y - 0.5f), "companion"));

            // Bilim Agaci Monument at farthest clearing
            result.Structures.Add(new StructureSpawnInfo(
                new Vector2(result.BilimAgaciTile.x + 0.5f, result.BilimAgaciTile.y + 0.5f), "bilim_agaci"));

            // Place Historical Kitabes along the map in open clearings
            var allWalkable = new List<Vector2IntCoord>();
            for (int y = 4; y < height - 4; y++)
            {
                for (int x = 4; x < width - 4; x++)
                {
                    if (result.WalkableGrid[x, y] == 0 &&
                        (Math.Abs(x - result.SpawnTile.x) > 4 || Math.Abs(y - result.SpawnTile.y) > 4))
                    {
                        allWalkable.Add(new Vector2IntCoord(x, y));
                    }
                }
            }

            // Shuffle candidates
            for (int i = allWalkable.Count - 1; i > 0; i--)
            {
                int j = rng.Range(0, i);
                var temp = allWalkable[i];
                allWalkable[i] = allWalkable[j];
                allWalkable[j] = temp;
            }

            int kitabeCount = Math.Min(StoryData.Inscriptions.Length, allWalkable.Count);
            for (int k = 0; k < kitabeCount; k++)
            {
                var pt = allWalkable[k];
                result.Structures.Add(new StructureSpawnInfo(
                    new Vector2(pt.x + 0.5f, pt.y + 0.5f), "kitabe", k));
            }

            // Extra Campfires along the trail
            for (int cf = kitabeCount; cf < kitabeCount + 3 && cf < allWalkable.Count; cf++)
            {
                var pt = allWalkable[cf];
                result.Structures.Add(new StructureSpawnInfo(
                    new Vector2(pt.x + 0.5f, pt.y + 0.5f), "campfire"));
            }

            // Stage 5: Ecological Props (Trees, Piles, Rocks)
            result.Props = PoissonDiskSampling.DistributeProps(
                result.WalkableGrid, width, height, rng, 2.8f);

            // Stage 6: Threat Budgeting & Entities (Relics, Acorns, Wolves, Wisps, Stalkers)
            int cursor = kitabeCount + 3;
            int totalEnemies = Mathf.Clamp((width * height) / 80, 8, 30);
            for (int e = 0; e < totalEnemies && cursor < allWalkable.Count; e++, cursor++)
            {
                var pt = allWalkable[cursor];
                float r = rng.Random();
                string type;
                if (r < 0.35f) type = "wolf";
                else if (r < 0.65f) type = "wisp";
                else if (r < 0.85f) type = "stalker";
                else type = "golem";

                result.Entities.Add(new EntitySpawnInfo(new Vector2(pt.x + 0.5f, pt.y + 0.5f), type));
            }

            // Collectibles: 5 Relics & Acorns
            for (int relic = 0; relic < 5 && cursor < allWalkable.Count; relic++, cursor++)
            {
                var pt = allWalkable[cursor];
                result.Entities.Add(new EntitySpawnInfo(new Vector2(pt.x + 0.5f, pt.y + 0.5f), "relic"));
            }

            for (int acorn = 0; acorn < 8 && cursor < allWalkable.Count; acorn++, cursor++)
            {
                var pt = allWalkable[cursor];
                result.Entities.Add(new EntitySpawnInfo(new Vector2(pt.x + 0.5f, pt.y + 0.5f), "acorn"));
            }

            return result;
        }
    }
}
