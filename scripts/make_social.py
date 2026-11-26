"""Make the Bulletin's social profile images: static/social/profile.png (1080x1080, circle-safe)
and static/social/fb-cover.png (1640x624, Facebook Page cover; key content in the center safe zone).
Run after a branding change: python3 scripts/make_social.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_og import font, mark, fit, PAPER, INK, MUTED, LAKE, WARM, ROOT
from PIL import Image, ImageDraw

out = ROOT / "static/social"
out.mkdir(parents=True, exist_ok=True)

# Profile (Ben, Nov. 25: less blue, art fills the circle): static/mark-profile.svg is the same bridge, sun and waves
# scaled to the circle crop with heavier strokes for small avatars. Edit that SVG, not this script, to change it.
import subprocess, io
p = Image.open(io.BytesIO(subprocess.run(["rsvg-convert", "-w", "1080", "-h", "1080", str(ROOT / "static/mark-profile.svg")],
                                         capture_output=True, check=True).stdout)).convert("RGBA")
p.convert("RGB").save(out / "profile.png")

# Facebook cover: white paper, nameplate, double rule, tagline, promise, URL.
# Everything sits in the top 60%: Facebook overlaps the profile circle on the bottom center (phones) or bottom left (desktop).
W, H = 1640, 624
c = Image.new("RGBA", (W, H), PAPER)
d = ImageDraw.Draw(c)
d.rectangle([0, 0, W // 2, 14], fill=LAKE)
d.rectangle([W // 2, 0, W, 14], fill=WARM)
plate = fit(d, "The Bay View Bulletin", "plate", 112, 1040)
tw = d.textlength("The Bay View Bulletin", font=plate)
x = (W - tw) // 2
d.text((W / 2, 150), "The Bay View Bulletin", font=plate, fill=INK, anchor="ms")
d.line([(x, 176), (x + tw, 176)], fill=INK, width=3)
d.line([(x, 184), (x + tw, 184)], fill=INK, width=1)
d.text((W / 2, 238), "Bay View's morning paper", font=font("serif_i", 44), fill=MUTED, anchor="ms")
d.text((W / 2, 300), "NEWS · EVENTS · NEIGHBORHOOD TALK · EVERY MORNING BY 6:30", font=font("sans_b", 27), fill=LAKE, anchor="ms")
d.text((W / 2, 356), "bayviewbulletin.com", font=font("serif_b", 38), fill=WARM, anchor="ms")
c.convert("RGB").save(out / "fb-cover.png")
print("wrote", out / "profile.png", out / "fb-cover.png")
