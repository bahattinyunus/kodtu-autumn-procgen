#version 330 core
// KODTU Autumn ProcGen - 16-Color Sonbahar LUT Quantization & Hue-Shift Shader
in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_screen_tex;
uniform sampler2D u_autumn_lut; // 16x1 16-Color Sonbahar LUT
uniform float u_mist_density;

const vec3 DEEP_VOID = vec3(0.102, 0.067, 0.094);    // #1A1118
const vec3 SUNLIT_BIRCH = vec3(0.961, 0.839, 0.482); // #F5D67B
const vec3 AUTUMN_MIST = vec3(0.831, 0.784, 0.745);  // #D4C8BE

void main() {
    vec4 src = texture(u_screen_tex, v_texcoord);
    vec3 col = mix(src.rgb, AUTUMN_MIST, clamp(u_mist_density, 0.0, 0.35));

    // Find nearest neighbor in the 16-Color Sonbahar LUT
    vec3 best_col = DEEP_VOID;
    float min_dist = 999.0;
    for (int i = 0; i < 16; ++i) {
        vec3 lut_col = texelFetch(u_autumn_lut, ivec2(i, 0), 0).rgb;
        vec3 diff = col - lut_col;
        // Perceptual RGB weighting
        float d = dot(diff * diff, vec3(0.299, 0.587, 0.114));
        if (d < min_dist) {
            min_dist = d;
            best_col = lut_col;
        }
    }
    frag_color = vec4(best_col, src.a);
}
