from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out = Path("core/static/core/icons")
out.mkdir(parents=True, exist_ok=True)
for size in (192, 512):
    img = Image.new("RGB", (size, size), "#39764d")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=int(size * 0.6))
    draw.text((size / 2, size / 2), "S", fill="white", font=font, anchor="mm")
    img.save(out / f"icon-{size}.png")
