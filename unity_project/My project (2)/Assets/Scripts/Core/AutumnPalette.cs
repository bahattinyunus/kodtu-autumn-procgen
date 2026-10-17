using System.Collections.Generic;
using UnityEngine;

namespace AutumnProcGen.Core
{
    /// <summary>
    /// KODTU Game Jam 16-Color Autumn Chromatic Spectrum (LUT).
    /// Pure pixel-art aesthetic colors.
    /// </summary>
    public static class AutumnPalette
    {
        public static readonly Color DeepVoid       = HexToColor("#1A1118");
        public static readonly Color PlumShadow     = HexToColor("#2D1B2D");
        public static readonly Color WitheredBark   = HexToColor("#4E222A");
        public static readonly Color MulberryDusk   = HexToColor("#6E2D3B");
        public static readonly Color DamsonMoss     = HexToColor("#433835");
        public static readonly Color CrimsonDecay   = HexToColor("#6E4438");
        public static readonly Color OchreClay      = HexToColor("#9A5338");
        public static readonly Color RustTerracotta = HexToColor("#B5592A");
        public static readonly Color CopperLeaf     = HexToColor("#9E472A");
        public static readonly Color BurntAmber     = HexToColor("#C86A2E");
        public static readonly Color HarvestGold    = HexToColor("#E09F3E");
        public static readonly Color MustardGlow    = HexToColor("#E5B14B");
        public static readonly Color SunlitBirch    = HexToColor("#F5D67B");
        public static readonly Color PaleSunbeam    = HexToColor("#FCEBB6");
        public static readonly Color SlateFog       = HexToColor("#888A8A");
        public static readonly Color AutumnMist     = HexToColor("#D4C8BE");

        public static readonly Color[] Palette16 = new Color[]
        {
            DeepVoid, PlumShadow, WitheredBark, MulberryDusk,
            DamsonMoss, CrimsonDecay, OchreClay, RustTerracotta,
            CopperLeaf, BurntAmber, HarvestGold, MustardGlow,
            SunlitBirch, PaleSunbeam, SlateFog, AutumnMist
        };

        public static Color HexToColor(string hex)
        {
            if (ColorUtility.TryParseHtmlString(hex, out Color col))
            {
                return col;
            }
            return Color.magenta;
        }

        public static Color FindNearestLutColor(Color src)
        {
            Color best = DeepVoid;
            float minDst = float.MaxValue;
            for (int i = 0; i < Palette16.Length; i++)
            {
                Color c = Palette16[i];
                float dr = (src.r - c.r) * 0.299f;
                float dg = (src.g - c.g) * 0.587f;
                float db = (src.b - c.b) * 0.114f;
                float dst = dr * dr + dg * dg + db * db;
                if (dst < minDst)
                {
                    minDst = dst;
                    best = c;
                }
            }
            return best;
        }
    }
}
