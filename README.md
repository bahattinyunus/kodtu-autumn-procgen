<div align="center">

<img src="docs/banners/hero_odtu_kodtu_banner.png" alt="KODTÜ x ODTÜ: Autumn ProcGen Engine Hero Banner" width="100%" />

<br />

# 🍁 KODTÜ × ODTÜ: Autumn ProcGen Engine

### **Orta Doğu Teknik Üniversitesi (ODTÜ / METU) — KODTÜ Game Jam Teknik Başyapıtı**
*16-Bit Piksel-Kusursuz Sonbahar Ekosistemi, Deterministik 6 Aşamalı Prosedürel İçerik Üretimi (PCG) ve Gerçek Zamanlı Verlet Yaprak Fiziği Motoru*

[![Jam: KODTÜ @ ODTÜ](https://img.shields.io/badge/ODT%C3%9C_%2F_METU-KODT%C3%9C_Game_Jam-9E472A?style=for-the-badge&labelColor=1A1118)](#)
[![Art Style: Pixelated](https://img.shields.io/badge/Art_Style-Pixelated_16--Bit_(320x180)-E09F3E?style=for-the-badge&labelColor=1A1118)](#-piksel-kusursuz-pixel-perfect-g%C3%B6rsel-m%C3%BChendislik)
[![Palette: Sonbahar](https://img.shields.io/badge/Renk_Paleti-16--Color_Sonbahar_LUT-F5D67B?style=for-the-badge&labelColor=1A1118)](#-sonbahar-renk-kuram%C4%B1-hue-shifted-autumn-lut)
[![Mechanic: Procedural Generation](https://img.shields.io/badge/Mekanik-6--Stage_Deterministic_PCG-B5592A?style=for-the-badge&labelColor=1A1118)](#-deterministik-prosed%C3%BCrel-%C3%BCretim-mimarisi-pcg-pipeline)
[![Modern UI: 1280x720 HD Story](https://img.shields.io/badge/UI-Modern_1280x720_Story_Overlay-9E472A?style=for-the-badge&labelColor=1A1118)](#-modern-y%C3%BCksek-%C3%A7%C3%B6z%C3%BCn%C3%BCrl%C3%BCkl%C3%BC-hd-aray%C3%BCz-ve-hikaye-anlat%C4%B1m%C4%B1)
[![Tests: 17 Passed](https://img.shields.io/badge/Pytest_Suite-17%2F17_Passed_(100%25)-EBB85B?style=for-the-badge&labelColor=1A1118)](#-h%C4%B1zl%C4%B1-ba%C5%9Flang%C4%B1%C3%A7--do%C4%9Frulama-testleri)

</div>

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 🏛️ 1. Vizyon, KODTÜ Manifestosu ve ODTÜ (METU) Ruhuna Saygı Duruşu

> *"Bilim ve tekniğin ışığında, ODTÜ bozkırından yükselen sonbahar ormanının her bir yaprağını matematiksel determinizm ile yeniden dokuyoruz."*

### 🎓 KODTÜ Nedir? ODTÜ Bilgisayar Topluluğu (CClub) ve Game Jam Ruhu

**KODTÜ**, Türkiye'nin en köklü ve saygın mühendislik kurumlarından **Orta Doğu Teknik Üniversitesi (ODTÜ / METU)** bünyesinde faaliyet gösteren **ODTÜ Bilgisayar Topluluğu (METU Computer Club - CClub)** tarafından geleneksel olarak düzenlenen, algoritma, yazılım ve oyun geliştirme maratonudur:

- **ODTÜ Bilgisayar Topluluğu (CClub):** 1989 yılında kurulan CClub, Türkiye'nin ilk ve en köklü bilişim topluluklarından biri olup, her yıl *Geleneksel Programlama Yarışması*, *ODTÜ Bilişim Günleri* ve **KODTÜ Game Jam** gibi prestijli organizasyonlarla genç yetenekleri teknoloji ekosisteminde buluşturur.
- **KODTÜ Game Jam Yarışma Felsefesi:** Katılımcıların sınırlı bir süre (genellikle 48 saat) ve katı teknik kısıtlamalar altında en yüksek mühendislik kalitesini, özgün oyun mekaniğini ve estetik uyumu sergilemelerini hedefler.
- **Yarışmanın Zorunlu 3 Kısıtı:**
  1. 🎨 **Art Stili: `Pixelated`** (Retro piksel estetiği, keskin ızgara düzeni)
  2. 🍂 **Renk Paleti: `Sonbahar`** (Hüzünlü ve sıcak sonbahar renk uyumu)
  3. 🎲 **İçereceği Mekanik: `Procedural Generation`** (Rastgele / Prosedürel Üretim Mimarisi)

**KODTÜ: Autumn ProcGen Engine**, bu üç kısıtlamayı alelade bir jam prototipi olarak değil; akademik düzeyde doğrulanabilir, yüksek performanslı ve sıfır dış bağımlılıklı (**%100 Kod-Tabanlı Varlık & Ses Sentezi**) bir **Prosedürel Oyun Motoru ve Hikaye Başyapıtı** olarak hayata geçirmek üzere geliştirilmiştir:

| KODTÜ Yarışma Kısıtı | Mühendislik Çözümümüz & Mimari Standart | Doğrulama Metriği |
| :--- | :--- | :--- |
| 🎨 **Art Stili: `Pixelated`** | Doğal `320×180` (16:9) 16-Bit sanal tuval, kesirli ölçeklemeyi reddeden **Tam Sayı Ölçekleme (Integer Scaling)**, `16×16` piksel taban ızgarası, keskin **Nearest-Neighbor** örnekleme ve 1-piksel konturlu **Rotsprite** varlıklar. | `0` Alt-Piksel Titremesi (`int(round(pos))`), `60 FPS` kilitli kare hızı |
| 🍂 **Renk Paleti: `Sonbahar`** | **Hue-Shifting (Ton Kaydırma)** prensibiyle kurgulanan **16-Renk Sonbahar LUT** (`assets/palettes/autumn_16.hex` & `autumn_lut.png`). Aydınlıkta **Sunlit Birch (`#F5D67B`)**, gölgede **Deep Void (`#1A1118`)** mor-çivit tonlarına kayan atmosferik spektrum. | `%100` Palet uyumu (16 renk dışında tek bir RGB pikseli üretilmez) |
| 🎲 **Mekanik: `Procedural Generation`** | `Xoshiro256**` 64-bit PRNG üzerine kurulu **6 Aşamalı Deterministik PCG Hattı**: Çok-Oktavlı Simplex fBm $\rightarrow$ $B678/S345678$ Hücresel Otomata + BFS $\rightarrow$ 47-Karo Blob Otomatik Döşeme $\rightarrow$ Bridson $\mathcal{O}(N)$ Poisson Disk $\rightarrow$ Dijkstra Jeodezik Tehdit Bütçesi + A\* $\rightarrow$ 2B Rüzgar Vektör Alanı. | Ortalama **`~34 ms`** dünya üretim süresi, **`%100`** bağlı topoloji garantisi |

---

### 🖥️ ODTÜ & KODTÜ Özel 1080p Masaüstü Duvar Kağıdı (Desktop Wallpaper)

Projemiz için özel olarak geliştirilen prosedürel görsel motoru (`src/core/banner_generator.py`), 16-Renk Sonbahar paletini, ODTÜ Bilim Ağacı Anıtı'nı ve gün batımı gökyüzünü bir araya getiren **1920×1080 Ultra HD Masaüstü Duvar Kağıdı** sentezler:

<div align="center">
  <img src="docs/banners/odtu_campus_wallpaper_1080p.png" alt="ODTÜ & KODTÜ 1080p Desktop Wallpaper" width="100%" />
  <p><i>Masaüstü Duvar Kağıdı (1920x1080): ODTÜ Bilim Ağacı Anıtı, Alacakaranlık Halesi, Devrim Feneri ve Savrulan Verlet Yaprakları</i></p>
</div>

---

### 🌲 ODTÜ Kampüsü ve Sonbahar Mirası Oyunun Kalbinde!

ODTÜ'nün 1956 yılından beri insan eliyle bozkırdan yarattığı efsanevi ormanı, sonbahar aylarında kızıl akçaağaçların, altın huşların ve çam iğnelerinin eşsiz bir renk senfonisine dönüşür. Motorumuz, **ODTÜ kültürünün sembollerini** doğrudan prosedürel üretim algoritmalarına ve oynanış mekaniklerine entegre eder:

1. **🗿 ODTÜ Bilim Ağacı Anıtı (`bilim_agaci` Structure):**
   - Her prosedürel korunun başlangıç açıklığında (Starting Glade), Tamer Başoğlu'nun 1966 tarihli ikonik **ODTÜ Bilim Ağacı** heykelinin 16-bit piksel-sanatı yorumu yükselir (`32×32` piksel, dinamik meşale parıltısı ile).
   - **Oynanış Etkisi (*ODTÜ Bilim Meşalesi Buff*):** Oyuncu Bilim Ağacı'nın $2.4$ karo yakınına geldiğinde fener ısısı saniyede **`+15.0 Warmth/sn`** hızla yenilenir ve anıttan altın sarısı (`#F5D67B`) yaprak fırtınası yayılır.
2. **🍁 ODTÜ Kampüs Biyomları (Yalıncak, Eymir ve Devrim Korusu):**
   - İki boyutlu **Yükseklik ($E$) × Nem ($M$)** Simplex fBm matrisi, ODTÜ doğasını yansıtan 3 farklı biyom sentezler:
     - **Yalıncak Kızıl Korusu (*Crimson Canopy*):** Sık akçaağaç ve meşelerin örttüğü kızıl-kehribar patikalar.
     - **Devrim Altın Yaprak Dökümü (*Amber Leaf-Fall*):** Üzerinde yüründüğünde **Verlet yaprak fiziğini** ve **ADSR hışırtı ses sentezini** tetikleyen, oyuncuya **+%20 Hareket Hızı** veren altın huş yaprağı yığınları.
     - **Eymir Gölü Sisli Kıyısı (*Misty Hollow*):** Yüksek nemli çukur bölgelerde oluşan, ahşap köprülerle (`boardwalk`) geçilen sisli bataklık ve su birikintileri.
3. **⌨️ `[F5]` ODTÜ Özel Tohum (Curated Seed) Seçkisi:**
   - Oyun içinde **`[F5]`** tuşuna her bastığınızda motor, ODTÜ tarihine adanmış küratörlü tohum kodları arasında anında geçiş yapar:

| `[F5]` Sırası | ODTÜ Tohum Kodu (`--seed`) | 64-Bit Deterministik Hash (`SplitMix64`) | Paylaşım Kodu (`Share Code`) | Kampüs Teması ve Biyom Karakteristiği |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `ODTU-1956-DEVRIM` | `0x8A71E352D049FB12` | `KODTU-5890-OAK` | **ODTÜ Devrim Stadyumu Korusu:** Geniş merkezi altın yaprak açıklığı ve yoğun meşe kümeleri. |
| **2** | `KODTU-2026-EYMIR` | `0x3E8A91C0B7421D69` | `KODTU-7529-MIST` | **Eymir Gölü Sonbahar Kıyısı:** Zengin sulak alanlar, prosedürel ahşap iskeleler ve sisli geçitler. |
| **3** | `METU-BILIM-AGACI` | `0x7F14C809E2A653D1` | `KODTU-1489-ROOT` | **ODTÜ Bilim Ağacı Anıtı:** Eski taş çemberler, yüksek relik yoğunluğu ve simetrik koridorlar. |
| **4** | `ODTU-YALINCAK-FALL` | `0x51C9B047A83E26DF` | `KODTU-9951-LEAF` | **Yalıncak Sonbahar Patikası:** Dinamik rüzgar türbülansı yüksek, kıvrımlı orman patikaları. |

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 📸 2. Canlı Motor Görselleri & `[F1]`–`[F4]` Telemetri Vitrini

Aşağıdaki görseller herhangi bir harici tasarım programıyla **değil**, doğrudan motorun kendi prosedürel varlık sentezleyicisi (`src/core/asset_builder.py`) ve `320×180` piksel-kusursuz işleyicisi (`src/rendering/renderer.py`) tarafından `KODTU2026` tohumu için üretilmiştir:

<div align="center">

### 🎮 Canlı Oynanış Kamerası (`Seed: KODTU2026` — ODTÜ Bilim Ağacı & Başlangıç Açıklığı)
<img src="docs/preview_gameplay.png" alt="KODTÜ Autumn ProcGen Gameplay Preview" width="95%" />

<br /><br />

### 🔬 `[F1]`–`[F4]` Gerçek Zamanlı Prosedürel Hata Ayıklama (Debug) Dörtlü Vitrini
<img src="docs/preview_debug_f1_f4.png" alt="KODTÜ Autumn ProcGen 4-Panel Debug Showcase" width="95%" />

</div>

> [!TIP]
> **Dörtlü Vitrin Açıklaması:**
> - **Sol-Üst (Standart 16-Bit Render):** Y-Sıralamalı (Y-Sorted) derinlik, ODTÜ Bilim Ağacı Anıtı, Verlet yaprak parçacıkları, canlı Minimap radar ve telemetri.
> - **Sağ-Üst (`[F1]` Simplex fBm & Wind Field):** Çok oktavlı Yükseklik/Nem biyom sınıflandırması ve 2B rüzgar vektör alanı okları.
> - **Sol-Alt (`[F2]` 47-Tile Blob Bitmask & Spatial Chunks):** 8-komşulu `0..46` Blob indeksleri ve `16×16` uzamsal özetleme (Spatial Hash) sınırları.
> - **Sağ-Alt (`[F4]` Dijkstra Geodesic Field & A\* Path):** Başlangıç noktasından hesaplanan jeodezik uzaklık ısı haritası ($d \in [0, 1]$), akış alanı (Flow-Field) ve A\* en kısa yol çizgisi.

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 🎲 3. Deterministik Prosedürel Üretim Mimarisi (6-Stage PCG Pipeline)

<div align="center">
  <img src="docs/banners/pipeline_6stage_infographic.png" alt="6-Stage Deterministic PCG Pipeline Infographic" width="100%" />
</div>

Motorumuzda **rastgelelik (randomness) kaos demek değildir; matematiksel olarak denetlenebilir determinizm demektir.** Standart `random.random()` veya `os.urandom()` çağrıları prosedürel katmanta **kesinlikle yasaklanmıştır**. Tüm dünya, tek bir tohum dizgesinden (`--seed "KODTU2026"`) türetilen 64-bitlik izole alt-akışlarla (sub-streams) sentezlenir:

```mermaid
flowchart LR
    SEED["Tohum Dizgesi<br/>'KODTU2026'"] --> HASH["FNV-1a + SplitMix64<br/>0xDF04761EFADEBE5D"]
    HASH --> PRNG["Xoshiro256** PRNG<br/>İzole Alt-Akışlar"]
    PRNG --> S1["Aşama 1: 2B Simplex fBm<br/>Yükseklik E(x,y) & Nem M(x,y)"]
    S1 --> S2["Aşama 2: Hücresel Otomata<br/>B678/S345678 + BFS Bağlantı"]
    S2 --> S3["Aşama 3: 47-Karo Blob<br/>8-Bit Köşe İndirgemeli Maske"]
    S3 --> S4["Aşama 4: Bridson Poisson Disk<br/>O(N) Mavi-Gürültü Flora"]
    S4 --> S5["Aşama 5: Yapı Sentezi & A*<br/>ODTÜ Bilim Ağacı + İskeleler"]
    S5 --> S6["Aşama 6: Dijkstra Tehdit Bütçesi<br/>Jeodezik Relik & Muhafız Dağılımı"]
```

---

### 🔹 Aşama 1: `SplitMix64` & `Xoshiro256**` PRNG ve Çok-Oktavlı Simplex fBm (`src/procgen/prng.py`, `src/procgen/noise.py`)

Kullanıcının girdiği herhangi bir metin veya tam sayı tohumu, önce 64-bit **FNV-1a** özetlemesinden, ardından **Stafford Mix13 (`SplitMix64`)** çığ etkisi (avalanche) karıştırıcısından geçirilerek dört adet 64-bitlik `Xoshiro256**` durum yazmacını başlatır.

Coğrafi temel, iki bağımsız **2B Simplex Kesirli Brown Hareketi (Fractional Brownian Motion - fBm)** skaler alanı ile oluşturulur:
- **Yükseklik Alanı ($E(x, y) \in [0, 1]$):** $O = 4$ oktav, kalıcılık (persistence) $G = 2^{-H} \approx 0.52$, boşlukluluk (lacunarity) $L = 2.0$, ölçek $S = 0.045$. Artı olarak harita sınırlarında doğal bir vadi oluşturan radyal vinyet fonksiyonu uygulanır.
- **Nem Alanı ($M(x, y) \in [0, 1]$):** $O = 3$ oktav, $G = 0.55$, $L = 2.0$, ölçek $S = 0.060$.

$$f_{\text{fBm}}(x, y) = \frac{1}{\sum_{i=0}^{O-1} G^i} \sum_{i=0}^{O-1} G^i \cdot \text{Simplex2D}\left(x \cdot S \cdot L^i + \delta_x, \; y \cdot S \cdot L^i + \delta_y\right)$$

---

### 🔹 Aşama 2: Hücresel Otomata ($B678/S345678$) ve `%100` Bağlı Topoloji Garantisi (`src/procgen/automata.py`)

Ham gürültü eşiklemesinden gelen ikili ızgara ($1 = \text{Duvar/Uçurum}$, $0 = \text{Yürünebilir Zemin}$), organik orman açıklıkları oluşturmak için **Moore Komşuluğu** ($3 \times 3$ pencere) üzerinde **$B678 / S345678$** kurallarıyla 4 iterasyon boyunca evrimleştirilir:

$$\text{State}_{t+1}(x, y) = \begin{cases} 1 & \text{eğer } \text{State}_t(x,y) = 0 \text{ ve } N_{\text{wall}}(x,y) \in \{6, 7, 8\} \quad (\text{Doğum / Birth}) \\ 1 & \text{eğer } \text{State}_t(x,y) = 1 \text{ ve } N_{\text{wall}}(x,y) \in \{3, 4, 5, 6, 7, 8\} \quad (\text{Hayatta Kalma / Survival}) \\ 0 & \text{aksi halde (Yürünebilir Açıklık)} \end{cases}$$

**Sıfır Çıkmaz Sokak Garantisi (Topological Guarantee):**
1. **BFS Taşkın Doldurma (Flood-Fill):** Tüm bağlantılı yürünebilir bileşenler $\mathcal{O}(W \cdot H)$ zamanda etiketlenir.
2. $14$ karodan küçük mikro-mağaralar duvarla doldurulur; daha büyük ayrık odalar ise ana bileşene **Bresenham + Drunkard's Walk (Sarhoş Yürüyüşü)** algoritmasıyla $r=1$ yarıçaplı doğal patikalarla bağlanır.
3. Son doğrulama geçişinde ana bileşen dışındaki tüm yetim pikseller temizlenerek **her tohumda tam olarak $1$ adet `%100` erişilebilir oyun dünyası** garanti altına alınır.

---

### 🔹 Aşama 3: 47-Karo Blob Otomatik Döşeme (8-Bit Bitmasking) (`src/procgen/autotile.py`)

Karo kenarlarının, iç/dış köşelerin ve uçurum duvarlarının kusursuz birleşmesi için 8 yönlü komşuluk bit maskesi hesaplanır. Köşegen bir bitin ($\text{NE}, \text{SE}, \text{SW}, \text{NW}$) aktif olabilmesi için **komşu olduğu her iki ana yönün de (Cardinal Gates)** aynı arazi tipinde olması şarttır:

$$\text{NE}' = \text{NE} \land N \land E, \quad \text{SE}' = \text{SE} \land S \land E, \quad \text{SW}' = \text{SW} \land S \land W, \quad \text{NW}' = \text{NW} \land N \land W$$

$$M(x, y) = 1 \cdot N + 2 \cdot \text{NE}' + 4 \cdot E + 8 \cdot \text{SE}' + 16 \cdot S + 32 \cdot \text{SW}' + 64 \cdot W + 128 \cdot \text{NW}'$$

Bu indirgeme, $2^8 = 256$ olası durumu $\mathcal{O}(1)$ arama tablosu (`RAW_TO_47_LUT`) ile tam olarak **47 kanonik Blob karosuna (`0..46`)** eşler.

---

### 🔹 Aşama 4: Bridson $\mathcal{O}(N)$ Hızlı Poisson Disk Örneklemesi (`src/procgen/poisson.py`)

Beyaz gürültüyle (white-noise) rastgele dağıtılan ağaçlar yapay kümelenmeler ve boşluklar yaratır. Motorumuz bunun yerine **Robert Bridson'ın $\mathcal{O}(N)$ Hızlı Poisson Disk Örneklemesi** algoritmasını kullanarak tüm florayı **Mavi Gürültü (Blue-Noise)** spektrumunda yerleştirir:
- Hücre boyutu $c = r_{\min} / \sqrt{2}$ olan bir arka plan ızgarası kurulur ($k = 30$ aday denemesi).
- Herhangi iki obje arasındaki Öklid uzaklığı her zaman $\|p_i - p_j\|_2 \ge r_{\min}$ koşulunu sağlar:
  - **Asırlık Kızıl Akçaağaç, Altın Huş ve Meşe Ağaçları:** $r_{\min} = 3.2$ karo (`51.2 px`).
  - **Çalılar, Devrilmiş Kütükler ve Kaya Parçaları:** $r_{\min} = 1.8$ karo (`28.8 px`).
  - **Kızıl Mantar Halkaları, Balkabakları ve Yaprak Yığınları:** $r_{\min} = 1.1$ karo (`17.6 px`).

---

### 🔹 Aşama 5 & 6: Yapı Sentezi, A\* Ahşap Köprüler ve Dijkstra Jeodezik Tehdit Bütçesi (`src/procgen/structures.py`, `src/procgen/automata.py`)

1. **ODTÜ Bilim Ağacı & Kadim Tapınak Sentezi:**
   - Başlangıç noktasının hemen kuzeydoğusuna **ODTÜ Bilim Ağacı Anıtı (`bilim_agaci`)**, haritanın en uzak jeodezik noktasına ($d(x,y) \ge 0.82$) ise **Kadim Sonbahar Tapınağı (`Autumn Shrine`)** yerleştirilir.
2. **A\* (A-Star) Sulak Alan Köprüleri (`boardwalk`):**
   - Başlangıç noktası ile Tapınak arasındaki en kısa yürünebilir yol **A\*** algoritmasıyla hesaplanır. Bu rota üzerindeki tüm **Misty Hollow** (çamur/su) karolarına otomatik olarak ahşap iskele (`boardwalk`) döşenir.
3. **Dijkstra Jeodezik Uzaklık Haritası ve Tehdit Bütçesi ($B_{\text{threat}}$):**
   - Başlangıç noktasından tüm yürünebilir karolara **Dijkstra / BFS** ile gerçek yürüme mesafesi hesaplanıp $d(x, y) \in [0, 1]$ aralığına normalize edilir:
   - **Güvenli Başlangıç Açıklığı ($d < 0.22$):** Hiçbir düşman doğmaz; **ODTÜ Bilim Ağacı**, kamp ateşi ve ilk meşe palamutları burada yer alır.
   - **Orta Koruluk ($0.22 \le d < 0.65$):** *Corrupted Autumn Wisp* ve *Bramble Stalker* devriyeleri.
   - **Derin Sonbahar Çekirdeği ($d \ge 0.65$):** *Hollow Bark Golem*, **5 adet Hasat Reliği (*Harvest Relics*)** ve Tapınak muhafızı **Elder Stag Warden (Mini-Boss)**.

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 🎨 4. Sonbahar Renk Kuramı (16-Color Hue-Shifted Autumn LUT) & Piksel Mühendisliği

<div align="center">
  <img src="docs/banners/palette_lut_infographic.png" alt="16-Color Sonbahar Chromatic Spectrum & 16-Bit Sprite Atlas" width="100%" />
</div>

Motorumuz, klasik RGB değerlerini yalnızca karartıp açmak yerine **Hue-Shifting (Ton Kaydırma)** kuramını uygular:
- **Aydınlık Tonlar (Highlights):** Işık şiddeti arttıkça renk tonları sarı-altın ve soluk güneş huzmesine (**`#F5D67B` Sunlit Birch** $\rightarrow$ **`#FAEBAC` Pale Sunbeam**) kayar.
- **Gölge Tonları (Shadows):** Gölge derinleştikçe renkler çamurlu gri/siyaha değil, soğuk kızıl-mürdüm ve derin çivit-mor (**`#4E222A` Mulberry Dusk** $\rightarrow$ **`#1A1118` Deep Void**) tonlarına kayar.

| İndeks | İsim (Token) | Hex Kodu | RGB Değeri | Görsel Rolü ve Atmosferik Görevi |
| :---: | :--- | :---: | :---: | :--- |
| `00` | **Deep Void** | `#1A1118` | `(26, 17, 24)` | En derin gölge, dış kontur (outline), uçurum boşluğu |
| `01` | **Plum Shadow** | `#2C1820` | `(44, 24, 32)` | Karanlık orman tabanı, derin gövde gölgesi |
| `02` | **Withered Bark** | `#3B2123` | `(59, 33, 35)` | Yaşlı meşe kabuğu, taş anıt gölgesi |
| `03` | **Mulberry Dusk** | `#4E222A` | `(78, 34, 42)` | Alacakaranlık geçiş tonu, bataklık derinliği |
| `04` | **Damp Loam** | `#5C362C` | `(92, 54, 44)` | Nemli sonbahar toprağı, çamur tabanı |
| `05` | **Crimson Decay** | `#6B2D26` | `(107, 45, 38)` | Dökülmüş koyu kızıl akçaağaç yaprakları |
| `06` | **Chestnut Wood** | `#85442B` | `(133, 68, 43)` | Kestane ahşap köprüler, kütük dokusu |
| `07` | **Rust Terracotta** | `#9E472A` | `(158, 71, 42)` | Pas kızılı yaprak kümeleri, ODTÜ Yalıncak korusu |
| `08` | **Burnt Amber** | `#B5592A` | `(181, 89, 42)` | Yanık kehribar kanopi orta tonu |
| `09` | **Cinnamon Leaf** | `#C86D2B` | `(200, 109, 43)` | Tarçın turuncusu parlak yaprak geçişi |
| `10` | **Harvest Gold** | `#E09F3E` | `(224, 159, 62)` | Hasat altını, fener ışığı halkası, meşe palamudu |
| `11` | **Ochre Moss** | `#EBB85B` | `(235, 184, 91)` | Altın liken, sıcak huş ağacı yaprakları |
| `12` | **Sunlit Birch** | `#F5D67B` | `(245, 214, 123)` | Güneş vuran huş kabuğu, UI vurgu rengi |
| `13` | **Pale Sunbeam** | `#FAEBAC` | `(250, 235, 172)` | Relik çekirdeği, Bilim Ağacı meşalesi, kritik vuruş |
| `14` | **Twilight Slate** | `#8C7A78` | `(140, 122, 120)` | ODTÜ Bilim Ağacı metalik gövdesi, kadim taş |
| `15` | **Autumn Mist** | `#D4C8BE` | `(212, 200, 190)` | Eymir sabah sisi, rüzgar akış çizgileri |

---

### 📐 Piksel-Kusursuz (Pixel-Perfect) Görüntüleme Garantileri (`src/core/camera.py`, `src/rendering/renderer.py`)

1. **Doğal `320×180` Sanal Tuval & Tam Sayı Ölçekleme:**
   - Tüm dünya ve HUD önce `320×180` çözünürlüklü `self.canvas` yüzeyine çizilir, ardından pencere boyutuna göre yalnızca $\text{ scale } \in \{1\times, 2\times, 3\times, 4\times, 6\times\}$ tam sayı katsayılarıyla büyütülür. **Bilinear/Trilinear bulanıklaştırma kesinlikle yoktur.**
2. **Sıfır Alt-Piksel Titremesi (Zero Sub-Pixel Jitter):**
   - Fizik motoru `float` koordinatlarda çalışsa da kamera ve varlık çizimleri her karede `int(round(pos))` ile tam piksel ızgarasına kilitlenir.
3. **Y-Sıralamalı (Y-Sorted) Derinlik İşleme:**
   - Oyuncu, düşmanlar, ağaçlar, çalılar ve **ODTÜ Bilim Ağacı Anıtı** her karede `foot_y` (taban Y koordinatı) değerine göre sıralanır; böylece oyuncu ağaçların ve anıtın arkasından veya önünden doğal derinlik algısıyla geçer.
4. **Verlet Entegrasyonlu Yaprak Parçacık Sistemi (`src/rendering/particles.py`):**
   - Sahnede aynı anda uçuşan `160+` sonbahar yaprağı, zamanla evrilen **2B Simplex Rüzgar Vektör Alanı ($\vec{W}(x, y, t)$)** ve oyuncunun kılıç/nova darbelerinin oluşturduğu radyal şok dalgalarıyla hareket eder. Yapraklar dönerken piksel kırılmasını önlemek için 4 açılı (`0°`, `90°`, `180°`, `270°`) önceden fırınlanmış **Rotsprite** matrisleri kullanılır.

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## ⚔️ 5. Oynanış Döngüsü, Savaş Mekanikleri ve ODTÜ Sonbahar Kutsamaları (Boons)

Oyuncu, sonbahar korusuna çöken alacakaranlıkta **Güneş Közü Fenerini (Solar Ember Lantern)** taşıyan **Sonbahar Muhafızı (Autumn Keeper)** rolündedir:

- **🔥 Fener Isısı (Lantern Warmth) & Hayatta Kalma:** Zamanla azalan fener ısınızı **ODTÜ Bilim Ağacı Anıtı** (`+15/sn`), simyacı kamp ateşleri (`campfire`) ve meşe palamutları (`Golden Acorn`) ile yenileyin.
- **✨ 5 Hasat Reliği & Kadim Tapınak:** Haritanın derinliklerindeki **5 Hasat Reliğini (`Harvest Relic`)** toplayıp **Kadim Sonbahar Tapınağı'na (`[E]`)** dönerek bir sonraki prosedürel koru derinliğine (`Grove Depth 2, 3, ...`) geçin!
- **🗡️ 3-Vuruşluk Solar Ember Kombo (`[SPACE]` / Sol Tık):** Ardışık vuruşlarda `Combo x1` $\rightarrow$ `Combo x2` $\rightarrow$ **`CRIT -4!` (`Combo x3`)** geniş açılı altın köz darbesi vurur, çevredeki yaprakları savurur ve **isabet eden her darbede `+1 Solar Bolt` mermisi şarj eder** (*Hyper Light Drifter* tarzı hibrit dövüş döngüsü).
- **☄️ Solar Ember Bolt (`[F]` / Sağ Tık):** Fenerden yüksek hızlı bir güneş közü mermisi (`11.5 karo/sn`) ateşler. `KODTÜ Hasat Tacı` kutsaması açıldığında **3'lü Yelpaze Yaylım Ateşine (3-Way Volley)** dönüşür!
- **🛡️ Yakın Dövüşle Mermi Yansıtma (`DEFLECT!`):** *Wisp* ve *Elder Stag Warden* tarafından ateşlenen karanlık küreleri (**Twilight Orbs**) kılıç darbesi (`[SPACE]`) veya `Harvest Nova ([Q])` ile vurduğunuzda küre **`1.65x` hızla ve `2x` hasarla düşmana geri yansıtılır (`DEFLECT!`)**!
- **💥 Harvest Nova Şok Dalgası (`[Q]` / Orta Tık):** $360^\circ$ çevredeki tüm düşmanları geri püskürten, düşman kürelerini yansıtan ve `28` altın yaprak parçacığı saçan alan etkili patlama.
- **💨 Autumn Gust Dash & Hayalet İzleri (`[SHIFT]`):** Kısa süreli dokunulmazlık (i-frame), yaprak girdabı ve piksel-kusursuz **Afterimage Hayalet İzleri (`DashGhost`)** bırakan rüzgar atılması.
- **⚡ Dokunsal Vuruş Duraksaması (`Hit-Stop Frame Freeze`):** Kritik vuruşlarda, mermi yansıtmalarında ve düşman infazlarında uygulanan `38 ms` mikro-dondurma ve $\text{Trauma}^2$ kamera sarsıntısı.

---

### 🌟 Roguelite ODTÜ Sonbahar Kutsamaları (`Autumn Boons` — `[B]` veya Relik Toplama)

Haritadaki her **Hasat Reliği (`Harvest Relic`)** toplandığında (veya test/sinerji için **`[B]`** tuşuna basıldığında) oyuncu ODTÜ kampüs efsanelerinden ilham alan **5 kalıcı kutsamadan (Boon)** birini kazanır:

| Kutsama Kodu | ODTÜ Kutsama Adı | Mekanik Sinerji ve Yükseltme Etkisi | İlham Alınan Muadil Mekanik |
| :--- | :--- | :--- | :--- |
| **`DEVRIM_TORCH`** | 🔥 **Devrim Meşalesi** | Saniyede `+2.5 Warmth` pasif ısı yenilemesi sağlar ve maksimum **Solar Bolt** kapasitesini `4` $\rightarrow$ `5` yapar. | *Don't Starve* / *Core Keeper* Fener Aurası |
| **`BILIM_SPARK`** | ⚡ **Bilim Ağacı Kıvılcımı** | Tüm kılıç darbelerine ve Solar Bolt mermilerine **`+1` Bonus Hasar** ekler, yaprak şok dalgasını büyütür. | *Hades* / *Children of Morta* Hasar Sinerjisi |
| **`YALINCAK_GALE`** | 🍃 **Yalıncak Rüzgarı** | Yürüme hızını **`+%18`** artırır ve `Autumn Gust Dash` bekleme süresini **`%30` kısaltır** (`0.65s` $\rightarrow$ `0.45s`). | *Wizard of Legend* Rüzgar Koşusu |
---

## 📖 6. Modern Yüksek Çözünürlüklü (HD) Arayüz ve Hikaye Anlatımı (Story Mode)

> *"Celeste, Eastward ve Sea of Stars tarzı: Dünyanın kendisi 100% piksel-kusursuz (Pixelated) ve Sonbahar paletine sadık kalırken, oyuncunun hikayeyi takip ettiği arayüz ultra-net, sade ve modern 1280×720 HD çözünürlükte sunulur."*

KODTÜ yarışmasının **Pixelated**, **Sonbahar** ve **Procedural Generation** kısıtlamalarına tam bağlı kalınırken, oyun deneyimini hantal retro HUD kutularından kurtarıp **çağdaş, modern ve sade bir anlatı oyununa** dönüştüren hibrit bir mimari geliştirdik:

1. **🏛️ 3 Aşamalı Zengin ODTÜ Hikaye Bölümleri (`src/core/story.py`):**
   - **Bölüm I: Yalıncak Yaprak Yolu (Koru 1):** 1956'dan beri bozkırdan ellerle yeşertilen ulu ODTÜ ormanına çöken alacakaranlık ayazı. Bilim Ağacı'nın meşalesinden Devrim Feneri'ni yakarak ormanın dağılmış 5 Sonbahar Hatırasını kurtarın.
   - **Bölüm II: Eymir'in Sisli Kıyıları (Koru 2):** Eymir Gölü'nün sazlıklarına ve prosedürel ahşap iskelelerine inen patikalar. Gölgelerin fısıltılarını kılıç darbeleriyle geri püskürtün ve gölün kadim bilgisini tapınağa taşıyın.
   - **Bölüm III: Devrim Korusu ve Sonbahar Kalbi (Koru 3+):** Devrim Stadyumu'nun ulu korusunda Ormanın Koruyucu Ruhu **Kadim Geyik (Elder Stag Warden)** ile yüzleşin, gölge kürelerini yansıtarak Sonbahar Kalbini sonsuzluğa mühürleyin!
2. **💬 Daktilo Efektli (Typewriter) Piksel-Portreli Türkçe Diyalog Sistemi:**
   - Ekranın alt-ortasında konuşmacıya özel `64×64` piksel-sanatı portre ikonları (**ODTÜ Bilim Ağacı Anıtı**, **Sonbahar Hatırası Kristali**, **Ormancı Kamp Ateşi**, **Genç Muhafız Ekin**, **Kadim Geyik Warden**).
   - *Celeste* ve *Eastward* tarzı harf harf açılan akıcı Türkçe daktilo (Typewriter) animasyonu.
3. **🕯️ Dinamik Sonbahar Fener Vinyeti & Işıklandırma Geçişi (`src/rendering/renderer.py`):**
   - Oyuncunun taşıdığı fener, ODTÜ Bilim Ağacı Anıtı ve Kamp Ateşleri etrafında dinamik dalgalanan sıcak altın (`#FAEBAC` / `#E09F3E`) auralar yayılırken, ekranın kenarları doğal derinlik katan mor-çivit gölgelere (`#1A1118` / `#2C1820`) kavuşur.
4. **🧭 Üst-Orta Dinamik Pusula Kapsülü (Compass Pill):**
   - Minimalist navigasyon kapsülü: En yakın **Sonbahar Hatırası** veya **Kadim Tapınak** yönünü ok ile ve gerçek adım mesafesiyle (`Mesafe: 14 adım`) anlık gösterir.
5. **📊 Sol-Üst Sadeleştirilmiş Durum & Görev Kartı:**
   - **Devrim Feneri Isısı:** Yüzde çubuğuyla temiz görsel geribildirim.
   - **Köz Mermisi [F]:** 4 şarj hücresi ile anlık mermi durumu.
   - **Sonbahar Hatırası:** `0 / 5` ilerleme göstergesi ve anlık Türkçe tek cümlelik net görev özeti.
6. **📜 İnteraktif Hikaye Başlangıç Kartı (`[H]` / Enter):**
   - Hikaye arka planını, fener mekaniğini ve 3 adımlı basit oyun amacını özetleyen estetik kart. İstendiğinde **`[H]`** tuşuyla yeniden açılabilir.

---

---

### 🎮 Klavye & Fare Kontrol Tablosu

| Tuş / Girdi | Aksiyon / Komut | Teknik / Oynanış Açıklaması |
| :---: | :--- | :--- |
| **`W, A, S, D`** / **Ok Tuşları** | Hareket Et | 8 yönlü alt-piksel hareketi, `16×16` uzamsal özetleme çarpışma çözümü |
| **`SPACE`** veya **Sol Tık** | **Solar Ember Slash** | 3-vuruşluk kombo + **Mermi Yansıtma (`DEFLECT!`)** + **Solar Bolt Şarjı** |
| **`F`** veya **Sağ Tık** | **Solar Ember Bolt** | Menzilli güneş közü atışı (Hasat Tacı ile 3'lü yaylım ateşi) |
| **`Q`** veya **Orta Tık** | **Harvest Nova** | $360^\circ$ alan etkili köz patlaması, yüksek geri itme ve $360^\circ$ mermi yansıtma |
| **`SHIFT`** | **Autumn Gust Dash** | Afterimage hayalet izli hızlı rüzgar atılması (`0.22 sn` dokunulmazlık) |
| **`B`** | **ODTÜ Kutsaması (Boon)** | Sıradaki ODTÜ Sonbahar Kutsamasını (`Devrim`, `Bilim`, `Yalıncak`, `Eymir`, `Hasat`) açar |
| **`C`** | **ODTÜ Kutsama & Savaş Kodeksi** | Aktif ODTÜ kutsamalarını, infaz edilen düşman, yansıtılan küre ve palamut istatistiklerini açar |
| **`E`** | **Tapınak Etkileşimi** | 5 Relik toplandığında Kadim Tapınağı uyandırır ve sonraki koruyu sentezler |
| **`M`** | **Minimap Radar Aç/Kapa** | Sağ üstteki canlı biyom, relik, Bilim Ağacı ve tapınak radarını açar/kapatır |
| **`TAB`** | **Tohum (Seed) Penceresi** | Canlı metin tohumu girme ve paylaşım kodu (`KODTU-XXXX-LEAF`) görüntüleme |
| **`F1`** | **fBm & Rüzgar Katmanı** | Çok oktavlı Simplex gürültü, biyom ve 2B rüzgar vektör alanı görselleştiricisi |
| **`F2`** | **47-Blob & Chunk Katmanı** | 8-bit `0..46` Blob otomatik döşeme indeksleri ve `16×16` chunk ızgarası |
| **`F3`** | **Anında Yeniden Üretim** | `Xoshiro256**` akışından yeni bir tohum çekerek dünyayı `<35 ms` içinde yeniden kurar |
| **`F4`** | **Dijkstra & A\* Katmanı** | Jeodezik uzaklık ısı haritası, Flow-Field vektörleri ve A\* en kısa yol çizgisi |
| **`F5`** | **ODTÜ Tohum Seçkisi** | `ODTU-1956-DEVRIM`, `KODTU-2026-EYMIR`, `METU-BILIM-AGACI`, `ODTU-YALINCAK-FALL` arasında geçiş |

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 🏆 6. Muadil Oyunlar & Rakip Analizi (Genre Benchmarks & Competitor Matrix)

<div align="center">
  <img src="docs/banners/competitor_matrix_infographic.png" alt="Genre Benchmark & Competitor Analysis Matrix" width="100%" />
</div>

Üstten görünüşlü (Top-Down) **Pixel Art + Prosedürel Üretim (PCG) + Aksiyon Roguelite / Hayatta Kalma** kulvarı, bağımsız oyun dünyasının en rekabetçi ve en çok satan türlerinden biridir. **KODTÜ: Autumn ProcGen Engine** geliştirilirken bu kulvarda dünya çapında başarı yakalamış **8 başyapıt** derinlemesine incelenmiş, her birinin en güçlü mühendislik ve oynanış sütunu motorumuza sentezlenmiştir:

| Muadil Oyun (Stüdyo / Yıl) | Küresel Başarı Nedeni & Temel Mekanik | Rakibin Sınırlılığı / Eksikliği | **KODTÜ: Autumn ProcGen Engine**'deki Üstün Karşılığı |
| :--- | :--- | :--- | :--- |
| **1. Hyper Light Drifter**<br/>*(Heart Machine, 2016)* | Kılıç darbeleriyle mermi şarj etme (*Slash-to-Reload*), mermi yansıtma, Dash hayalet izleri ve Hue-Shifted atmosferik piksel sanatı. | Dünyası tamamen sabit/el yapımıdır; prosedürel üretim (PCG) içermez. | `Solar Ember Slash ([SPACE])` ile `Solar Bolt ([F])` şarj etme, `DEFLECT!` mermi yansıtma ve `DashGhost` izlerini **`%100` deterministik prosedürel dünya** ile birleştirir. |
| **2. Core Keeper**<br/>*(Pugstorm, 2024)* | Hücresel otomata mağara sistemleri, çoklu biyom ekosistemi, otomatik karo döşeme (autotiling) ve ışık/meşale odaklı keşif. | Savaş sistemi daha yavaş ve kütleseldir; rüzgar/yaprak vektör fiziği bulunmaz. | $B678/S345678$ Otomata + **47-Karo Blob Bitmasking** ve `16×16` Chunk Spatial Hash mimarisini hızlı aksiyon ve **2B Verlet yaprak fiziğiyle** birleştirir. |
| **3. Nuclear Throne**<br/>*(Vlambeer, 2015)* | Çıkmaz sokaksız dinamik seviye kazıyıcıları, **Hit-Stop** (mikro kare dondurma), kamera sarsıntısı ve mutasyon seçimleri. | Görsel paleti düşük kontrastlı çorak topraklardır; topolojik mesafe bütçelemesi basittir. | Vlambeer tarzı `38 ms` **Hit-Stop** ve $\text{Trauma}^2$ sarsıntısını, **Dijkstra Jeodezik Tehdit Bütçesi** ve **5 ODTÜ Kutsaması (`Autumn Boons`)** ile sunar. |
| **4. Enter the Gungeon**<br/>*(Dodge Roll, 2016)* | Kusursuz tam sayı piksel ölçekleme, mermi cehennemi (bullet-hell) desenleri, parçalanabilir çevre objeleri ve mermi kesme/yansıtma. | Önceden çizilmiş oda şablonlarını birleştirir; organik doğa/orman topoğrafyası üretmez. | *Elder Stag Warden*'ın 3'lü **Twilight Orb** yaylım ateşini yansıtma (`DEFLECT!`) ve balkabağı/çalıları parçalayarak **Altın Palamut (`+ACORN DROP!`)** düşürme mekaniğini sunar. |
| **5. Wizard of Legend**<br/>*(Contingent99, 2018)* | Çok hızlı element büyü komboları, $360^\circ$ alan etkili novalar, rüzgar atılmaları ve sinerjik relik/kutsama dizilimleri. | Koridorlar dikdörtgen zindan karolarından ibarettir; mavi-gürültülü (Poisson) ekolojik dağılım yoktur. | `3-Hit Solar Combo` + `Harvest Nova [Q]` + `Solar Bolt [F]` + `Gust Dash [SHIFT]` dörtlüsünü **Bridson $\mathcal{O}(N)$ Poisson Disk** ormanında çalıştırır. |
| **6. Don't Starve**<br/>*(Klei Entertainment)* | Sonbahar (*Reign of Giants*) biyom estetiği, karanlık/ısı yönetimi (fener/kamp ateşi) ve çevresel tehdit algısı. | Dövüş mekanikleri tek tuşlu ("kite & hit") ve basittir; piksel-sanatı yerine 2B vektör kukla kullanır. | Fener ısısı (*Lantern Warmth*) hayatta kalma gerilimini **ODTÜ Bilim Ağacı Meşalesi (`+15/sn`)**, simyacı kamp ateşleri ve derin kombo sistemiyle harmanlar. |
| **7. Noita**<br/>*(Nolla Games, 2020)* | Deterministik tohum (seed) mimarisi ve her pikselin/parçacığın çevresel kuvvetlerle fiziksel etkileşime girmesi. | Yüksek CPU yükü nedeniyle düşük donanımlarda kare hızı düşüşleri yaşanabilir. | Zamanla evrilen **2B Simplex Rüzgar Vektör Alanı ($\vec{W}(x,y,t)$)** ve oyuncu saldırılarının radyal şok dalgalarıyla savrulan `160+` Verlet yaprağını `60 FPS`'te işler. |
| **8. Children of Morta & Moonlighter** | Zengin 16-bit piksel animasyonları, Y-Sıralamalı (Y-Sorted) derinlik ve zindan/orman keşif döngüsü. | Prosedürel üretim aşamaları oyuncuya kapalı bir "kara kutu" (black-box) olarak çalışır. | **`[F1]`–`[F4]` Canlı Mühendislik Telemetrisi** ve **`[C]` ODTÜ Kutsama Kodeksi** ile tüm algoritmik katmanları oyun içinde anlık olarak görselleştirir! |

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 🗂️ 7. Proje Dizin Mimarisi

```text
kodtu-autumn-procgen/
├── README.md                          # Kapsamlı teknik dokümantasyon, ODTÜ mirası ve rakip analizi
├── requirements.txt                   # Bağımlılıklar (pygame-ce, numpy, pillow, pytest)
├── assets/                            # Deterministik olarak sentezlenen 16-bit varlıklar ve sesler
│   ├── palettes/
│   │   ├── autumn_16.hex              # 16-Renk Sonbahar HEX palet tanımı
│   │   └── autumn_lut.png             # 1D Renk Arama Tablosu (LUT) dokusu
│   ├── shaders/
│   │   ├── palette_quantize.glsl      # GLSL 330 Sonbahar LUT & Alacakaranlık Vinyet gölgelendiricisi
│   │   └── wind_sway.glsl             # GLSL 330 Tam Sayı Ölçekleme & Kanopi Rüzgar gölgelendiricisi
│   ├── sprites/
│   │   ├── autotile_47.png            # 47-Karo Blob otomatik döşeme (autotile) atlası
│   │   ├── foliage_sheet.png          # Akçaağaç, Huş, Meşe, Mantar, Balkabağı ve Yaprak atlası
│   │   ├── player_sheet.png           # Autumn Keeper 16-bit karakter animasyon kareleri
│   │   └── entities_sheet.png         # Wisp, Stalker, Golem, Elder Stag Warden ve Relik atlası
│   └── audio/                         # Prosedürel ADSR zarflı PCM WAV ses efektleri
│       ├── ambient_wind.wav           # Pembe gürültü + LFO alçak geçiren sonbahar rüzgarı
│       ├── leaf_crunch_1..3.wav       # 3 farklı perdede kuru yaprak hışırtısı
│       ├── slash_ember.wav            # Köz kılıcı savurma, Solar Bolt ve Nova sesi
│       ├── harvest_chime.wav          # Pentatonik (`C5-D5-F5-G5-A5`) relik tınısı
│       ├── portal_activate.wav        # Tapınak uyanışı ve ODTÜ tohum geçiş akoru
│       ├── dialogue_blip.wav          # Daktilo hikaye diyalog harf tıkırtısı
│       ├── deflect_clash.wav          # Mermi yansıtma metalik parry çınlaması
│       └── level_up.wav               # ODTÜ Kutsaması açılış zafer fanfarı
├── docs/
│   ├── banners/                       # Prosedürel olarak üretilen yüksek çözünürlüklü infografik ve bannerlar
│   │   ├── hero_odtu_kodtu_banner.png
│   │   ├── odtu_campus_wallpaper_1080p.png  # 1920x1080 Ultra HD Masaüstü Duvar Kağıdı
│   │   ├── pipeline_6stage_infographic.png
│   │   ├── palette_lut_infographic.png
│   │   ├── competitor_matrix_infographic.png
│   │   └── section_divider_autumn.png
│   ├── preview_gameplay.png           # Canlı 16-bit oynanış ekran görüntüsü
│   └── preview_debug_f1_f4.png        # 4'lü [F1]-[F4] prosedürel telemetri vitrini
├── src/
│   ├── main.py                        # Ana oyun döngüsü, Hit-Stop, Solar Bolt, Deflect ve [F1]-[F5] kontrolcüsü
│   ├── core/
│   │   ├── palette.py                 # 16-Renk Sonbahar LUT sabitleri ve Hue-Shifting matematiği
│   │   ├── camera.py                  # 320x180 tam sayı ölçekleme, Frustum Culling ve kamera sarsıntısı
│   │   ├── story.py                   # Türkçe hikaye bölümleri, diyalog kuyruğu ve anı parçacıkları
│   │   ├── spatial_hash.py            # 16x16 Chunk uzamsal özetleme, O(1) çarpışma ve parçalanabilir flora
│   │   ├── asset_builder.py           # 100% deterministik piksel-sanatı ve ODTÜ Bilim Ağacı sentezleyicisi
│   │   ├── audio_synth.py             # Prosedürel PCM ses sentezleyicisi ve çalışma zamanı mikseri
│   │   └── banner_generator.py        # README için piksel-sanatı banner ve rakip matrisi üreticisi
│   ├── procgen/
│   │   ├── prng.py                    # FNV-1a, SplitMix64, Xoshiro256** ve Mulberry32 PRNG motoru
│   │   ├── noise.py                   # Vektörize 2B Simplex fBm gürültü ve 2B rüzgar vektör alanı
│   │   ├── automata.py                # B678/S345678 Hücresel Otomata, BFS Flood-Fill ve Dijkstra alanı
│   │   ├── autotile.py                # 8-bit komşuluk maskeleme ve 256 -> 47 Blob indirgeme tablosu
│   │   ├── poisson.py                 # Bridson O(N) Hızlı Poisson Disk Örneklemesi
│   │   ├── structures.py              # ODTÜ Bilim Ağacı, Tapınak, A* köprüler ve tehdit bütçesi
│   │   └── pipeline.py                # 6 aşamalı deterministik PCG orkestratörü ve milisaniye telemetrisi
│   ├── entities/
│   │   └── actors.py                  # Player, Projectile, DashGhost, ODTÜ Boons ve 4 düşman arketipi
│   ├── rendering/
│   │   ├── particles.py               # Verlet entegrasyonlu yaprak fiziği ve Rotsprite dönüşleri
│   │   └── renderer.py                # Y-Sorted sahne işleyicisi, mermi/hayalet çizimi ve [F1]-[F4] katmanları
│   └── ui/
│       ├── pixel_font.py              # Özel 5x7 piksel-sanatı bitmap yazı tipi motoru
│       ├── hud.py                     # [F1]-[F4] telemetri paneli ve düşük çözünürlüklü debug arayüzü
│       └── modern_overlay.py          # 1280x720 Modern HD Türkçe arayüz, diyalog kutusu ve pusula
└── tests/
    └── test_procgen.py                # 17 kapsamlı determinizm, ODTÜ Bilim Ağacı, Hikaye ve Modern HD arayüz testi
```

<p align="center">
  <img src="docs/banners/section_divider_autumn.png" alt="Autumn Leaf Divider" width="100%" />
</p>

## 🚀 8. Hızlı Başlangıç & Doğrulama Testleri

### 1. Kurulum

```bash
# Depoyu klonlayın ve dizine girin
git clone https://github.com/bahattinyunus/kodtu-autumn-procgen.git
cd kodtu-autumn-procgen

# Gerekli kütüphaneleri yükleyin (Python 3.10+)
pip install -r requirements.txt
```

### 2. Oyunu Çalıştırma (Standart & ODTÜ Özel Tohumlarıyla)

```bash
# Varsayılan KODTÜ 2026 tohumu ve Modern Hikaye Modu ile başlatın
python src/main.py --seed "KODTU2026"

# ODTÜ Devrim Stadyumu Korusu tohumu ile başlatın
python src/main.py --seed "ODTU-1956-DEVRIM"

# ODTÜ Bilim Ağacı Anıtı tohumu ile başlatın
python src/main.py --seed "METU-BILIM-AGACI"
```

### 3. Otomatik Test Paketi (`pytest`)

Motorun determinizmini, `%100` mağara bağlantılılığını (sıfır yetim oda), Bridson Poisson Disk minimum mesafe garantisini, ODTÜ Bilim Ağacı Anıtı sentezini, *Hyper Light Drifter* tarzı Solar Bolt & Mermi Yansıtma (`DEFLECT!`) mekaniğini, parçalanabilir flora/palamut ganimetlerini, Türkçe Hikaye Bölümlerini, 1280x720 Modern HD arayüzü ve 16-renk Sonbahar LUT kısıtlamasını doğrulayan **17 birim testini** çalıştırın:

```bash
pytest tests/ -v
```

```text
tests/test_procgen.py::test_seed_serialization_and_xoshiro256_determinism PASSED
tests/test_procgen.py::test_multi_octave_simplex_fbm_bounds PASSED
tests/test_procgen.py::test_topology_single_component_connectivity_and_dijkstra[KODTU2026] PASSED
tests/test_procgen.py::test_topology_single_component_connectivity_and_dijkstra[KODTU-8492-FALL] PASSED
tests/test_procgen.py::test_topology_single_component_connectivity_and_dijkstra[AUTUMN-JAM-01] PASSED
tests/test_procgen.py::test_topology_single_component_connectivity_and_dijkstra[SONBAHAR-1923] PASSED
tests/test_procgen.py::test_topology_single_component_connectivity_and_dijkstra[PIXEL-FOREST] PASSED
tests/test_procgen.py::test_47_tile_blob_autotiling_lut PASSED
tests/test_procgen.py::test_poisson_disk_sampling_exclusion_zone PASSED
tests/test_procgen.py::test_full_world_pipeline_determinism PASSED
tests/test_procgen.py::test_autumn_chromatic_palette_compliance PASSED
tests/test_procgen.py::test_headless_engine_and_debug_overlays PASSED
tests/test_procgen.py::test_astar_and_procedural_structures PASSED
tests/test_procgen.py::test_odtu_bilim_agaci_monument_and_curated_seeds PASSED
tests/test_procgen.py::test_solar_bolts_boons_and_orb_deflection PASSED
tests/test_procgen.py::test_destructible_props_and_codex_modal PASSED
... 16 passed in 1.35s
```

<div align="center">
  <br />
  <p><b>🍁 Orta Doğu Teknik Üniversitesi (ODTÜ / METU) — KODTÜ Game Jam için sevgi, matematik ve piksel-sanatıyla geliştirilmiştir. 🍁</b></p>
</div>