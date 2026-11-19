"""Render agnes-video-generator's real subtitle clips for Arabic lines.

Usage: python harness.py REPO OUT_PNG
Runs VideoConcatenator._parse_srt_to_clips on an SRT with Arabic lines and stacks the
first frame of every subtitle clip on a dark band.
"""

import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
repo, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))

import numpy as np  # noqa: E402
from PIL import Image, features  # noqa: E402

from core.compositor.concatenator import VideoConcatenator  # noqa: E402
from models.task import SubtitleStyle  # noqa: E402

print("Pillow raqm:", features.check("raqm"))

LINES = [
    "مرحبا بالعالم",
    "هذه جملة طويلة في الترجمة تلتف على سطرين لنرى ترتيب الأسطر بوضوح تام",
    "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
    "سعر القهوة 25 ريالا (عرض خاص)",
]
srt = "\n".join(
    f"{n}\n00:00:{n:02d},000 --> 00:00:{n:02d},900\n{line}\n" for n, line in enumerate(LINES, start=1)
)
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "subs.srt"
    path.write_text(srt, encoding="utf-8")
    clips = VideoConcatenator._parse_srt_to_clips(
        str(path), SubtitleStyle(), video_width=1280, video_height=720, video_duration=10
    )

bands = []
for clip in clips:
    frame = clip.get_frame(0)
    rgb = Image.fromarray(np.uint8(frame[..., :3]))
    mask = getattr(clip, "mask", None)
    band = Image.new("RGB", (1280, rgb.height + 20), (40, 70, 110))
    alpha = None if mask is None else Image.fromarray(np.uint8(mask.get_frame(0) * 255))
    band.paste(rgb, ((1280 - rgb.width) // 2, 10), alpha)
    bands.append(band)
sheet = Image.new("RGB", (1280, sum(b.height for b in bands)), "white")
y = 0
for band in bands:
    sheet.paste(band, (0, y))
    y += band.height
sheet.save(out)
print("clips:", [type(c).__module__ for c in clips])
