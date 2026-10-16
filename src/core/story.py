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
        "BÖLÜM I : YALINCAK VE BOZKIRIN ENTROPİSİ",
        "Her dökülen yaprak, doğanın kaçınılmaz entropisine karşı bir veda değil; toprağa bırakılmış bir vaattir. "
        "1956'da ellerle dikilen bu orman, insanın tabiatla kurduğu en derin diyalogdur. "
        "Fenerindeki köz, sadece karanlığı delmekle kalmaz; unuttuğun köklerini ve yarım kalmış hatıraları aydınlatır.",
        "Görev: Yalıncak patikasında dağılmış 5 Varlık Hatırasını topla ve Kadim Tapınakta [E] döngüyü başlat.",
    ),
    2: (
        "BÖLÜM II : EYMİR'İN DİNGİNLİĞİ VE ZAMANIN AKIŞI",
        "Su akar, sis çöker, yaprak çürür; fakat bilgi ve hafıza asla yok olmaz. Eymir'in dingin kıyılarında "
        "yankılanan fısıltılar sana şunu hatırlatır: 'Karanlık, ışığın yokluğu değil; henüz yakılmamış bir meşaledir.' "
        "Korkularını gölgelere fırlat, fenerinin sıcaklığıyla gölün sakladığı felsefi hakikati çöz.",
        "Görev: Eymir'in sisli sularındaki 5 Hatırayı birleştir ve gölge kürelerini erdemle geri yansıt.",
    ),
    3: (
        "BÖLÜM III : DEVRİM KORUSU VE EBEDİ DÖNGÜ (OUROBOROS)",
        "Sonbahar bir son değil, dirilişin sessiz eşiğidir. Devrim basamaklarında yükselen 'Devrim', doğanın "
        "kendini durmaksızın yenileyen devrimci iradesidir. Ormanın Kadim Bekçisiyle yüzleşirken anla ki: "
        "Sen ormanda yürüyen bir yabancı değilsin; sen ormanın ta kendisisin, düşen yaprağın ve yanan közün kardeşisin.",
        "Görev: Son 5 Bilgelik Hatırasını mühürle, Orman Bekçisinin sınavını geç ve Sonbahar Kalbini ebediyete ada.",
    ),
}

RELIC_STORY_FRAGMENTS: List[Tuple[str, str, str]] = [
    (
        "VAROLUŞUN İLK KIVILCIMI (Anı 1/5)",
        "Bozkırın ortasında bir avuç gencin diktiği ilk fidan fısıldıyor: "
        "'Umut, en çorak toprakta bile bir tohumun çatlamaya cüret etmesidir.' Fenerin felsefi bir dinginlikle ışıdı.",
        "bilim_agaci",
    ),
    (
        "KABULLENİŞ VE DÖKÜLEN YAPRAKLAR (Anı 2/5)",
        "Sarı huş yaprağı dalından koparken korkmuyor; çünkü toprağa karışmanın, yeniden doğmanın ilk adımı olduğunu biliyor. "
        "'Geçicilik, varlığa anlam katan tek hakikattir.' [Ruhsal Dinginlik & Hız +%18]",
        "relic",
    ),
    (
        "SİSLER ARASINDAKİ AYNA (Anı 3/5)",
        "Eymir'in yüzeyinde kendi aksini değil, bu ormanı var eden binlerce insanın ortak vicdanını görüyorsun. "
        "'Birey bir damladır; dayanışma ise gölün ta kendisidir.' Fenerin gölün duruluğuyla parladı.",
        "bilim_agaci",
    ),
    (
        "DİRENİŞ VE DEVRİM MEŞALESİ (Anı 4/5)",
        "Devrim basamaklarına kazınan miras konuşuyor: 'Dünyayı değiştirmek, önce kendi içindeki karanlığa köz taşımakla başlar.' "
        "Solar Ember mermilerin artık tek bir kıvılcım değil, kolektif bir hakikat meşalesidir!",
        "player",
    ),
    (
        "EBEDİ DÖNGÜ: SONBAHARIN SON IŞIĞI (Anı 5/5)",
        "Tüm parçalar tamamlandı. Ölüm ve yaşam, düşüş ve yükseliş, bozkır ve orman tek bir ahenkte birleşti. "
        "Artık Kadim Tapınağa [E] git; fenerindeki ışık artık sadece sana değil, tüm geleceğe aittir.",
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
            title="AKIL VE BOZKIRIN DİYALEKTİĞİ",
            text="'1956'dan beri bozkırdan göğe uzanan bu anıt der ki: Ağaç dikmek, zamana karşı verilmiş en saf meydan okumadır. "
            "Bilgiyle tutuşan meşale üşüyen fenerini ısıtır; akıl doğayı tüketmek için değil, onunla nefes almak içindir.' (+15 Isı/sn)",
            duration=6.8,
            accent_type="birch",
            avatar_key="bilim_agaci",
            once_key="bilim_agaci_intro",
        )

    def on_near_campfire(self) -> None:
        self.trigger_dialogue(
            speaker="ORMANCI KAMP ATEŞİ",
            title="SOLUKLANMA VE GEÇİCİLİK",
            text="'Ateş yanar, kül olur, sonra toprağa döner. Yolcu dinlenir, fenerini ısıtır, sonra tekrar yürür. "
            "Bu durağın kıymetini bil; çünkü her mola, fırtınaya karşı toplanan yeni bir cesarettir.' (+9 Isı/sn)",
            duration=5.8,
            accent_type="gold",
            avatar_key="campfire",
            once_key="campfire_intro",
        )

    def on_boss_encounter(self) -> None:
        self.trigger_dialogue(
            speaker="KADİM GEYİK (ELDER STAG WARDEN)",
            title="TABİATIN İÇSEL SINAVI",
            text="'Bozkırın kış uykusu yaklaşırken seni durdurmak için değil, ışığını tartmak için buradayım! "
            "Karanlığı düşman belleme; kılıcınla gölge kürelerimi yansıt ve zıttınla ahenk içinde dans etmeyi öğren!'",
            duration=7.0,
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
