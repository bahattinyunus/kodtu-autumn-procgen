"""
Modern Narrative & Story Engine for KODTÜ: Autumn ProcGen.

Transforms the procedural autumn world into an accessible, heartfelt,
modern story-driven adventure ("ODTÜ: Sonbaharın Son Işığı") while preserving
all three KODTÜ constraints:
1. Art Style: Pixelated
2. Color Palette: Sonbahar (16-Color Autumn LUT)
3. Core Mechanic: Procedural Generation (Random Generation)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class DialogueEntry:
    """Represents a modern story dialogue box shown at the bottom of the HD screen."""

    speaker: str
    title: str
    text: str
    duration: float = 6.5
    accent_type: str = "gold"  # 'gold', 'birch', 'crimson'


CHAPTER_INFO: Dict[int, Tuple[str, str, str]] = {
    1: (
        "BÖLÜM I : YALINCAK YAPRAK YOLU",
        "Bozkır ayazı ODTÜ ormanına erken çöktü. Bilim Ağacı'nın meşalesinden aldığın "
        "ışıkla, her adımda yeniden şekillenen koruda kaybolmuş 5 Sonbahar Anısını bul.",
        "Görev: 5 Sonbahar Anısını (Kristal) topla ve Kadim Tapınağa [E] ulaş.",
    ),
    2: (
        "BÖLÜM II : EYMİR'İN SİSLİ KIYILARI",
        "İlk koru yeniden ısındı! Şimdi Eymir'in sisli sularına inen prosedürel patikaları "
        "ve ahşap köprüleri takip ederek unutulmuş hatıraları birleştir.",
        "Görev: Sisli kıyılardaki 5 Sonbahar Anısını topla ve Tapınağı uyandır.",
    ),
    3: (
        "BÖLÜM III : DEVRİM KORUSU VE SONBAHAR KALBİ",
        "Alacakaranlık muhafızları Kadim Tapınağın etrafında toplanıyor. Fenerinin "
        "sonbahar ateşiyle gölgeleri dağıt ve ODTÜ Ormanı'na sıcaklığı geri getir!",
        "Görev: Son 5 Sonbahar Anısını topla ve Sonbahar Kalbini mühürle.",
    ),
}

RELIC_STORY_FRAGMENTS: List[Tuple[str, str]] = [
    (
        "İLK TOHUMUN HATIRASI (Anı 1/5)",
        "1960'ların bozkırında toprağa düşen ilk fidanın yaprağı... Fenerin daha parlak yanıyor!",
    ),
    (
        "YALINCAK RÜZGARININ MELODİSİ (Anı 2/5)",
        "Sarı huş yapraklarının rüzgarda fısıldadığı eski bir öğrenci türküsü yankılandı.",
    ),
    (
        "EYMİR SABAH SİSİ (Anı 3/5)",
        "Göl yüzeyinden yükselen kehribar rengi sabah buğusu, fenerinin çatlaklarını onardı.",
    ),
    (
        "DEVRİM MEŞALESİNİN KIVILCIMI (Anı 4/5)",
        "Stadyum basamaklarında yankılanan coşku, karanlık orman gölgelerini geri püskürttü!",
    ),
    (
        "SONBAHARIN SON IŞIĞI (Anı 5/5)",
        "Tüm Sonbahar Anıları birleşti! Artık Kadim Tapınağa [E] giderek yeni korunun kapısını açabilirsin.",
    ),
]


class StoryManager:
    """
    Manages accessible, clear, story-driven progression, dialogue boxes,
    and current player objective prompts.
    """

    def __init__(self, show_intro_card: bool = False) -> None:
        self.chapter = 1
        self.show_intro_card = show_intro_card
        self.active_dialogue: Optional[DialogueEntry] = None
        self.dialogue_timer = 0.0
        self.seen_triggers: set[str] = set()

    def get_chapter_meta(self) -> tuple[str, str]:
        ch_key = min(3, max(1, self.chapter))
        title, text, _ = CHAPTER_INFO[ch_key]
        return title, text

    def start_chapter(self, depth_level: int, seed_code: str) -> None:
        self.chapter = depth_level
        self.seen_triggers.clear()
        title, story_text = self.get_chapter_meta()
        self.trigger_dialogue(
            speaker="ORMAN GÜNLÜĞÜ — " + seed_code,
            title=title,
            text=story_text,
            duration=7.0,
            accent_type="birch",
        )

    def trigger_dialogue(
        self,
        speaker: str,
        title: str,
        text: str,
        duration: float = 6.0,
        accent_type: str = "gold",
        once_key: Optional[str] = None,
    ) -> None:
        if once_key is not None:
            if once_key in self.seen_triggers:
                return
            self.seen_triggers.add(once_key)
        self.active_dialogue = DialogueEntry(
            speaker=speaker,
            title=title,
            text=text,
            duration=duration,
            accent_type=accent_type,
        )
        self.dialogue_timer = duration

    def on_relic_collected(self, current_count: int, total_count: int, boon_title: Optional[str] = None) -> None:
        idx = max(0, min(len(RELIC_STORY_FRAGMENTS) - 1, current_count - 1))
        frag_title, frag_text = RELIC_STORY_FRAGMENTS[idx]
        if boon_title:
            frag_text += f" [Yeni Kutsama: {boon_title}]"
        self.trigger_dialogue(
            speaker=f"SONBAHAR ANISI ({current_count}/{total_count})",
            title=frag_title,
            text=frag_text,
            duration=6.5,
            accent_type="birch" if current_count >= total_count else "gold",
        )

    def on_near_bilim_agaci(self) -> None:
        self.trigger_dialogue(
            speaker="ODTÜ BİLİM AĞACI ANITI",
            title="SÖNMEYEN BİLİM MEŞALESİ",
            text="'Bozkırdan yükselen bu orman, her sonbaharda küllerinden yeniden doğar. "
            "Fenerin üşüdüğünde yanıma gel, ışığım seni koruyacaktır.' (+15 Isı/sn)",
            duration=6.0,
            accent_type="birch",
            once_key="bilim_agaci_intro",
        )

    def on_near_campfire(self) -> None:
        self.trigger_dialogue(
            speaker="ORMANCI KAMP ATEŞİ",
            title="SICAK KÖZ DURAĞI",
            text="Çıtırdayan kestane dalları fenerinin ısısını yeniliyor. "
            "Yolculuğa devam etmeden önce soluklanmak için güvenli bir nokta.",
            duration=5.0,
            accent_type="gold",
            once_key="campfire_intro",
        )

    def get_current_objective_text(self, relics_collected: int, total_relics: int) -> str:
        if relics_collected >= total_relics:
            return "GÖREV: Tüm Anılar Toplandı! Pusulayı takip et ve Kadim Tapınakta [E] tuşuna bas."
        rem = total_relics - relics_collected
        return f"GÖREV: Ormandaki Sonbahar Anılarını Bul ({relics_collected}/{total_relics}) — Kalan: {rem}"

    def update(self, dt: float) -> None:
        if self.dialogue_timer > 0.0:
            self.dialogue_timer = max(0.0, self.dialogue_timer - dt)
            if self.dialogue_timer <= 0.0:
                self.active_dialogue = None
