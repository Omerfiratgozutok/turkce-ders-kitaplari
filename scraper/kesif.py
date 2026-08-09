#!/usr/bin/env python3
"""OGM Materyal (ogmmateryal.eba.gov.tr) ders kitabi kesif araci.

Ders sayfalarini gezer, her sinif icin kitap sayfasini acar, PDF ciltlerini
ve boyutlarini cikarir, data/kitaplar.json dosyasina yazar.

Bagimlilik yok - sadece Python standart kutuphanesi.

Kullanim:
    python3 scraper/kesif.py                  # varsayilan dersler
    python3 scraper/kesif.py matematik fizik  # secili dersler
"""

import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TABAN = "https://ogmmateryal.eba.gov.tr"
KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "data" / "kitaplar.json"

# Pilot kapsam: lise matematik. Yeni ders eklemek icin slug eklemek yeterli.
VARSAYILAN_DERSLER = {
    "matematik": "Matematik",
    "matematik-temel-duzey": "Matematik (Temel Duzey)",
    "fl-matematik": "Matematik (Fen Lisesi)",
}

BASLIKLAR = {
    "User-Agent": "turkce-ders-kitaplari/0.1 (+https://github.com/TapXWorld/ChinaTextbook benzeri arsiv projesi)"
}

# Kart bloklarini ayirmak icin: her kart bir <a href="/etkilesimli-kitap/..."> ile baslar
KART = re.compile(
    r'href="(/etkilesimli-kitap/[^"]*?\?s=\d+[^"]*)".*?<h4>(.*?)</h4>',
    re.DOTALL,
)
PDF = re.compile(r'href="(https://ogmmateryal\.eba\.gov\.tr/panel/upload/pdf/[a-z0-9]+\.pdf)"')


def getir(url, deneme=3):
    """Sayfayi metin olarak indirir, gecici hatalarda tekrar dener."""
    for i in range(deneme):
        try:
            istek = urllib.request.Request(url, headers=BASLIKLAR)
            with urllib.request.urlopen(istek, timeout=45) as y:
                return y.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as e:
            if i == deneme - 1:
                raise
            print(f"    ! {e} - tekrar deneniyor ({i + 2}/{deneme})", file=sys.stderr)
            time.sleep(2 * (i + 1))


def boyut_al(url):
    """PDF boyutunu HEAD istegiyle ogrenir. Basarisiz olursa None doner."""
    try:
        istek = urllib.request.Request(url, headers=BASLIKLAR, method="HEAD")
        with urllib.request.urlopen(istek, timeout=30) as y:
            uzunluk = y.headers.get("Content-Length")
            return int(uzunluk) if uzunluk else None
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def temizle(metin):
    """HTML varliklarini cozer ve fazla bosluklari siler."""
    return re.sub(r"\s+", " ", html.unescape(metin)).strip()


def sinif_no(baslik):
    """'10. Sinif (2017-23 Mufredati)' -> 10. Bulunamazsa None."""
    m = re.match(r"\s*(\d+)\s*\.", baslik)
    return int(m.group(1)) if m else None


def eski_mufredat(baslik):
    return "mufredat" in baslik.lower().replace("ü", "u")


def ders_tara(slug, ders_adi):
    """Bir dersin tum sinif/kitap kayitlarini dondurur."""
    print(f"\n[{ders_adi}] /etkilesimli-kitaplar/{slug}")
    try:
        sayfa = getir(f"{TABAN}/etkilesimli-kitaplar/{slug}")
    except Exception as e:
        print(f"  HATA: ders sayfasi alinamadi - {e}", file=sys.stderr)
        return []

    kartlar = []
    for yol, baslik in KART.findall(sayfa):
        baslik = temizle(baslik)
        # Menu/modal basliklarini ele: sadece "N. Sinif" veya "Hazirlik" kalsin
        if sinif_no(baslik) is None and "azırlık" not in baslik and "azirlik" not in baslik:
            continue
        kartlar.append((html.unescape(yol), baslik))

    # Ayni (yol, baslik) ciftini tekrarlama
    gorulen, benzersiz = set(), []
    for k in kartlar:
        if k not in gorulen:
            gorulen.add(k)
            benzersiz.append(k)

    print(f"  {len(benzersiz)} sinif karti bulundu")

    kayitlar = []
    for yol, baslik in benzersiz:
        url = TABAN + yol
        try:
            kitap_sayfasi = getir(url)
        except Exception as e:
            print(f"  ! {baslik}: sayfa alinamadi - {e}", file=sys.stderr)
            continue

        # Ayni PDF birden cok unitede tekrarlanir; ilk gorunme sirasi cilt sirasidir
        ciltler, gorulen_pdf = [], set()
        for pdf_url in PDF.findall(kitap_sayfasi):
            if pdf_url not in gorulen_pdf:
                gorulen_pdf.add(pdf_url)
                ciltler.append(pdf_url)

        if not ciltler:
            print(f"  ! {baslik}: PDF bulunamadi ({url})", file=sys.stderr)
            continue

        cilt_kayitlari = []
        for i, pdf_url in enumerate(ciltler, 1):
            boyut = boyut_al(pdf_url)
            cilt_kayitlari.append(
                {
                    "cilt": i,
                    "url": pdf_url,
                    "boyut_bayt": boyut,
                    "dosya_adi": dosya_adi_uret(slug, baslik, i, len(ciltler)),
                }
            )
            time.sleep(0.3)

        toplam_mb = sum(c["boyut_bayt"] or 0 for c in cilt_kayitlari) / 1048576
        print(f"  + {baslik}: {len(ciltler)} cilt, {toplam_mb:.1f} MB")

        kayitlar.append(
            {
                "ders": ders_adi,
                "ders_slug": slug,
                "seviye": "lise",
                "sinif": sinif_no(baslik),
                "sinif_etiketi": baslik,
                "eski_mufredat": eski_mufredat(baslik),
                "yayinevi": "MEB",
                "kaynak_sayfa": url,
                "ciltler": cilt_kayitlari,
            }
        )
        time.sleep(0.5)

    return kayitlar


def dosya_adi_uret(slug, baslik, cilt, toplam_cilt):
    """9-sinif-matematik-meb-cilt1.pdf gibi duzgun bir ad uretir."""
    sn = sinif_no(baslik)
    parca = f"{sn}-sinif" if sn else "hazirlik"
    if eski_mufredat(baslik):
        parca += "-2017mufredat"
    ad = f"{parca}-{slug}-meb"
    if toplam_cilt > 1:
        ad += f"-cilt{cilt}"
    return ad + ".pdf"


def main():
    istenen = sys.argv[1:]
    dersler = (
        {s: VARSAYILAN_DERSLER.get(s, s.replace("-", " ").title()) for s in istenen}
        if istenen
        else VARSAYILAN_DERSLER
    )

    tum_kayitlar = []
    for slug, ad in dersler.items():
        tum_kayitlar.extend(ders_tara(slug, ad))

    tum_kayitlar.sort(key=lambda k: (k["ders_slug"], k["eski_mufredat"], k["sinif"] or 0))

    toplam_cilt = sum(len(k["ciltler"]) for k in tum_kayitlar)
    toplam_bayt = sum(c["boyut_bayt"] or 0 for k in tum_kayitlar for c in k["ciltler"])

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(
        json.dumps(
            {
                "kaynak": TABAN,
                "guncelleme": time.strftime("%Y-%m-%d"),
                "kitap_sayisi": len(tum_kayitlar),
                "cilt_sayisi": toplam_cilt,
                "toplam_bayt": toplam_bayt,
                "kitaplar": tum_kayitlar,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"\n{'=' * 55}\n"
        f"{len(tum_kayitlar)} kitap / {toplam_cilt} cilt / {toplam_bayt / 1048576:.0f} MB\n"
        f"-> {CIKTI.relative_to(KOK)}"
    )


if __name__ == "__main__":
    main()
