using System;
using System.Text;

namespace AutumnProcGen.Core
{
    public static class HashUtils
    {
        public const ulong MASK64 = 0xFFFFFFFFFFFFFFFF;

        public static ulong RotL(ulong x, int k)
        {
            return (x << k) | (x >> (64 - k));
        }

        public static ulong SplitMix64(ulong x)
        {
            ulong z = x + 0x9E3779B97F4A7C15UL;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
            return z ^ (z >> 31);
        }

        public static ulong SeedToUInt64(string seed)
        {
            if (string.IsNullOrWhiteSpace(seed))
                seed = "KODTU2026";

            ulong h = 0xCBF29CE484222325UL;
            byte[] bytes = Encoding.UTF8.GetBytes(seed.Trim());
            for (int i = 0; i < bytes.Length; i++)
            {
                h ^= bytes[i];
                h *= 0x100000001B3UL;
            }
            return SplitMix64(h);
        }

        public static string FormatSeedCode(ulong seed)
        {
            ulong num = (seed % 9000UL) + 1000UL;
            string[] suffixes = { "FALL", "LEAF", "BARK", "MIST", "GOLD", "RUST", "PINE", "MOSS" };
            string suffix = suffixes[(seed >> 16) & 7];
            return $"KODTU-{num}-{suffix}";
        }
    }

    public class Mulberry32
    {
        private uint state;

        public Mulberry32(uint seed)
        {
            state = seed;
        }

        public uint NextUInt32()
        {
            state += 0x6D2B79F5u;
            uint t = state;
            t = (t ^ (t >> 15)) * (t | 1u);
            t ^= t + ((t ^ (t >> 7)) * (t | 61u));
            return t ^ (t >> 14);
        }

        public float Random()
        {
            return NextUInt32() / 4294967296.0f;
        }
    }

    public class Xoshiro256
    {
        private ulong s0, s1, s2, s3;
        public ulong SeedUInt64 { get; private set; }
        public string SeedCode { get; private set; }

        public Xoshiro256(string seed = "KODTU2026")
        {
            SeedUInt64 = HashUtils.SeedToUInt64(seed);
            SeedCode = HashUtils.FormatSeedCode(SeedUInt64);

            s0 = HashUtils.SplitMix64(SeedUInt64);
            s1 = HashUtils.SplitMix64(s0);
            s2 = HashUtils.SplitMix64(s1);
            s3 = HashUtils.SplitMix64(s2);

            if ((s0 | s1 | s2 | s3) == 0UL)
                s0 = 1UL;
        }

        public ulong NextUInt64()
        {
            ulong result = HashUtils.RotL(s1 * 5UL, 7) * 9UL;
            ulong t = s1 << 17;

            s2 ^= s0;
            s3 ^= s1;
            s1 ^= s2;
            s0 ^= s3;

            s2 ^= t;
            s3 = HashUtils.RotL(s3, 45);

            return result;
        }

        public float Random()
        {
            return (NextUInt64() >> 11) * (1.0f / (1UL << 53));
        }

        public float Uniform(float a, float b)
        {
            return a + (b - a) * Random();
        }

        public int Range(int minInclusive, int maxInclusive)
        {
            if (maxInclusive <= minInclusive)
                return minInclusive;
            ulong span = (ulong)(maxInclusive - minInclusive + 1);
            return minInclusive + (int)(NextUInt64() % span);
        }

        public T Choice<T>(T[] array)
        {
            if (array == null || array.Length == 0)
                return default;
            return array[Range(0, array.Length - 1)];
        }

        public void Shuffle<T>(T[] array)
        {
            for (int i = array.Length - 1; i > 0; i--)
            {
                int j = Range(0, i);
                T temp = array[i];
                array[i] = array[j];
                array[j] = temp;
            }
        }
    }
}
