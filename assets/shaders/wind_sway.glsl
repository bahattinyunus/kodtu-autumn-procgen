#version 330 core
// KODTU Autumn ProcGen - Pixel-Snapped Foliage Wind Sway & Mist Shader
in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_sprite_tex;
uniform float u_time;
uniform vec2 u_wind_vec;
uniform vec2 u_tex_size;

void main() {
    // Upper canopy sways with sinusoidal wind while trunk base stays anchored
    float height_factor = clamp(1.0 - v_texcoord.y, 0.0, 1.0);
    float sway_px = round(sin(u_time * 3.2 + v_texcoord.y * 4.0) * u_wind_vec.x * height_factor);
    vec2 snapped_uv = (floor(v_texcoord * u_tex_size + vec2(sway_px, 0.0)) + 0.5) / u_tex_size;
    frag_color = texture(u_sprite_tex, clamp(snapped_uv, 0.0, 1.0));
}
