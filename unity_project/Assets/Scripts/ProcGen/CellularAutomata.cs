using System;
using System.Collections.Generic;
using AutumnProcGen.Core;
using UnityEngine;

namespace AutumnProcGen.ProcGen
{
    public struct Vector2IntCoord
    {
        public int x;
        public int y;

        public Vector2IntCoord(int x, int y)
        {
            this.x = x;
            this.y = y;
        }

        public override bool Equals(object obj)
        {
            if (!(obj is Vector2IntCoord other)) return false;
            return x == other.x && y == other.y;
        }

        public override int GetHashCode()
        {
            return (x * 397) ^ y;
        }
    }

    public static class CellularAutomata
    {
        public static List<Vector2IntCoord> BresenhamLine(int x0, int y0, int x1, int y1)
        {
            var points = new List<Vector2IntCoord>();
            int dx = Math.Abs(x1 - x0);
            int dy = -Math.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1;
            int sy = y0 < y1 ? 1 : -1;
            int err = dx + dy;
            int x = x0, y = y0;

            while (true)
            {
                points.Add(new Vector2IntCoord(x, y));
                if (x == x1 && y == y1) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; x += sx; }
                if (e2 <= dx) { err += dx; y += sy; }
            }

            return points;
        }

        public static int[,] StepB678_S345678(int[,] grid, int width, int height)
        {
            int[,] nextGrid = new int[width, height];

            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    if (x < 2 || x >= width - 2 || y < 2 || y >= height - 2)
                    {
                        nextGrid[x, y] = 1;
                        continue;
                    }

                    int walls = 0;
                    for (int dy = -1; dy <= 1; dy++)
                    {
                        for (int dx = -1; dx <= 1; dx++)
                        {
                            if (dx == 0 && dy == 0) continue;
                            if (grid[x + dx, y + dy] == 1) walls++;
                        }
                    }

                    if (grid[x, y] == 0)
                    {
                        // Born if 6, 7, 8
                        nextGrid[x, y] = (walls >= 6 && walls <= 8) ? 1 : 0;
                    }
                    else
                    {
                        // Survive if 3..8
                        nextGrid[x, y] = (walls >= 3 && walls <= 8) ? 1 : 0;
                    }
                }
            }

            return nextGrid;
        }

        public static List<List<Vector2IntCoord>> FindConnectedClearings(int[,] grid, int width, int height)
        {
            bool[,] visited = new bool[width, height];
            var components = new List<List<Vector2IntCoord>>();

            for (int y = 1; y < height - 1; y++)
            {
                for (int x = 1; x < width - 1; x++)
                {
                    if (grid[x, y] == 0 && !visited[x, y])
                    {
                        var comp = new List<Vector2IntCoord>();
                        var queue = new Queue<Vector2IntCoord>();
                        queue.Enqueue(new Vector2IntCoord(x, y));
                        visited[x, y] = true;

                        while (queue.Count > 0)
                        {
                            var cur = queue.Dequeue();
                            comp.Add(cur);

                            int[] dxs = { 1, -1, 0, 0 };
                            int[] dys = { 0, 0, 1, -1 };
                            for (int d = 0; d < 4; d++)
                            {
                                int nx = cur.x + dxs[d];
                                int ny = cur.y + dys[d];
                                if (nx >= 0 && nx < width && ny >= 0 && ny < height)
                                {
                                    if (grid[nx, ny] == 0 && !visited[nx, ny])
                                    {
                                        visited[nx, ny] = true;
                                        queue.Enqueue(new Vector2IntCoord(nx, ny));
                                    }
                                }
                            }
                        }
                        components.Add(comp);
                    }
                }
            }

            components.Sort((a, b) => b.Count.CompareTo(a.Count));
            return components;
        }

        public static int[,] SculptConnectedTopology(
            float[,] elevation,
            Xoshiro256 rng,
            int width,
            int height,
            float wallThreshold = 0.56f,
            int caIterations = 4,
            int minClearingSize = 18)
        {
            int[,] grid = new int[width, height];
            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    grid[x, y] = (elevation[x, y] >= wallThreshold) ? 1 : 0;
                    if (x < 2 || x >= width - 2 || y < 2 || y >= height - 2)
                        grid[x, y] = 1;
                }
            }

            // Central glade seed
            int cx = width / 2;
            int cy = height / 2;
            for (int dy = -4; dy <= 4; dy++)
            {
                for (int dx = -4; dx <= 4; dx++)
                {
                    if (dx * dx + dy * dy <= 18)
                    {
                        if (cx + dx >= 2 && cx + dx < width - 2 && cy + dy >= 2 && cy + dy < height - 2)
                            grid[cx + dx, cy + dy] = 0;
                    }
                }
            }

            // 4 satellite glades
            for (int i = 0; i < 4; i++)
            {
                int gx = rng.Range(8, width - 9);
                int gy = rng.Range(8, height - 9);
                for (int dy = -3; dy <= 3; dy++)
                {
                    for (int dx = -3; dx <= 3; dx++)
                    {
                        if (dx * dx + dy * dy <= 10)
                        {
                            if (gx + dx >= 2 && gx + dx < width - 2 && gy + dy >= 2 && gy + dy < height - 2)
                                grid[gx + dx, gy + dy] = 0;
                        }
                    }
                }
            }

            // CA iterations
            for (int iter = 0; iter < caIterations; iter++)
            {
                grid = StepB678_S345678(grid, width, height);
            }

            // Connectivity
            var components = FindConnectedClearings(grid, width, height);
            if (components.Count > 0)
            {
                var mainComp = components[0];
                for (int i = 1; i < components.Count; i++)
                {
                    var comp = components[i];
                    if (comp.Count >= minClearingSize)
                    {
                        var repA = comp[comp.Count / 2];
                        int step = Math.Max(1, mainComp.Count / 40);
                        Vector2IntCoord bestB = mainComp[0];
                        int bestDist = int.MaxValue;

                        for (int k = 0; k < mainComp.Count; k += step)
                        {
                            var cand = mainComp[k];
                            int d2 = (cand.x - repA.x) * (cand.x - repA.x) + (cand.y - repA.y) * (cand.y - repA.y);
                            if (d2 < bestDist)
                            {
                                bestDist = d2;
                                bestB = cand;
                            }
                        }

                        var line = BresenhamLine(repA.x, repA.y, bestB.x, bestB.y);
                        foreach (var pt in line)
                        {
                            for (int dy = -1; dy <= 1; dy++)
                            {
                                for (int dx = -1; dx <= 1; dx++)
                                {
                                    int nx = pt.x + dx;
                                    int ny = pt.y + dy;
                                    if (nx >= 2 && nx < width - 2 && ny >= 2 && ny < height - 2)
                                        grid[nx, ny] = 0;
                                }
                            }
                        }
                        mainComp.AddRange(comp);
                    }
                    else
                    {
                        // Cull tiny orphans
                        foreach (var pt in comp)
                        {
                            grid[pt.x, pt.y] = 1;
                        }
                    }
                }
            }

            // Final safety pass
            var finalComps = FindConnectedClearings(grid, width, height);
            if (finalComps.Count > 1)
            {
                for (int i = 1; i < finalComps.Count; i++)
                {
                    foreach (var pt in finalComps[i])
                        grid[pt.x, pt.y] = 1;
                }
            }

            return grid;
        }

        public static int[,] ComputeDijkstra(int[,] grid, int width, int height, Vector2IntCoord start, out Vector2IntCoord farthest)
        {
            int[,] dist = new int[width, height];
            for (int y = 0; y < height; y++)
                for (int x = 0; x < width; x++)
                    dist[x, y] = -1;

            dist[start.x, start.y] = 0;
            var queue = new Queue<Vector2IntCoord>();
            queue.Enqueue(start);

            farthest = start;
            int maxD = 0;

            int[] dxs = { 1, -1, 0, 0 };
            int[] dys = { 0, 0, 1, -1 };

            while (queue.Count > 0)
            {
                var cur = queue.Dequeue();
                int cd = dist[cur.x, cur.y];

                if (cd > maxD)
                {
                    maxD = cd;
                    farthest = cur;
                }

                for (int d = 0; d < 4; d++)
                {
                    int nx = cur.x + dxs[d];
                    int ny = cur.y + dys[d];
                    if (nx >= 0 && nx < width && ny >= 0 && ny < height)
                    {
                        if (grid[nx, ny] == 0 && dist[nx, ny] == -1)
                        {
                            dist[nx, ny] = cd + 1;
                            queue.Enqueue(new Vector2IntCoord(nx, ny));
                        }
                    }
                }
            }

            return dist;
        }
    }
}
