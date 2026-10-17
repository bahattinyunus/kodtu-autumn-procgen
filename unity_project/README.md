# 🍁 KODTÜ × ODTÜ: Autumn ProcGen Engine (Unity 2D Port)

Bu klasör, **KODTÜ: Autumn ProcGen Engine** oyununun Unity 6 (URP 2D) için tam teşekküllü C# portunu içerir.

---

## 🎮 Unity Hub ile Nasıl Açılır ve Çalıştırılır?

1. **Unity Hub'ı Açın.**
2. **Projects** sekmesinden **`Add`** (veya **`Add project from disk`**) butonuna tıklayın.
3. Şu klasörü seçin:
   ```text
   kodtu-autumn-procgen\unity_project
   ```
4. Editör sürümü olarak sisteminizde kurulu olan **Unity 6 (`6000.6.6f1`)** veya üzeri bir sürümü seçerek projeyi açın.
5. Proje ilk açıldığında paketleri ve varlıkları otomatik olarak derleyecektir.
6. Üst menü çubuğundan:
   ```text
   Tools -> KODTÜ Autumn -> 1. Setup Game Scene (Hazır Sahneyi Kur)
   ```
   seçeneğine bir kez tıklayın. Sahne, Tilemap'ler, Kamera ve Dünya Yöneticisi (`AutumnWorldManager`) anında kurulacaktır.
7. Editörün üstündeki **`▶ Play`** butonuna basın!

---

## 🕹️ Kontroller (Oynanış)

- **`W, A, S, D` veya Yön Tuşları:** Bozkırda hareket et.
- **`Sol Shift`:** Depar (Sprint) — Dayanıklılık (Stamina) tüketir.
- **`Space` veya Sol Tık:** Solar Ember / Kılıç Savurması (Düşman gölgelerine saldır).
- **`E` Tuşu:** Etkileşim:
  - 🗿 **ODTÜ Tarih Kitabeleri:** Kadim yazıtları oku, fenerini ısıt (`+15 Isı`), ilham hızı kazan.
  - 🔥 **Kamp Ateşi:** Isın, canını yenile, dinlen.
  - 🐾 **Bozkır Kangalı:** Sadık kampüs dostunu sev.
  - ✦ **Bilim Ağacı Anıtı:** Zafer meşalesini yak ve oyunu tamamla.
- **`Esc` veya `E`:** Kitabe diyalog penceresini kapat.

---

## 📦 Mimari ve Dosya Yapısı

- `Assets/Scripts/ProcGen/`: 6-aşamalı deterministik harita üretim hattı (Xoshiro256**, 2B Simplex fBm, B678/S345678 Hücresel Otomata, Bridson Poisson Disk, 47-Blob Autotile).
- `Assets/Scripts/Entities/`: Oyuncu kontrolcüsü (`PlayerController.cs`), Düşman yapay zekası (`EnemyAI.cs`), Etkileşimler (`InteractiveObject.cs`), Mermiler (`Projectile.cs`).
- `Assets/Scripts/World/`: `AutumnWorldManager.cs` — Tilemap'leri prosedürel olarak döşeyen, varlıkları ve savrulan yaprak parçacıklarını oluşturan ana yönetici.
- `Assets/Scripts/Core/`: 16-Renk Sonbahar Paleti (`AutumnPalette.cs`), Ses Yöneticisi (`AudioManager.cs`), ODTÜ Kitabe ve Başarım Verileri (`StoryData.cs`).
- `Assets/Scripts/UI/`: Modern HUD, Can/Isı/Stamina barları, daktilo efektli Kitabe okuma modalı (`AutumnHUD.cs`).
- `Assets/Editor/`: Tek tıkla sahne kurucu (`AutumnSceneSetup.cs`) ve piksel-kusursuz sprite içe aktarıcı (`PixelArtImporter.cs`).
- `Assets/Resources/`: Çalışma anında anında yüklenen tüm piksel sprite'ları ve sentezlenmiş WAV ses efektleri.
