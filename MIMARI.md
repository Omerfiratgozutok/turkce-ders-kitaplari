# Mimari — Repo Nasıl Çalışır?

Bu belge deponun iç işleyişini anlatır. Kullanım için [README.md](README.md)'ye bak.

---

## 1. Temel fikir: iki fazlı tasarım

Projenin tek önemli mimari kararı şu: **metadata toplamak** ile **bayt indirmek**
birbirinden ayrıldı.

```mermaid
flowchart LR
    subgraph FAZ1["FAZ 1 — Keşif (yavaş, seyrek)"]
        A["OGM Materyal<br/>web sayfaları"] -->|"HTML kazıma"| B["kesif.py"]
        B --> C[("data/kitaplar.json<br/>~10 KB")]
    end

    subgraph FAZ2["FAZ 2 — İndirme (hızlı, sık)"]
        C --> D["indir.py"]
        D -->|"doğrudan HTTP"| E["MEB sunucusu"]
        E --> F["kitaplar/*.pdf<br/>759 MB"]
    end

    C -.->|"README üret"| G["readme_uret.py"]
    G -.-> H["README.md"]

    style C fill:#2d6a4f,color:#fff
    style F fill:#1d3557,color:#fff
```

**Neden ayrı?** Üç sebep:

| Sebep | Açıklama |
|---|---|
| **Hız** | Keşif ~40 saniye sürüyor (30+ HTTP isteği). Kullanıcı her indirmede bunu beklemek zorunda değil. |
| **Kırılganlık izolasyonu** | MEB HTML'i değiştirirse sadece `kesif.py` bozulur. `indir.py` JSON'a bakar, HTML'e değil. |
| **Denetlenebilirlik** | `kitaplar.json` git'te versiyonlanıyor. MEB bir kitabı sessizce değiştirdiğinde diff'te görünür. |

Bu ayrım aynı zamanda deponun **hiç PDF barındırmamasını** mümkün kılıyor:
repoda sadece 10 KB'lık bir işaretçi dosyası var, baytlar kullanıcının
makinesine MEB'den doğrudan iniyor.

---

## 2. Faz 1 — `scraper/kesif.py`

### Kazıma zinciri

OGM Materyal'de bir PDF'e ulaşmak için üç seviye inmek gerekiyor:

```mermaid
flowchart TD
    L1["/etkilesimli-kitaplar<br/><i>ders listesi</i>"]
    L2["/etkilesimli-kitaplar/matematik<br/><i>sınıf kartları</i>"]
    L3["/etkilesimli-kitap/matematik?s=21&d=204<br/><i>ünite listesi</i>"]
    PDF["/panel/upload/pdf/xarxnz5n30i.pdf<br/><i>gerçek dosya</i>"]

    L1 -->|"slug: matematik,<br/>fizik, kimya..."| L2
    L2 -->|"KART regex →<br/>7 kart"| L3
    L3 -->|"PDF regex →<br/>7 eşleşme, 2 benzersiz"| PDF

    style PDF fill:#2d6a4f,color:#fff
```

Kod sadece **L2'den** başlıyor — ders slug'ları `VARSAYILAN_DERSLER` sözlüğünde
elle tutuluyor. Sebep: L1'i kazımak 60+ dersin hepsini getirirdi, oysa kapsamı
bilinçli olarak dar tutuyoruz.

### Adım adım işleyiş

```mermaid
sequenceDiagram
    participant K as kesif.py
    participant S as OGM sunucusu
    participant J as kitaplar.json

    loop her ders slug'ı için
        K->>S: GET /etkilesimli-kitaplar/{slug}
        S-->>K: HTML "sınıf kartları"
        Note over K: KART regex → [href, başlık] çiftleri<br/>menü/modal başlıklarını ele<br/>tekrarları temizle

        loop her sınıf kartı için
            K->>S: GET /etkilesimli-kitap/{slug}?s=..&d=..
            S-->>K: HTML "ünite listesi"
            Note over K: PDF regex → N eşleşme<br/>sırayı koruyarak tekilleştir<br/>= ciltler

            loop her cilt için
                K->>S: HEAD /panel/upload/pdf/{slug}.pdf
                S-->>K: Content-Length
                Note over K: 0.3 sn bekle
            end
            Note over K: 0.5 sn bekle
        end
    end

    K->>J: kayıtları sırala ve yaz
```

Aradaki `sleep`'ler bilinçli: MEB sunucusuna saniyede onlarca istek atmıyoruz.
Toplam ~30 istek, ~40 saniye.

### İki kritik regex

**`KART`** — sınıf kartını başlığıyla eşleştirir:

```python
r'href="(/etkilesimli-kitap/[^"]*?\?s=\d+[^"]*)".*?<h4>(.*?)</h4>'
```

HTML'de `<a href="...">` ile `<h4>9. Sınıf</h4>` arasında birkaç `div` var.
`.*?` (tembel eşleşme) + `re.DOTALL` ile aradaki her şeyi atlıyoruz. Tembel
olması şart — açgözlü olsaydı ilk href'i **son** h4 ile eşleştirirdi.

Bu regex menüdeki `<h5>Menü</h5>` gibi alakasız başlıkları da yakalayabilir,
o yüzden arkasından bir filtre var: başlık ya `N.` ile başlamalı ya da
"Hazırlık" içermeli.

**`PDF`** — dosya bağlantısını çeker:

```python
r'href="(https://ogmmateryal\.eba\.gov\.tr/panel/upload/pdf/[a-z0-9]+\.pdf)"'
```

Slug'lar (`xarxnz5n30i`) rastgele — tahmin edilemez, üretilemez. Kazımak tek yol.

### Cilt tespiti: en can alıcı nokta

Sayfa kitabı **ünite ünite** listeliyor, ama her ünitenin yanına o ünitenin ait
olduğu **cildin tamamını** koyuyor:

```mermaid
flowchart LR
    subgraph SAYFA["9. Sınıf Matematik sayfası"]
        U1["Ünite 1"] --> P1["xarxnz5n30i.pdf"]
        U2["Ünite 2"] --> P1
        U3["Ünite 3"] --> P1
        U4["Ünite 4"] --> P2["ssq4n1cqcle.pdf"]
        U5["Ünite 5"] --> P2
        U6["Ünite 6"] --> P2
        U7["Ünite 7"] --> P2
    end

    P1 --> C1["Cilt 1<br/>58.1 MB"]
    P2 --> C2["Cilt 2<br/>49.4 MB"]

    style C1 fill:#2d6a4f,color:#fff
    style C2 fill:#2d6a4f,color:#fff
```

Yani 7 link → 2 dosya. Kod **sırayı koruyarak tekilleştiriyor**:

```python
ciltler, gorulen_pdf = [], set()
for pdf_url in PDF.findall(kitap_sayfasi):
    if pdf_url not in gorulen_pdf:
        gorulen_pdf.add(pdf_url)
        ciltler.append(pdf_url)
```

`set()` tek başına kullanılsaydı sıra kaybolur, cilt 1 ile cilt 2 rastgele
yer değiştirirdi. Liste + set kombinasyonu hem tekilliği hem sırayı korur —
sayfadaki ilk görünme sırası = cilt sırası.

### Veri modeli

```mermaid
erDiagram
    KOK ||--o{ KITAP : "kitaplar[]"
    KITAP ||--o{ CILT : "ciltler[]"

    KOK {
        string kaynak
        string guncelleme
        int kitap_sayisi
        int cilt_sayisi
        int toplam_bayt
    }
    KITAP {
        string ders "Matematik"
        string ders_slug "matematik — filtre anahtarı"
        string seviye "lise"
        int sinif "9 — filtre anahtarı"
        string sinif_etiketi "9. Sınıf (2017-23 Müfredatı)"
        bool eski_mufredat "--guncel filtresi"
        string yayinevi "MEB"
        string kaynak_sayfa "izlenebilirlik için"
    }
    CILT {
        int cilt "1, 2"
        string url "indirilecek adres"
        int boyut_bayt "doğrulama + devam ettirme"
        string dosya_adi "9-sinif-matematik-meb-cilt1.pdf"
    }
```

`boyut_bayt` sadece bilgi değil — indiricinin **doğrulama ve devam ettirme**
mekanizması buna dayanıyor.

`dosya_adi` keşif anında üretiliyor, indirme anında değil. Böylece dosya adı da
versiyonlanmış veri oluyor: adlandırma mantığı değişirse diff'te görünür.

---

## 3. Faz 2 — `indir.py`

### Genel akış

```mermaid
flowchart TD
    A["kitaplar.json oku"] --> B{"filtreler"}
    B -->|"--sinif"| B
    B -->|"--ders"| B
    B -->|"--guncel"| B
    B --> C{"--liste?"}
    C -->|evet| D["tabloyu yazdır, çık"]
    C -->|hayır| E["kitap × cilt<br/>düzleştir"]
    E --> F["her cilt için:<br/>klasör oluştur"]
    F --> G["indir()"]
    G --> H["sayaç: indirildi /<br/>atlandı / hata"]
    H --> I{"hata var mı?"}
    I -->|evet| J["exit 1"]
    I -->|hayır| K["exit 0"]

    style D fill:#1d3557,color:#fff
    style J fill:#7f1d1d,color:#fff
    style K fill:#2d6a4f,color:#fff
```

`exit 1` bilinçli: bu betiği bir cron/CI içinde çalıştırırsan başarısızlığı
otomatik yakalayabilirsin.

### `indir()` — durum makinesi

Fonksiyonun asıl karmaşıklığı burada. Her cilt için:

```mermaid
stateDiagram-v2
    [*] --> HedefVarMi

    HedefVarMi --> BoyutTam: hedef.pdf var
    HedefVarMi --> ParcaKontrol: hedef yok

    BoyutTam --> ATLANDI: boyut eşleşiyor
    BoyutTam --> Sil: boyut tutmuyor
    Sil --> ParcaKontrol

    ParcaKontrol --> Tasi: .part tam boyutta
    ParcaKontrol --> ParcaSil: .part fazla büyük
    ParcaKontrol --> Istek: .part yarım ya da yok
    ParcaSil --> Istek
    Tasi --> INDIRILDI

    Istek --> Range: .part var
    Istek --> Bastan: .part yok
    Range --> Yanit
    Bastan --> Yanit

    Yanit --> Bastan: 206 beklenirken 200 geldi
    Yanit --> Yaz: akış başladı

    Yaz --> Dogrula: akış bitti
    Dogrula --> HATA_R: boyut eksik
    Dogrula --> HATA_R: PDF imzası yok
    Dogrula --> Rename: her ikisi tamam

    Rename --> INDIRILDI
    HATA_R --> Istek: 3 denemeden az
    HATA_R --> HATA: 3 deneme bitti

    ATLANDI --> [*]
    INDIRILDI --> [*]
    HATA --> [*]
```

Bu makinenin çözdüğü gerçek problemler:

| Durum | Ne olur |
|---|---|
| Aynı komut ikinci kez çalıştırıldı | Boyut eşleşir → `ATLANDI`. İdempotent. |
| İndirme %60'ta kesildi | `.part` kalır, sonraki çalıştırma `Range: bytes=X-` ile kaldığı yerden devam eder. |
| Sunucu `Range`'i yok saydı | Yanıt 206 yerine 200 gelir → kod fark eder, `.part`'ı silip baştan başlar. |
| MEB hata sayfası döndü | `%PDF-` imzası tutmaz → dosya silinir, tekrar denenir. |
| MEB kitabı güncelledi (boyut değişti) | Mevcut dosya boyutu tutmaz → silinir, yenisi iner. |
| Ağ koptu | 3 deneme, artan bekleme (2s, 4s). |

### Atomik yazma

Kritik ayrıntı: indirme **hiçbir zaman** doğrudan hedef dosyaya yazmaz.

```mermaid
flowchart LR
    A["ağdan gelen<br/>baytlar"] --> B["kitap.pdf.part"]
    B --> C{"boyut + imza<br/>doğru mu?"}
    C -->|hayır| D["sil / tekrar dene"]
    C -->|evet| E["rename →<br/>kitap.pdf"]

    style E fill:#2d6a4f,color:#fff
    style D fill:#7f1d1d,color:#fff
```

`rename` işletim sistemi düzeyinde atomiktir. Sonuç: `kitap.pdf` adlı bir dosya
diskte varsa, **kesinlikle** eksiksiz ve doğrulanmıştır. Yarım PDF diye bir şey
oluşamaz. `.part` uzantısı da `.gitignore`'da — kaza eseri commit edilemez.

### Doğrulama neden iki katmanlı?

```python
if gecici.stat().st_size != beklenen_boyut:   # 1. katman
    raise OSError("eksik indirme")
if f.read(5) != b"%PDF-":                      # 2. katman
    raise OSError("gelen dosya PDF degil")
```

Boyut kontrolü **eksik** indirmeyi yakalar. İmza kontrolü **yanlış içeriği**
yakalar — MEB bir gün 34 MB'lık bir HTML hata sayfası döndürürse boyut kontrolü
bunu geçirebilir, imza kontrolü geçirmez.

### Çıktı klasör düzeni

```
kitaplar/
└── lise/                        ← k["seviye"]
    ├── 9-sinif/                 ← k["sinif"]
    │   ├── matematik/           ← k["ders_slug"]
    │   │   ├── 9-sinif-matematik-meb-cilt1.pdf
    │   │   └── 9-sinif-matematik-meb-cilt2.pdf
    │   └── fl-matematik/
    └── 12-sinif/
```

Klasör yolu JSON alanlarından türetiliyor — kodda sabit yol yok. Ortaokul
eklendiğinde `seviye: "ortaokul"` yazmak yeterli, indiriciye dokunmaya gerek yok.

---

## 4. `scraper/readme_uret.py`

README elle yazılmıyor, üretiliyor. Sebep: kapsam 13 kitaptan 300 kitaba
çıktığında elle güncellenen bir tablo kaçınılmaz olarak yanlışa düşer.

```mermaid
flowchart LR
    A[("kitaplar.json")] --> B["derse göre grupla"]
    B --> C["sınıfa göre sırala<br/>eski müfredat sona"]
    C --> D["markdown tablo"]
    D --> E["SABLON.format()"]
    E --> F["README.md"]

    style F fill:#2d6a4f,color:#fff
```

Sayılar (`13 kitap`, `759 MB`) da şablona JSON'dan geliyor — hiçbir rakam
iki yerde tutulmuyor.

---

## 5. Bağımlılık politikası

Üç betik de **yalnızca Python standart kütüphanesi** kullanıyor:
`urllib`, `re`, `json`, `html`, `argparse`, `pathlib`.

`requests` + `beautifulsoup4` kodu belki %20 kısaltırdı. Karşılığında kullanıcı
`pip install` yapmak zorunda kalırdı. Bu deponun hedef kitlesi öğrenciler ve
öğretmenler — `git clone` + `python3 indir.py` iki adımda bitmeli.

HTML'i regex ile ayrıştırmak genelde kötü bir fikirdir; burada kabul edilebilir
çünkü hedef desenler çok dar ve spesifik (tek bir domain, iki sabit URL kalıbı).
Kırılırsa gürültülü kırılır: `kesif.py` "PDF bulunamadı" der, sessizce yanlış
veri üretmez.

---

## 6. Genişletme noktaları

| Ne eklemek istiyorsun | Nereye dokunacaksın |
|---|---|
| Yeni lise dersi (fizik, kimya...) | `kesif.py` → `VARSAYILAN_DERSLER` sözlüğü. Başka hiçbir yer. |
| Ortaokul / ilkokul | Yeni bir kazıyıcı modülü. OGM sadece ortaöğretim — ayrı kaynak gerekli. Çıktı aynı JSON şemasına uyduğu sürece `indir.py` değişmez. |
| Paralel indirme | `indir.py` → `main()` içindeki döngü. Dikkat: MEB sunucusunu yormamak için 2-3 eşzamanlı istekle sınırla. |
| Checksum doğrulama | `kesif.py` → cilt kaydına `sha256` alanı; `indir.py` → `Dogrula` adımına ekle. Boyut kontrolünden daha güçlü olur. |
| Değişiklik takibi | `kitaplar.json` zaten git'te. Bir CI işi haftalık `kesif.py` çalıştırıp diff varsa issue açabilir. |

---

## 7. Bilinen sınırlar

- **OGM = Ortaöğretim.** İlkokul ve ortaokul kitapları bu kaynakta yok.
- **Ders slug'ları elle.** Yeni bir ders MEB'e eklenirse kendiliğinden gelmez.
- **HTML'e bağımlılık.** MEB şablonu değiştirirse `kesif.py` güncellenmeli.
  `indir.py` etkilenmez — mevcut JSON ile çalışmaya devam eder.
- **Checksum yok.** Şu an sadece boyut + PDF imzası doğrulanıyor. MEB bir kitabı
  aynı boyutta değiştirirse fark edilmez.
- **Tek iş parçacığı.** 759 MB, ~2.5 MB/s ile yaklaşık 5 dakika.
