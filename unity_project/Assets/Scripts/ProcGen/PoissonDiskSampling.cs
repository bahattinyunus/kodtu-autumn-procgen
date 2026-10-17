using System;
using System.Collections.Generic;
using AutumnProcGen.Core;
using UnityEngine;

namespace AutumnProcGen.ProcGen
{
    public struct PlacedProp
    {
        public float x;
        public float y;
        public string kind;
        public int variant;

        public PlacedProp(float x, float y, string kind, int variant)
        {
            this.x = x;
            this.y = y;
            this.kind = kind;
            this.variant = variant;
        }
    }

    public static class PoissonDiskSampling
    {
        public static List<PlacedProp> DistributeProps(
            int[,] walkableGrid,
            int width,
            int height,
            Xoshiro256 rng,
            float minRadius = 2.2f,
            int k = 30)
        {
            var props = new List<PlacedProp>();
            float cellSize = minRadius / Mathf.Sqrt(2.0f);
            int gridW = Mathf.CeilToInt(width / cellSize);
            int gridH = Mathf.CeilToInt(height / cellSize);

            int[,] grid = new int[gridW, gridH];
            for (int gy = 0; gy < gridH; gy++)
                for (int gx = 0; gx < gridW; gx++)
                    grid[gx, gy] = -1;

            var activeList = new List<Vector2>();

            // Find valid seed point
            for (int attempts = 0; attempts < 100; attempts++)
            {
                int rx = rng.Range(3, width - 4);
                int ry = rng.Range(3, height - 4);
                if (walkableGrid[rx, ry] == 0)
                {
                    Vector2 seed = new Vector2(rx + 0.5f, ry + 0.5f);
                    activeList.Add(seed);
                    int gx = Mathf.Clamp(Mathf.FloorToInt(seed.x / cellSize), 0, gridW - 1);
                    int gy = Mathf.Clamp(Mathf.FloorToInt(seed.y / cellSize), 0, gridH - 1);
                    grid[gx, gy] = 0;
                    props.Add(CreateRandomProp(seed.x, seed.y, rng));
                    break;
                }
            }

            while (activeList.Count > 0)
            {
                int randIdx = rng.Range(0, activeList.Count - 1);
                Vector2 cur = activeList[randIdx];
                bool found = false;

                for (int i = 0; i < k; i++)
                {
                    float angle = rng.Uniform(0.0f, Mathf.PI * 2.0f);
                    float r = rng.Uniform(minRadius, minRadius * 2.0f);
                    Vector2 candidate = cur + new Vector2(Mathf.Cos(angle) * r, Mathf.Sin(angle) * r);

                    int cx = Mathf.FloorToInt(candidate.x);
                    int cy = Mathf.FloorToInt(candidate.y);

                    if (cx >= 3 && cx < width - 3 && cy >= 3 && cy < height - 3 && walkableGrid[cx, cy] == 0)
                    {
                        int cgx = Mathf.Clamp(Mathf.FloorToInt(candidate.x / cellSize), 0, gridW - 1);
                        int cgy = Mathf.Clamp(Mathf.FloorToInt(candidate.y / cellSize), 0, gridH - 1);

                        bool ok = true;
                        for (int dy = -2; dy <= 2 && ok; dy++)
                        {
                            for (int dx = -2; dx <= 2 && ok; dx++)
                            {
                                int ngx = cgx + dx;
                                int ngy = cgy + dy;
                                if (ngx >= 0 && ngx < gridW && ngy >= 0 && ngy < gridH)
                                {
                                    int neighborIdx = grid[ngx, ngy];
                                    if (neighborIdx != -1)
                                    {
                                        PlacedProp other = props[neighborIdx];
                                        float d2 = (candidate.x - other.x) * (candidate.x - other.x) + (candidate.y - other.y) * (candidate.y - other.y);
                                        if (d2 < minRadius * minRadius)
                                            ok = false;
                                    }
                                }
                            }
                        }

                        if (ok)
                        {
                            grid[cgx, cgy] = props.Count;
                            props.Add(CreateRandomProp(candidate.x, candidate.y, rng));
                            activeList.Add(candidate);
                            found = true;
                            break;
                        }
                    }
                }

                if (!found)
                {
                    activeList.RemoveAt(randIdx);
                }
            }

            return props;
        }

        private static PlacedProp CreateRandomProp(float x, float y, Xoshiro256 rng)
        {
            float roll = rng.Random();
            string kind;
            int variant = rng.Range(0, 2);

            if (roll < 0.35f)
            {
                // Trees
                string[] trees = { "tree_maple", "tree_birch", "tree_oak" };
                kind = rng.Choice(trees);
            }
            else if (roll < 0.60f)
            {
                kind = "leaf_pile";
            }
            else if (roll < 0.75f)
            {
                kind = "bush_amber";
            }
            else if (roll < 0.88f)
            {
                kind = "mushroom";
            }
            else if (roll < 0.95f)
            {
                kind = "stone";
            }
            else
            {
                kind = "log";
            }

            return new PlacedProp(x, y, kind, variant);
        }
    }
}
