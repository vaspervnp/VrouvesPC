"""Make build/manual/Manual-EN.pdf and Manual-GR.pdf from manual/*.md.

The Markdown becomes an HTML page with the game's fonts, and Microsoft Edge (on the Windows
side of WSL) prints it to PDF in headless mode. Run from the repository with the .venv
python (it needs the markdown package).
"""
import os
import re
import shutil
import subprocess
import unicodedata

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
WIN_TMP = "/mnt/c/Users/vasilhs/AppData/Local/Temp/vrouves_manual"     # Edge reads from here
WIN_TMP_W = r"C:\Users\vasilhs\AppData\Local\Temp\vrouves_manual"
OUT = os.path.join(ROOT, "build", "manual")
MANUALS = [("Manual-EN", "en"), ("Manual-GR", "el")]

CSS = """
@font-face { font-family: Noto; src: url(fonts/NotoSans-Regular.ttf); }
@font-face { font-family: Noto; font-weight: bold; src: url(fonts/NotoSans-Bold.ttf); }
@font-face { font-family: NotoDisplay; src: url(fonts/NotoSansDisplay-Black.ttf); }
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font-family: Noto, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d2a16; }
h1 { font-family: NotoDisplay, sans-serif; font-size: 34pt; color: #d23b23; margin: 4mm 0 0; }
h2 { font-family: NotoDisplay, sans-serif; font-size: 19pt; color: #2f6f1e; margin: 0 0 3mm;
     padding-bottom: 1.5mm; border-bottom: 2.5px solid #f0c419; break-before: page; }
h2.first { break-before: auto; }
h3 { font-size: 12.5pt; color: #2f6f1e; margin: 5mm 0 2mm; break-after: avoid; }
p, li { margin: 1.5mm 0; }
a { color: #2f6f1e; text-decoration: none; }
hr { display: none; }
img { max-width: 100%; }
p > img:only-child { display: block; margin: 3mm auto; border-radius: 3mm; max-height: 105mm;
                     box-shadow: 0 1mm 3mm rgba(0,0,0,.25); }
table { border-collapse: collapse; width: 100%; margin: 3mm 0; break-inside: avoid; font-size: 9.5pt; }
th { background: #2f6f1e; color: white; text-align: left; padding: 1.5mm 2mm; }
td { padding: 1.2mm 2mm; border-bottom: 1px solid #d5e3c6; vertical-align: middle; }
tr:nth-child(even) td { background: #f2f8ea; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #eef3e6; padding: 0 1mm;
       border-radius: 1mm; }
h1 + p + p > img:only-child { max-height: none; width: 100%; margin-top: 8mm; }
"""


def slug(text: str, sep: str) -> str:
    """the anchors GitHub makes, so the same links work in the PDF (Greek letters kept)"""
    text = unicodedata.normalize("NFC", re.sub(r"<[^>]+>", "", text)).strip().lower()
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return text.replace(" ", sep)


def page(name: str, lang: str) -> str:
    src = open(os.path.join(ROOT, "manual", name + ".md"), encoding="utf-8").read()
    # the links between the two manuals point at the PDFs, installed side by side
    src = src.replace("Manual-EN.md", "Manual-EN.pdf").replace("Manual-GR.md", "Manual-GR.pdf")
    body = markdown.markdown(src, extensions=["tables", "toc", "attr_list"],
                             extension_configs={"toc": {"slugify": slug}})
    # the contents get a page of their own after the cover, and the story follows them
    heads = body.split("<h2")
    body = heads[0] + "<h2" + heads[1] + '<h2 class="first"' + "<h2".join(heads[2:])
    # a table with an empty heading row has none
    body = re.sub(r"<thead>\s*<tr>(\s*<th[^>]*>\s*</th>)+\s*</tr>\s*</thead>", "", body)
    title = re.search(r"<h1[^>]*>(.*?)</h1>", body).group(1)
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f"<title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>")


def main() -> None:
    shutil.rmtree(WIN_TMP, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "manual", "img"), os.path.join(WIN_TMP, "img"))
    shutil.copytree(os.path.join(ROOT, "art", "fonts"), os.path.join(WIN_TMP, "fonts"))
    os.makedirs(OUT, exist_ok=True)
    for name, lang in MANUALS:
        with open(os.path.join(WIN_TMP, name + ".html"), "w", encoding="utf-8") as f:
            f.write(page(name, lang))
        pdf_w = WIN_TMP_W + "\\" + name + ".pdf"
        subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        "--user-data-dir=" + WIN_TMP_W + "\\edge", "--print-to-pdf=" + pdf_w,
                        "file:///" + (WIN_TMP_W + "\\" + name + ".html").replace("\\", "/")],
                       check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy(os.path.join(WIN_TMP, name + ".pdf"), os.path.join(OUT, name + ".pdf"))
        print(os.path.join(OUT, name + ".pdf"), os.path.getsize(os.path.join(OUT, name + ".pdf")) // 1024, "KB")
    shutil.rmtree(WIN_TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
