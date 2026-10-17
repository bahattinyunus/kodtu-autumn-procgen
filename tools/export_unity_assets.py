"""
Exports all procedural pixel-art assets and synthesized audio to the Unity project Assets folder.
"""

import os
from pathlib import Path
import shutil
import numpy as np
from PIL import Image

# Ensure project root is in sys.path
import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.core.palette import AUTUMN_16_PALETTE, AUTUMN_16_HEX
from src.core.asset_builder import (
    _render_single_blob_tile,
    _build_floor_tiles,
    _build_tree_sprite,
    _build_small_prop_sprite,
    _build_player_frame,
    _build_entity_sprite,
    _build_campfire_sprite,
    _build_spring_sprite,
    _build_boardwalk_sprite,
    _build_bilim_agaci_sprite,
    _build_kitabe_sprite,
    _build_shrine_sprite,
)
from src.procgen.autotile import CANONICAL_47_MASKS


def export_assets_for_unity(unity_assets_dir: Path):
    print(f"Exporting assets to Unity directory: {unity_assets_dir}")
    
    sprites_dir = unity_assets_dir / "Sprites"
    audio_dir = unity_assets_dir / "Audio"
    palette_dir = unity_assets_dir / "Palettes"

    os.makedirs(sprites_dir / "Tiles", exist_ok=True)
    os.makedirs(sprites_dir / "Trees", exist_ok=True)
    os.makedirs(sprites_dir / "Props", exist_ok=True)
    os.makedirs(sprites_dir / "Player", exist_ok=True)
    os.makedirs(sprites_dir / "Entities", exist_ok=True)
    os.makedirs(sprites_dir / "Structures", exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(palette_dir, exist_ok=True)

    # 1. 47 Canonical Autotile Tiles
    print("Exporting 47 Autotiles...")
    for idx, mask in enumerate(CANONICAL_47_MASKS):
        arr = _render_single_blob_tile(mask, idx)
        img = Image.fromarray(arr, mode="RGBA")
        img.save(sprites_dir / "Tiles" / f"autotile_{idx:02d}.png")

    # 2. Floor Tiles
    print("Exporting Floor Tiles...")
    floor_arrays = _build_floor_tiles()
    biome_names = ["damp", "amber", "golden"]
    for b_idx, b_name in enumerate(biome_names):
        for var in range(4):
            arr = floor_arrays[b_idx * 4 + var]
            img = Image.fromarray(arr, mode="RGBA")
            img.save(sprites_dir / "Tiles" / f"floor_{b_name}_{var}.png")

    # 3. Trees (Maple, Birch, Oak)
    print("Exporting Trees...")
    for tkind in ("tree_maple", "tree_birch", "tree_oak"):
        for var in range(3):
            arr = _build_tree_sprite(tkind, var)
            img = Image.fromarray(arr, mode="RGBA")
            img.save(sprites_dir / "Trees" / f"{tkind}_{var}.png")

    # 4. Small Props
    print("Exporting Props...")
    for pkind in ("leaf_pile", "bush_amber", "mushroom", "log", "stone"):
        for var in range(3):
            arr = _build_small_prop_sprite(pkind, var)
            img = Image.fromarray(arr, mode="RGBA")
            img.save(sprites_dir / "Props" / f"{pkind}_{var}.png")

    # 5. Player Frames
    print("Exporting Player Sprites...")
    for f in range(3):
        arr = _build_player_frame(f)
        img = Image.fromarray(arr, mode="RGBA")
        img.save(sprites_dir / "Player" / f"player_frame_{f}.png")

    # 6. Entities & Monsters
    print("Exporting Entities...")
    for ekind in ("relic", "acorn", "wisp", "stalker", "wolf", "golem", "warden", "raven", "companion"):
        for f in range(2):
            arr = _build_entity_sprite(ekind, f)
            img = Image.fromarray(arr, mode="RGBA")
            img.save(sprites_dir / "Entities" / f"{ekind}_{f}.png")

    # 7. Structures & Monuments
    print("Exporting Structures...")
    for f in range(2):
        img = Image.fromarray(_build_campfire_sprite(f), mode="RGBA")
        img.save(sprites_dir / "Structures" / f"campfire_{f}.png")
        
        img = Image.fromarray(_build_spring_sprite(f), mode="RGBA")
        img.save(sprites_dir / "Structures" / f"spring_{f}.png")

    Image.fromarray(_build_boardwalk_sprite(), mode="RGBA").save(sprites_dir / "Structures" / "boardwalk.png")
    Image.fromarray(_build_bilim_agaci_sprite(), mode="RGBA").save(sprites_dir / "Structures" / "bilim_agaci.png")
    Image.fromarray(_build_kitabe_sprite(), mode="RGBA").save(sprites_dir / "Structures" / "kitabe.png")
    Image.fromarray(_build_shrine_sprite(False), mode="RGBA").save(sprites_dir / "Structures" / "shrine_dormant.png")
    Image.fromarray(_build_shrine_sprite(True), mode="RGBA").save(sprites_dir / "Structures" / "shrine_awake.png")

    # 8. Copy Audio files
    print("Copying synthesized Audio effects...")
    src_audio = ROOT_DIR / "assets" / "audio"
    if src_audio.exists():
        for wav_file in src_audio.glob("*.wav"):
            shutil.copy2(wav_file, audio_dir / wav_file.name)

    # 9. Copy Palette
    print("Copying Palette...")
    src_palettes = ROOT_DIR / "assets" / "palettes"
    if src_palettes.exists():
        for f in src_palettes.glob("*"):
            shutil.copy2(f, palette_dir / f.name)

    print("Successfully exported all assets to Unity!")


if __name__ == "__main__":
    target = ROOT_DIR / "unity_project" / "Assets"
    export_assets_for_unity(target)
