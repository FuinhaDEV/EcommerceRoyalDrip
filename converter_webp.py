#!/usr/bin/env python3
"""
Diagnostica, repara e OTIMIZA as imagens dos produtos do site.

Lê os caminhos "imagem" do produtos.py e, para cada um:
  1. se o .webp existe e é válido -> mantém (e, com --otimizar, reduz se for
     maior que --max-width, que é a principal causa de site lento);
  2. se não existe/está inválido -> procura na mesma pasta o arquivo original
     (ignorando maiúsculas, acentos, espaços e extensões duplicadas como
     "blue star.jpeg.jpg") e gera o .webp com o nome exato que o site espera.

Uso (rode dentro da pasta do projeto, a que tem produtos.py e static/):
    pip install Pillow
    python converter_webp.py --dry-run      # só mostra o diagnóstico
    python converter_webp.py                # diagnostica e repara
    python converter_webp.py --otimizar     # também reduz imagens pesadas
"""

import argparse
import difflib
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

PROJETO = Path(__file__).resolve().parent
EXTS = (".webp", ".jpeg", ".jpg", ".jpe", ".jfif", ".png", ".gif", ".bmp", ".tif", ".tiff")


def norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def stem_limpo(nome: str) -> str:
    """Remove extensões (inclusive duplicadas) do nome do arquivo."""
    p = Path(nome)
    while p.suffix.lower() in EXTS:
        p = p.with_suffix("")
    return p.name


def webp_valido(caminho: Path) -> bool:
    try:
        if not caminho.is_file() or caminho.stat().st_size == 0:
            return False
        with Image.open(caminho) as im:
            im.verify()
        return True
    except Exception:  # noqa: BLE001
        return False


def converter(origem: Path, destino: Path, qualidade: int, largura_max: int) -> None:
    with Image.open(origem) as im:
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
        if im.mode == "P":
            im = im.convert("RGBA" if "transparency" in im.info else "RGB")
        elif im.mode in ("LA", "PA"):
            im = im.convert("RGBA")
        elif im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        if largura_max and im.width > largura_max:
            altura = round(im.height * largura_max / im.width)
            im = im.resize((largura_max, altura), Image.LANCZOS)
        params = {"format": "WEBP", "quality": qualidade, "method": 6}
        if icc:
            params["icc_profile"] = icc
        tmp = destino.with_name(destino.name + ".tmp")
        im.save(tmp, **params)
    tmp.replace(destino)


def precisa_otimizar(caminho: Path, largura_max: int) -> bool:
    try:
        with Image.open(caminho) as im:
            return im.width > largura_max
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", type=Path, default=PROJETO / "produtos.py")
    ap.add_argument("--static", type=Path, default=PROJETO / "static")
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--max-width", type=int, default=1200,
                    help="largura máxima em px das imagens geradas (padrão 1200)")
    ap.add_argument("--otimizar", action="store_true",
                    help="também reduz .webp válidos que estejam acima da largura máxima")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.catalogo.is_file():
        print(f"[erro] catálogo não encontrado: {args.catalogo}")
        return 1
    if not args.static.is_dir():
        print(f"[erro] pasta static não encontrada: {args.static}")
        return 1

    texto = args.catalogo.read_text(encoding="utf-8")
    esperados = re.findall(r'"imagem":\s*"([^"]+)"', texto)
    print(f"{len(esperados)} imagens de produtos encontradas em {args.catalogo.name}\n")

    ok = reparadas = otimizadas = 0
    problemas = []

    for rel in esperados:
        destino = args.static.joinpath(*rel.split("/"))
        pasta = destino.parent

        if webp_valido(destino):
            if args.otimizar and precisa_otimizar(destino, args.max_width):
                antes = destino.stat().st_size
                print(f"[otimiza] {rel}  ({antes // 1024} KB, reduzindo para {args.max_width}px)")
                if not args.dry_run:
                    try:
                        converter(destino, destino, args.quality, args.max_width)
                        print(f"          -> {destino.stat().st_size // 1024} KB")
                    except Exception as exc:  # noqa: BLE001
                        print(f"[ERRO]   {rel}: {exc}")
                        continue
                otimizadas += 1
            else:
                ok += 1
            continue

        motivo = "arquivo inválido/vazio" if destino.exists() else "arquivo não existe"

        if not pasta.is_dir():
            problemas.append((rel, "pasta não existe", []))
            print(f"[FALTA]  {rel}  (a pasta {pasta.name} não existe)")
            continue

        alvo = norm(destino.stem)
        alvos = {alvo, alvo.replace("cowboy", "cawboy"), alvo.replace("cawboy", "cowboy")}
        candidatos = [
            f for f in pasta.iterdir()
            if f.is_file() and f != destino and f.suffix.lower() in EXTS
            and norm(stem_limpo(f.name)) in alvos
        ]
        candidatos.sort(key=lambda f: EXTS.index(f.suffix.lower()))

        if not candidatos:
            nomes = [f.stem for f in pasta.iterdir() if f.is_file()]
            parecidos = difflib.get_close_matches(destino.stem, nomes, n=3, cutoff=0.5)
            problemas.append((rel, motivo, parecidos))
            print(f"[FALTA]  {rel}  ({motivo}; nenhum original encontrado)")
            if parecidos:
                print(f"         nomes parecidos na pasta: {', '.join(parecidos)}")
            continue

        origem = candidatos[0]
        print(f"[repara] {rel}  <-  {origem.name}  ({motivo})")
        if args.dry_run:
            reparadas += 1
            continue
        try:
            converter(origem, destino, args.quality, args.max_width)
            reparadas += 1
        except Exception as exc:  # noqa: BLE001
            problemas.append((rel, f"falha ao converter {origem.name}: {exc}", []))
            print(f"[ERRO]   {rel}: {exc}")

    sim = " (simulado)" if args.dry_run else ""
    print("\n" + "=" * 55)
    print(f"OK: {ok} | Reparadas: {reparadas}{sim} | Otimizadas: {otimizadas}{sim} | Com problema: {len(problemas)}")
    if problemas:
        print("\nAinda precisam de atenção (coloque o arquivo na pasta com o nome indicado):")
        for rel, motivo, _ in problemas:
            print(f"  - static/{rel}  -> {motivo}")
    return 0 if not problemas else 2


if __name__ == "__main__":
    sys.exit(main())
