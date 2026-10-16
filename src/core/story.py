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
    duration: float = 7.0
    accent_type: str = "gold"  # 'gold', 'birch', 'crimson'
    avatar_key: str = "player"  # 'bilim_agaci', 'relic', 'campfire', 'player', 'warden'
    chars_revealed: int = 0
    typewriter_speed: float = 45.0  # characters per second


CHAPTER_INFO: Dict[int, Tuple[str, str, str]] = {
    1: (
        "BÖLÜM I : YALINCAK YAPRAK YOLU",
        "1956'dan beri bozkırdan ellerle yeşertilen ulu ODTÜ ormanına ansızın dondurucu bir alacakaranlık sisi çöktü. "
        "Yalıncak patikasında yapraklar hızla dökülürken, Bilim Ağacı'nın kadim meşalesinden aldığın köz feneriyle "
        "ormanın dağılmış 5 Sonbahar Hatırasını topla ve tapınağı uyandır.",
        "Görev: 5 Sonbahar Hatırası Kristalini topla, fenerini sıcak tut ve Kadim Tapınağa [E] ulaş.",
    ),
    2: (
        "BÖLÜM II : EYMİR'İN SİSLİ KIYILARI",
        "İlk korunun yaprakları ısındı! Şimdi Eymir Gölü'nün bataklık sazlıklarına ve prosedürel ahşap iskelelerine "
        "inme vakti. Suyun üzerinde asılı kalan alacakaranlık fısıltılarına kulak ver; gölgeler soğuk üflerken "
        "sadece köz fenerinin ışığı göl kıyısındaki kadim bilgiyi koruyabilir.",
        "Görev: Eymir'in sisli kıyılarındaki 5 Sonbahar Hatırasını bul ve karanlık orbları yansıtarak tapınağı aç.",
    ),
    3: (
        "BÖLÜM III : DEVRİM KORUSU VE SONBAHAR KALBİ",
        "Devrim Stadyumu'nun çam ve meşe korusuna ulaştın! Ormanın en kadim bekçisi Elder Stag Warden ve gölge ordusu, "
        "Sonbaharın Son Işığı'nı bozkır ayazına hapsetmek üzere. Fenerinin tüm kutsamalarını birleştir, "
        "son anıları mühürle ve ebedi sonbahar ahengini tüm kampüse geri kazandır!",
        "Görev: Devrim Korusu'ndaki son 5 hatırayı birleştir, Orman Bekçisiyle yüzleş ve Sonbahar Kalbini yak.",
    ),
}

RELIC_STORY_FRAGMENTS: List[Tuple[str, str, str]] = [
    (
        "İLK TOHUMUN HATIRASI (Anı 1/5)",
        "1956 güzünde bozkır rüzgarına emanet edilen ilk meşe palamudunun anısı... "
        "'Bir fidan bin inançtır.' Fenerinin alevi pas rengi kıvılcımlarla parıldadı!",
        "bilim_agaci",
    ),
    (
        "YALINCAK RÜZGARININ TÜRKÜSÜ (Anı 2/5)",
        "Altın huş yapraklarının savrulurken söylediği eski bir öğrenci marşı kulaklarında yankılandı: "
        "'Bu orman teslim olmaz, her sonbahar yeni bir bahara gebe kalır!' [Hız +%18]",
        "relic",
    ),
    (
        "EYMİR SİSİ VE BİLİM MEŞALESİ (Anı 3/5)",
        "Göl yüzeyindeki kehribar rengi sabah buğusu, fenerinin çatlaklarını güneş ısıyla doldurdu. "
        "Gölün derinliklerindeki su nilüferleri altın köz saçarak seni selamladı.",
        "bilim_agaci",
    ),
    (
        "DEVRİM STADYUMU KIVILCIMI (Anı 4/5)",
        "Tarihin taşa ve çime kazındığı basamaklardan yükselen sönmeyen inanç dalgası! "
        "Fenerinden fırlayan Solar Ember mermileri artık 3'lü yaylım halinde gölgeleri yarıyor!",
        "player",
    ),
    (
        "SONBAHARIN SON IŞIĞI (Anı 5/5)",
        "Tüm parçalar birleşti! ODTÜ ormanının bozkıra karşı verdiği yarım asırlık direniş fenerinde vücut buldu. "
        "Artık Kadim Tapınağa [E] dön ve yeni korunun gizemli geçidini sonsuzluğa aç!",
        "relic",
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
        avatar_key: str = "player",
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
            avatar_key=avatar_key,
            chars_revealed=0,
        )
        self.dialogue_timer = duration

    def on_relic_collected(self, current_count: int, total_count: int, boon_title: Optional[str] = None) -> None:
        idx = max(0, min(len(RELIC_STORY_FRAGMENTS) - 1, current_count - 1))
        frag_title, frag_text, avatar = RELIC_STORY_FRAGMENTS[idx]
        if boon_title:
            frag_text += f" [Yeni ODTÜ Kutsaması: {boon_title}]"
        self.trigger_dialogue(
            speaker=f"SONBAHAR HATIRASI ({current_count}/{total_count})",
            title=frag_title,
            text=frag_text,
            duration=7.2,
            accent_type="birch" if current_count >= total_count else "gold",
            avatar_key=avatar,
        )

    def on_near_bilim_agaci(self) -> None:
        self.trigger_dialogue(
            speaker="ODTÜ BİLİM AĞACI ANITI",
            title="SÖNMEYEN BİLİM MEŞALESİ",
            text="'1956'dan beri bozkırdan yükselen bu orman, her sonbaharda küllerinden yeniden doğar. "
            "Fenerin üşüdüğünde yanıma gel; bilgi ve dayanışmanın meşalesi fenerini koruyacaktır.' (+15 Isı/sn)",
            duration=6.5,
            accent_type="birch",
            avatar_key="bilim_agaci",
            once_key="bilim_agaci_intro",
        )

    def on_near_campfire(self) -> None:
        self.trigger_dialogue(
            speaker="ORMANCI KAMP ATEŞİ",
            title="SICAK KÖZ DURAĞI",
            text="Çıtırdayan kestane dalları ve meşe kökleri fenerinin ısısını tazeliyor. "
            "Yalıncak ve Eymir yollarında ilerlemeden önce soluklanmak için güvenli bir sığınak.",
            duration=5.5,
            accent_type="gold",
            avatar_key="campfire",
            once_key="campfire_intro",
        )

    def on_boss_encounter(self) -> None:
        self.trigger_dialogue(
            speaker="KADİM GEYİK (ELDER STAG WARDEN)",
            title="ORMANIN KORUYUCU RUHU",
            text="'Bozkırın kış uykusu yaklaşırken közünü söndürmeyeceğim, onu sınayacağım! "
            "Kılıcınla gölge kürelerimi yansıt ve sonbaharın ışığına layık olduğunu kanıtla!'",
            duration=6.8,
            accent_type="crimson",
            avatar_key="warden",
            once_key="boss_encounter",
        )

    def get_current_objective_text(self, relics_collected: int, total_relics: int) -> str:
        if relics_collected >= total_relics:
            return "GÖREV: Tüm Hatıralar Toplandı! Pusulayı takip et ve Kadim Tapınakta [E] ile yeni koruyu aç."
        rem = total_relics - relics_collected
        return f"GÖREV: Ormandaki Sonbahar Hatıralarını Topla ({relics_collected}/{total_relics}) — Kalan: {rem}"

    def update(self, dt: float) -> bool:
        """Updates dialogue timers and typewriter progression. Returns True if a character was revealed this tick."""
        revealed_char = False
        if self.dialogue_timer > 0.0:
            self.dialogue_timer = max(0.0, self.dialogue_timer - dt)
            if self.active_dialogue is not None:
                # Progressive typewriter reveal
                tot_chars = len(self.active_dialogue.text)
                if self.active_dialogue.chars_revealed < tot_chars:
                    add = max(1, int(round(self.active_dialogue.typewriter_speed * dt)))
                    old_chars = self.active_dialogue.chars_revealed
                    self.active_dialogue.chars_revealed = min(
                        tot_chars, self.active_dialogue.chars_revealed + add
                    )
                    if self.active_dialogue.chars_revealed > old_chars:
                        revealed_char = True
            if self.dialogue_timer <= 0.0:
                self.active_dialogue = None
        return revealed_char
