"""Contact sheet of PNGs on a checker background: tools/sheet.py out.png a.png b.png ..."""
import sys
from PIL import Image, ImageDraw

out, files = sys.argv[1], sys.argv[2:]
ims = [Image.open(f).convert("RGBA") for f in files]
cw = max(i.width for i in ims); ch = max(i.height for i in ims) + 14
cols = min(6, len(ims)); rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * cw, rows * ch), (90, 160, 70, 255))
d = ImageDraw.Draw(sheet)
for k, (f, im) in enumerate(zip(files, ims)):
    x, y = (k % cols) * cw, (k // cols) * ch
    d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=(60, 110, 50))
    sheet.alpha_composite(im, (x, y))
    d.text((x + 2, y + ch - 13), f.split("/")[-1][:30], fill=(255, 255, 255))
sheet.save(out)
