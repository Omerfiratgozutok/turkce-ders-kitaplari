# Türkçe Ders Kitapları

MEB ders kitaplarının derli toplu, indirilebilir arşivi.

MEB kitapları zaten ücretsiz — ama tek tek, tıklaya tıklaya indiriliyor ve
müfredat değişince eskileri siteden kalkıyor. Bu depo iki şeyi çözüyor:
**toplu indirme** ve **arşivleme**.

> ChinaTextbook projesinden esinlenilmiştir. Oradaki sorun kitapların
> ücretsiz olmamasıydı; buradaki sorun dağınık ve kalıcı olmamaları.

## Kapsam

**13 kitap · 14 PDF · 759 MB**  ·  Kaynak: [OGM Materyal](https://ogmmateryal.eba.gov.tr) (MEB)  ·  Güncelleme: 2026-08-09

Şu an pilot kapsam **lise matematik**. Diğer dersler ve seviyeler sırada —
altyapı hazır, tek yapılması gereken kazıyıcıya ders eklemek.

### Matematik

| Sınıf | Cilt | Boyut | Kaynak |
|---|---|---|---|
| Hazırlık | 1 | 62.1 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=23&d=208&u=0&k=0) |
| 9. Sınıf | 2 | 107.5 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=21&d=204&u=0&k=0) |
| 10. Sınıf | 1 | 85.1 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=22&d=220&u=0&k=0) |
| 11. Sınıf | 1 | 68.3 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=8&d=50&u=0&k=0) |
| 12. Sınıf | 1 | 47.2 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=9&d=51&u=0&k=0) |
| 9. Sınıf (2017-23 Müfredatı) | 1 | 51.9 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=6&d=48&u=0&k=0) |
| 10. Sınıf (2017-23 Müfredatı) | 1 | 75.4 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik?s=7&d=49&u=0&k=0) |

### Matematik (Fen Lisesi)

| Sınıf | Cilt | Boyut | Kaynak |
|---|---|---|---|
| 11. Sınıf | 1 | 50.9 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/fl-matematik?s=8&d=30&u=0&k=0) |
| 12. Sınıf | 1 | 58.6 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/fl-matematik?s=9&d=31&u=0&k=0) |
| 9. Sınıf (2017-23 Müfredatı) | 1 | 28.5 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/fl-matematik?s=6&d=28&u=0&k=0) |
| 10. Sınıf (2017-23 Müfredatı) | 1 | 39.9 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/fl-matematik?s=7&d=29&u=0&k=0) |

### Matematik (Temel Duzey)

| Sınıf | Cilt | Boyut | Kaynak |
|---|---|---|---|
| 11. Sınıf | 1 | 49.5 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik-temel-duzey?s=8&d=52&u=0&k=0) |
| 12. Sınıf | 1 | 34.3 MB | [OGM](https://ogmmateryal.eba.gov.tr/etkilesimli-kitap/matematik-temel-duzey?s=9&d=53&u=0&k=0) |

## Kullanım

Bağımlılık yok, sadece Python 3 yeterli.

```bash
git clone https://github.com/Omerfiratgozutok/turkce-ders-kitaplari.git
cd turkce-ders-kitaplari

python3 indir.py --liste          # neler var, indirmeden gör
python3 indir.py                  # hepsini indir (~759 MB)
```

### Seçerek indirme

```bash
python3 indir.py --sinif 9 --sinif 10       # sadece 9 ve 10. sınıf
python3 indir.py --ders matematik           # tek ders
python3 indir.py --guncel                   # eski müfredat kitaplarını atla
python3 indir.py --hedef ~/Kitaplar         # başka klasöre
```

Kitaplar `kitaplar/lise/9-sinif/matematik/...` düzeninde klasörlenir.

### İndirme yarıda kalırsa

Komutu tekrar çalıştırman yeterli. Yarım dosyalar `HTTP Range` ile kaldığı
yerden devam eder, tamamlananlar atlanır. Her PDF indikten sonra hem boyut
hem `%PDF-` imzası kontrol edilir — bozuk dosya diske yazılmaz.

## Arşivi güncelleme

MEB kitapları değiştirdiğinde metadata'yı yenilemek için:

```bash
python3 scraper/kesif.py                    # data/kitaplar.json'u yeniler
python3 scraper/readme_uret.py              # bu README'yi yeniler
```

Yeni ders eklemek için `scraper/kesif.py` içindeki `VARSAYILAN_DERSLER`
sözlüğüne OGM Materyal slug'ını ekle (`fizik`, `kimya`, `biyoloji`, ...):

```bash
python3 scraper/kesif.py fizik kimya biyoloji
```

## Depo yapısı

```
turkce-ders-kitaplari/
├── indir.py                 # toplu indirici (CLI)
├── data/kitaplar.json       # kitap metadata'sı — tek doğruluk kaynağı
├── scraper/
│   ├── kesif.py             # OGM Materyal kazıyıcı
│   └── readme_uret.py       # bu dosyayı üretir
├── MIMARI.md                # iç işleyiş + akış diyagramları
└── kitaplar/                # indirilen PDF'ler (git'e dahil değil)
```

Kodun nasıl çalıştığı, kazıma zinciri ve indiricinin durum makinesi için:
**[MIMARI.md](MIMARI.md)**

PDF'ler bilerek depoda tutulmuyor. Onlarca GB'lık bir git geçmişi klonlanamaz
hale gelirdi; metadata + indirici ile hem depo hafif kalıyor hem de aynı
"tek komutla hepsini indir" deneyimi sağlanıyor.

## Telif ve sorumluluk

Bu depoda **hiçbir PDF barındırılmıyor**. Depo yalnızca MEB'in kendi
sunucularındaki (https://ogmmateryal.eba.gov.tr) herkese açık dosyalara işaret eden metadata ve bu
dosyaları indiren bir araç içeriyor. İndirme, MEB sunucusundan doğrudan
yapılır.

Kitapların telif hakkı **T.C. Millî Eğitim Bakanlığı**'na aittir ve MEB
tarafından ücretsiz dağıtılmaktadır. Bu depo MEB ile bağlantılı değildir,
MEB tarafından desteklenmemektedir.

Bu depodaki **kod** MIT lisanslıdır.

## Katkı

Eksik ders, bozuk link veya yanlış eşleşme gördüysen issue aç. Yeni ders
kapsamı eklemek en çok işe yarayan katkı — `kesif.py`'ye slug eklemek
çoğu zaman yeterli oluyor.
