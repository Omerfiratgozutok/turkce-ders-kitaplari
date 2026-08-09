#!/usr/bin/env python3
"""Turkce Ders Kitaplari - toplu PDF indirici.

data/kitaplar.json icindeki kayitlari kullanarak PDF'leri indirir.
Yarim kalan indirmeler HTTP Range ile kaldigi yerden devam eder.

Bagimlilik yok - sadece Python standart kutuphanesi.

Ornekler:
    python3 indir.py                      # hepsini indir
    python3 indir.py --liste              # indirmeden listele
    python3 indir.py --sinif 9 --sinif 10 # sadece 9 ve 10. sinif
    python3 indir.py --ders matematik     # ders slug'ina gore filtrele
    python3 indir.py --guncel             # eski mufredat kitaplarini atla
    python3 indir.py --hedef ~/Kitaplar   # baska klasore indir
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent
VERI = KOK / "data" / "kitaplar.json"

BASLIKLAR = {"User-Agent": "turkce-ders-kitaplari/0.1"}


def mb(bayt):
    return f"{(bayt or 0) / 1048576:.1f} MB"


def ilerleme(inen, toplam, basla, etiket):
    """Tek satirlik ilerleme cubugu."""
    gecen = max(time.time() - basla, 0.001)
    hiz = inen / gecen / 1048576
    if toplam:
        oran = inen / toplam
        dolu = int(oran * 28)
        cubuk = "#" * dolu + "-" * (28 - dolu)
        sys.stdout.write(f"\r  [{cubuk}] {oran * 100:5.1f}%  {hiz:5.2f} MB/s  {etiket}")
    else:
        sys.stdout.write(f"\r  {mb(inen)} indirildi  {hiz:5.2f} MB/s  {etiket}")
    sys.stdout.flush()


def indir(url, hedef, beklenen_boyut, etiket, deneme=3):
    """Tek dosyayi indirir. Zaten tamsa atlar, yarimsa devam ettirir.

    Doner: "atlandi" | "indirildi" | "hata"
    """
    gecici = hedef.with_suffix(hedef.suffix + ".part")

    if hedef.exists():
        if beklenen_boyut is None or hedef.stat().st_size == beklenen_boyut:
            print(f"  = {etiket} (zaten var, {mb(hedef.stat().st_size)})")
            return "atlandi"
        print(f"  ! {etiket}: boyut tutmuyor, yeniden indiriliyor")
        hedef.unlink()

    for girisim in range(1, deneme + 1):
        basla_bayt = gecici.stat().st_size if gecici.exists() else 0

        # Onceki parca zaten tamsa dogrudan tasi
        if beklenen_boyut and basla_bayt == beklenen_boyut:
            gecici.rename(hedef)
            print(f"  + {etiket} ({mb(beklenen_boyut)})")
            return "indirildi"
        if beklenen_boyut and basla_bayt > beklenen_boyut:
            gecici.unlink()
            basla_bayt = 0

        istek = urllib.request.Request(url, headers=dict(BASLIKLAR))
        if basla_bayt:
            istek.add_header("Range", f"bytes={basla_bayt}-")

        try:
            with urllib.request.urlopen(istek, timeout=60) as yanit:
                # Sunucu Range'i yok saydiysa bastan basla
                if basla_bayt and yanit.status != 206:
                    basla_bayt = 0
                    if gecici.exists():
                        gecici.unlink()

                kalan = yanit.headers.get("Content-Length")
                toplam = (basla_bayt + int(kalan)) if kalan else beklenen_boyut

                inen = basla_bayt
                zaman = time.time()
                son_yazim = 0.0
                kip = "ab" if basla_bayt else "wb"
                with open(gecici, kip) as f:
                    while True:
                        parca = yanit.read(262144)
                        if not parca:
                            break
                        f.write(parca)
                        inen += len(parca)
                        if time.time() - son_yazim > 0.2:
                            ilerleme(inen, toplam, zaman, etiket)
                            son_yazim = time.time()

            sys.stdout.write("\r" + " " * 100 + "\r")

            if beklenen_boyut and gecici.stat().st_size != beklenen_boyut:
                raise OSError(
                    f"eksik indirme: {gecici.stat().st_size} / {beklenen_boyut} bayt"
                )

            # PDF imzasi kontrolu - hata sayfasi inmediginden emin ol
            with open(gecici, "rb") as f:
                if f.read(5) != b"%PDF-":
                    gecici.unlink()
                    raise OSError("gelen dosya PDF degil (muhtemelen hata sayfasi)")

            gecici.rename(hedef)
            print(f"  + {etiket} ({mb(hedef.stat().st_size)})")
            return "indirildi"

        except (urllib.error.URLError, TimeoutError, OSError) as e:
            sys.stdout.write("\r" + " " * 100 + "\r")
            if girisim == deneme:
                print(f"  X {etiket}: {e}", file=sys.stderr)
                return "hata"
            print(f"  ! {etiket}: {e} - tekrar ({girisim + 1}/{deneme})", file=sys.stderr)
            time.sleep(2 * girisim)

    return "hata"


def main():
    p = argparse.ArgumentParser(
        description="MEB lise ders kitaplarini toplu indirir.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Ornekler:")[1],
    )
    p.add_argument("--hedef", default="kitaplar", help="indirme klasoru (varsayilan: ./kitaplar)")
    p.add_argument("--sinif", type=int, action="append", help="sinif filtresi, tekrarlanabilir")
    p.add_argument("--ders", action="append", help="ders slug filtresi, tekrarlanabilir")
    p.add_argument("--guncel", action="store_true", help="eski mufredat kitaplarini atla")
    p.add_argument("--liste", action="store_true", help="indirme, sadece listele")
    args = p.parse_args()

    if not VERI.exists():
        sys.exit(f"HATA: {VERI} yok. Once: python3 scraper/kesif.py")

    veri = json.loads(VERI.read_text(encoding="utf-8"))
    kitaplar = veri["kitaplar"]

    if args.sinif:
        kitaplar = [k for k in kitaplar if k["sinif"] in args.sinif]
    if args.ders:
        kitaplar = [k for k in kitaplar if k["ders_slug"] in args.ders]
    if args.guncel:
        kitaplar = [k for k in kitaplar if not k["eski_mufredat"]]

    if not kitaplar:
        sys.exit("Filtrelere uyan kitap yok.")

    ciltler = [(k, c) for k in kitaplar for c in k["ciltler"]]
    toplam = sum(c["boyut_bayt"] or 0 for _, c in ciltler)

    print(f"{len(kitaplar)} kitap / {len(ciltler)} cilt / {mb(toplam)}")
    print(f"Kaynak: {veri['kaynak']}  (veri: {veri['guncelleme']})\n")

    if args.liste:
        for k, c in ciltler:
            print(f"  {k['ders']:28} {k['sinif_etiketi']:26} {mb(c['boyut_bayt']):>9}  {c['dosya_adi']}")
        return

    hedef_kok = Path(os.path.expanduser(args.hedef)).resolve()
    sayac = {"indirildi": 0, "atlandi": 0, "hata": 0}

    for k, c in ciltler:
        klasor = hedef_kok / k["seviye"] / f"{k['sinif'] or 'hazirlik'}-sinif" / k["ders_slug"]
        klasor.mkdir(parents=True, exist_ok=True)
        etiket = f"{k['ders']} - {k['sinif_etiketi']}" + (
            f" (cilt {c['cilt']})" if len(k["ciltler"]) > 1 else ""
        )
        sonuc = indir(c["url"], klasor / c["dosya_adi"], c["boyut_bayt"], etiket)
        sayac[sonuc] += 1

    print(
        f"\n{'=' * 55}\n"
        f"indirildi: {sayac['indirildi']}  atlandi: {sayac['atlandi']}  hata: {sayac['hata']}\n"
        f"-> {hedef_kok}"
    )
    if sayac["hata"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
