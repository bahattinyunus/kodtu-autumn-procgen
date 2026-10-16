# 🍂 KODTÜ: Autumn ProcGen Engine — Mimari ve Algoritmik Spesifikasyon

Bu belge, `kodtu-autumn-procgen` motorunun 6 aşamalı deterministik Prosedürel İçerik Üretimi (PCG) boru hattını, 47-Tile Blob Bitmasking eşleme mantığını ve Verlet entegrasyonlu yaprak fiziğini detaylandırır.

---

## 1. 64-Bit Tohum Serileştirme ve Alt-Sistem İzolasyonu (`src/procgen/prng.py`)

Oyun dünyası rastgeleliğini Python'un global `random` modülünden değil, tamamen deterministik **`Xoshiro256**`** ve **`SplitMix64`** algoritmalarından alır:

1. Kullanıcının girdiği herhangi bir metin (`"KODTU2026"` veya `"KODTU-8492-FALL"`), **64-bit FNV-1a** özeti alındıktan sonra **SplitMix64** çığ (avalanche) fonksiyonundan geçirilerek tek bir `uint64` tam sayıya dönüştürülür.
2. Ana üreteç (`root_prng`), her alt sistem için `root_prng.fork(subsystem_salt)` çağrısıyla bağımsız alt üreteçler oluşturur:
   - `elevation` (Yükseklik fBm Gürültüsü)
   - `moisture` (Nem ve Çürüme fBm Gürültüsü)
   - `topology` (Cellular Automata & Drunkard's Walk Koridor Açıcı)
   - `poisson` (Bridson Poisson Disk Örneklemesi)
   - `threat_budget` (Dijkstra Tehdit ve Yadigâr Dağıtımı)
   - `wind` (2D Rüzgâr Vektör Alanı)

Bu izolasyon sayesinde partikül sayısının veya ses efektlerinin değişmesi, harita topolojisini veya ağaç konumlarını asla etkilemez.

---

## 2. 47-Tile Blob Bitmasking Matematiği (`src/procgen/autotile.py`)

Bir hücrenin 8 komşusu (`NW=1, N=2, NE=4, W=8, E=16, SW=32, S=64, SE=128`) okunduğunda $2^8 = 256$ olası durum ortaya çıkar. Ancak diyagonal bir köşenin (`NW`, `NE`, `SW`, `SE`) görsel geçişi yalnızca kendisine komşu olan **her iki ana yön de (`N/S` ve `E/W`) dolu olduğunda** anlamlıdır:

```text
NW korunur <==> (N == 1) ve (W == 1)
NE korunur <==> (N == 1) ve (E == 1)
SW korunur <==> (S == 1) ve (W == 1)
SE korunur <==> (S == 1) ve (E == 1)
```

Bu sadeleştirme fonksiyonu (`sanitize_blob_mask`) uygulandığında 256 durum tam olarak **47 kanonik bitmask değerine (`0..46`)** indirgenir ve `RAW_TO_47_LUT` tablosu üzerinden $\mathcal{O}(1)$ karmaşıklıkla çizilir.

---

## 3. Dijkstra Uzaklık Alanı ve Tehdit Bütçelemesi (`src/procgen/automata.py` & `pipeline.py`)

Harita üzerinde $B678/S345678$ Hücresel Özdevinim ve BFS Flood-Fill tamamlandıktan sonra, oyuncunun doğduğu merkez açıklıktan (`spawn_tile`) başlayarak tüm geçilebilir karolar üzerinde **Dijkstra Jeodezik Uzaklık Haritası** hesaplanır:

*   Normalize uzaklık $d \in [0.0, 1.0]$ değerine göre:
    *   $d \approx 1.0$ (En uzak açıklık): **Kadim Sonbahar Tapınağı (Ancient Autumn Shrine)** yerleştirilir.
    *   $d \in [0.0, 0.20)$: **Güvenli Başlangıç Açıklığı** (Düşman doğmaz).
    *   $d \in [0.22, 0.95]$: Minimum Öklid ayrımı korunarak 5 adet **Hasat Yadigârı (Amber Relic)** dağıtılır.
    *   Düşman bütçesi (*Spore Wisp* = 1, *Bramble Stalker* = 2, *Hollow Golem* = 3) $d$ arttıkça daha tehlikeli varlıkları seçerek dengeli bir zorluk eğrisi kurar.
