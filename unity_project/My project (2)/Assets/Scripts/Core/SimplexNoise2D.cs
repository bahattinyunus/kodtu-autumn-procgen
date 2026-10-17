using System;
using UnityEngine;

namespace AutumnProcGen.Core
{
    public class SimplexNoise2D
    {
        private static readonly float[][] GRAD2 = new float[][]
        {
            new float[]{ 1.0f, 1.0f },
            new float[]{ -1.0f, 1.0f },
            new float[]{ 1.0f, -1.0f },
            new float[]{ -1.0f, -1.0f },
            new float[]{ 1.0f, 0.0f },
            new float[]{ -1.0f, 0.0f },
            new float[]{ 0.0f, 1.0f },
            new float[]{ 0.0f, -1.0f },
            new float[]{ 0.8660254f, 0.5f },
            new float[]{ -0.8660254f, 0.5f },
            new float[]{ 0.8660254f, -0.5f },
            new float[]{ -0.8660254f, -0.5f }
        };

        private static readonly float F2 = 0.5f * (Mathf.Sqrt(3.0f) - 1.0f);
        private static readonly float G2 = (3.0f - Mathf.Sqrt(3.0f)) / 6.0f;

        private readonly int[] perm = new int[512];
        private readonly int[] permMod12 = new int[512];

        public SimplexNoise2D(Xoshiro256 rng)
        {
            int[] basePerm = new int[256];
            for (int i = 0; i < 256; i++)
                basePerm[i] = i;

            rng.Shuffle(basePerm);

            for (int i = 0; i < 256; i++)
            {
                perm[i] = basePerm[i];
                perm[i + 256] = basePerm[i];
                permMod12[i] = basePerm[i] % 12;
                permMod12[i + 256] = basePerm[i] % 12;
            }
        }

        public float Sample(float x, float y)
        {
            float s = (x + y) * F2;
            int i = Mathf.FloorToInt(x + s);
            int j = Mathf.FloorToInt(y + s);
            float t = (i + j) * G2;
            float X0 = i - t;
            float Y0 = j - t;
            float x0 = x - X0;
            float y0 = y - Y0;

            int i1, j1;
            if (x0 > y0) { i1 = 1; j1 = 0; }
            else { i1 = 0; j1 = 1; }

            float x1 = x0 - i1 + G2;
            float y1 = y0 - j1 + G2;
            float x2 = x0 - 1.0f + 2.0f * G2;
            float y2 = y0 - 1.0f + 2.0f * G2;

            int ii = i & 255;
            int jj = j & 255;

            int gi0 = permMod12[ii + perm[jj]];
            int gi1 = permMod12[ii + i1 + perm[jj + j1]];
            int gi2 = permMod12[ii + 1 + perm[jj + 1]];

            float n0 = 0.0f;
            float t0 = 0.5f - x0 * x0 - y0 * y0;
            if (t0 >= 0.0f)
            {
                t0 *= t0;
                float[] g0 = GRAD2[gi0];
                n0 = t0 * t0 * (g0[0] * x0 + g0[1] * y0);
            }

            float n1 = 0.0f;
            float t1 = 0.5f - x1 * x1 - y1 * y1;
            if (t1 >= 0.0f)
            {
                t1 *= t1;
                float[] g1 = GRAD2[gi1];
                n1 = t1 * t1 * (g1[0] * x1 + g1[1] * y1);
            }

            float n2 = 0.0f;
            float t2 = 0.5f - x2 * x2 - y2 * y2;
            if (t2 >= 0.0f)
            {
                t2 *= t2;
                float[] g2 = GRAD2[gi2];
                n2 = t2 * t2 * (g2[0] * x2 + g2[1] * y2);
            }

            return 70.0f * (n0 + n1 + n2);
        }

        public float SampleFbm(float x, float y, int octaves = 4, float lacunarity = 2.0f, float persistence = 0.5f)
        {
            float total = 0.0f;
            float frequency = 1.0f;
            float amplitude = 1.0f;
            float maxAmp = 0.0f;

            for (int i = 0; i < octaves; i++)
            {
                total += Sample(x * frequency, y * frequency) * amplitude;
                maxAmp += amplitude;
                frequency *= lacunarity;
                amplitude *= persistence;
            }

            return total / maxAmp;
        }
    }
}
