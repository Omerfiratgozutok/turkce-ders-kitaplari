#!/usr/bin/env python3
"""data/kitaplar.json dosyasindan README.md uretir.

Kapsam buyudukce README'yi elle guncellemek zorunda kalmamak icin.

Kullanim:
    python3 scraper/readme_uret.py
"""

import json
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "kitaplar.json"
CIKTI = KOK / "README.md"

SABLON = """# Türkçe Ders Kitapları

MEB ders kitaplarının derli toplu, indirilebilir arşivi.

MEB kitapları zaten ücretsiz — ama tek tek, tıklaya tıklaya indiriliyor ve
müfredat değişince eskileri siteden kalkıyor. Bu depo iki şeyi çözüyor:
**toplu indirme** ve **arşivleme**.

> ChinaTextbook projesinden esinlenilmiştir. Oradaki sorun kitapların
> ücretsiz olmamasıydı; buradaki sorun dağınık ve kalıcı olmamaları.

## Kapsam

**{kitap_sayisi} kitap · {cilt_sayisi} PDF · {toplam_mb:.0f} MB**  ·  Kaynak: [OGM Materyal]({kaynak}) (MEB)  ·  Güncelleme: {guncelleme}

Şu an pilot kapsam **lise matematik**. Diğer dersler ve seviyeler sırada —
altyapı hazır, tek yapılması gereken kazıyıcıya ders eklemek.

{tablolar}
## Kullanım

Bağımlılık yok, sadece Python 3 yeterli.

```bash
git clone https://github.com/<kullanici>/turkce-ders-kitaplari.git
cd turkce-ders-kitaplari

python3 indir.py --liste          # neler var, indirmeden gör
python3 indir.py                  # hepsini indir (~{toplam_mb:.0f} MB)
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
sunucularındaki ({kaynak}) herkese açık dosyalara işaret eden metadata ve bu
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
"""


def mb(bayt):
    return (bayt or 0) / 1048576


def main():
    if not VERI.exists():
        raise SystemExit(f"HATA: {VERI} yok. Once: python3 scraper/kesif.py")

    veri = json.loads(VERI.read_text(encoding="utf-8"))

    gruplar = defaultdict(list)
    for k in veri["kitaplar"]:
        gruplar[k["ders"]].append(k)

    bolumler = []
    for ders in sorted(gruplar):
        kitaplar = sorted(
            gruplar[ders], key=lambda k: (k["eski_mufredat"], k["sinif"] or 0)
        )
        satirlar = [
            f"### {ders}\n",
            "| Sınıf | Cilt | Boyut | Kaynak |",
            "|---|---|---|---|",
        ]
        for k in kitaplar:
            boyut = mb(sum(c["boyut_bayt"] or 0 for c in k["ciltler"]))
            cilt = str(len(k["ciltler"]))
            satirlar.append(
                f"| {k['sinif_etiketi']} | {cilt} | {boyut:.1f} MB | "
                f"[OGM]({k['kaynak_sayfa']}) |"
            )
        bolumler.append("\n".join(satirlar) + "\n")

    CIKTI.write_text(
        SABLON.format(
            kitap_sayisi=veri["kitap_sayisi"],
            cilt_sayisi=veri["cilt_sayisi"],
            toplam_mb=mb(veri["toplam_bayt"]),
            kaynak=veri["kaynak"],
            guncelleme=veri["guncelleme"],
            tablolar="\n".join(bolumler),
        ),
        encoding="utf-8",
    )
    print(f"-> {CIKTI.relative_to(KOK)} ({veri['kitap_sayisi']} kitap)")


if __name__ == "__main__":
    main()
