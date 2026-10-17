using System;
using System.Collections.Generic;

namespace AutumnProcGen.ProcGen
{
    public static class AutotileMasks
    {
        public const int BIT_NW = 1;
        public const int BIT_N  = 2;
        public const int BIT_NE = 4;
        public const int BIT_W  = 8;
        public const int BIT_E  = 16;
        public const int BIT_SW = 32;
        public const int BIT_S  = 64;
        public const int BIT_SE = 128;

        public static readonly int[] Canonical47Masks;
        public static readonly Dictionary<int, int> MaskTo47Index;
        public static readonly int[] RawTo47LUT;

        static AutotileMasks()
        {
            var uniqueMasks = new HashSet<int>();
            for (int m = 0; m < 256; m++)
            {
                uniqueMasks.Add(SanitizeBlobMask(m));
            }

            var list = new List<int>(uniqueMasks);
            list.Sort();
            Canonical47Masks = list.ToArray();

            MaskTo47Index = new Dictionary<int, int>();
            for (int i = 0; i < Canonical47Masks.Length; i++)
            {
                MaskTo47Index[Canonical47Masks[i]] = i;
            }

            RawTo47LUT = new int[256];
            for (int m = 0; m < 256; m++)
            {
                int sanitized = SanitizeBlobMask(m);
                RawTo47LUT[m] = MaskTo47Index[sanitized];
            }
        }

        public static int SanitizeBlobMask(int rawMask)
        {
            int mask = rawMask & 0xFF;
            if ((mask & BIT_N) == 0 || (mask & BIT_W) == 0) mask &= ~BIT_NW;
            if ((mask & BIT_N) == 0 || (mask & BIT_E) == 0) mask &= ~BIT_NE;
            if ((mask & BIT_S) == 0 || (mask & BIT_W) == 0) mask &= ~BIT_SW;
            if ((mask & BIT_S) == 0 || (mask & BIT_E) == 0) mask &= ~BIT_SE;
            return mask;
        }

        public static int CalculateBlobIndex(int[,] grid, int x, int y, int width, int height, int targetValue = 1)
        {
            int rawMask = 0;
            // NW
            if (IsMatch(grid, x - 1, y + 1, width, height, targetValue)) rawMask |= BIT_NW;
            // N
            if (IsMatch(grid, x, y + 1, width, height, targetValue))     rawMask |= BIT_N;
            // NE
            if (IsMatch(grid, x + 1, y + 1, width, height, targetValue)) rawMask |= BIT_NE;
            // W
            if (IsMatch(grid, x - 1, y, width, height, targetValue))     rawMask |= BIT_W;
            // E
            if (IsMatch(grid, x + 1, y, width, height, targetValue))     rawMask |= BIT_E;
            // SW
            if (IsMatch(grid, x - 1, y - 1, width, height, targetValue)) rawMask |= BIT_SW;
            // S
            if (IsMatch(grid, x, y - 1, width, height, targetValue))     rawMask |= BIT_S;
            // SE
            if (IsMatch(grid, x + 1, y - 1, width, height, targetValue)) rawMask |= BIT_SE;

            return RawTo47LUT[rawMask];
        }

        private static bool IsMatch(int[,] grid, int x, int y, int width, int height, int targetValue)
        {
            if (x < 0 || x >= width || y < 0 || y >= height)
                return true; // Treat edges as solid/target
            return grid[x, y] == targetValue;
        }
    }
}
