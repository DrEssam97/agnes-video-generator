"""Re-check agnes-video-generator master's Arabic subtitles, as the maintainer asked.

Usage: python recheck.py REPO OUT_DIR
Cases: mixed Arabic + Latin + digits + brackets, a very long Arabic line, and a real
video whose subtitles use bg_color + stroke_width (default style and a heavier one).
Writes clips.png (each clip's first frame), video.mp4, and frames.png (frames read
back from the encoded video).
"""

import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
repo, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))

import numpy as np  # noqa: E402
from moviepy import CompositeVideoClip, ImageClip, VideoFileClip  # noqa: E402
from PIL import Image, features  # noqa: E402

import khatt  # noqa: E402
from core.compositor.concatenator import VideoConcatenator  # noqa: E402
from models.task import SubtitleStyle  # noqa: E402

print("Pillow", Image.__version__, "raqm:", features.check("raqm"), "khatt", khatt.__version__)

LINES = [
    "حلقة 3 من Python (الجزء الأول) بسعر $25 فقط",
    "«مرحبا» يا Ahmed، الساعة 10:30 مساءً [مباشر]",
    "في هذا الفيديو نشرح بالتفصيل كيف تبني تطبيقا كاملا من الصفر خطوة بخطوة، بدءا من "
    "تصميم الواجهة وحتى رفعه على الخادم، مع أمثلة عملية ونصائح من تجربة سنوات طويلة في "
    "تطوير البرمجيات، فتابع حتى النهاية ولا تنس الاشتراك في القناة",
    "Hello world, plain Latin line",
]
WIDTH, HEIGHT = 1280, 720
STYLES = {
    "default style (bg 0,0,0,128, stroke 2)": SubtitleStyle(),
    "bg 20,20,60,200, stroke 5": SubtitleStyle(bg_color=(20, 20, 60, 200), stroke_width=5),
}


def parse(style):
    srt = "\n".join(
        f"{n}\n00:00:{2 * n - 2:02d},000 --> 00:00:{2 * n - 1:02d},800\n{line}\n"
        for n, line in enumerate(LINES, start=1)
    )
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "subs.srt"
        path.write_text(srt, encoding="utf-8")
        return VideoConcatenator._parse_srt_to_clips(
            str(path), style, video_width=WIDTH, video_height=HEIGHT, video_duration=2 * len(LINES)
        )


def clip_image(clip):
    frame = Image.fromarray(np.uint8(clip.get_frame(0)[..., :3]))
    mask = getattr(clip, "mask", None)
    alpha = None if mask is None else Image.fromarray(np.uint8(mask.get_frame(0) * 255))
    band = Image.new("RGB", (WIDTH, frame.height + 20), (90, 130, 90))
    band.paste(frame, ((WIDTH - frame.width) // 2, 10), alpha)
    return band


def stack(images, path):
    sheet = Image.new("RGB", (max(i.width for i in images), sum(i.height + 6 for i in images)), "white")
    y = 0
    for image in images:
        sheet.paste(image, (0, y))
        y += image.height + 6
    sheet.save(path)


# 1. Each clip's first frame, default style
clips = parse(SubtitleStyle())
print("clips:", [type(c).__module__ + "." + type(c).__name__ for c in clips])
print("sizes:", [c.size for c in clips])
stack([clip_image(c) for c in clips], out / "clips.png")

# 2. A real video for each style, then frames read back from the encoded file
yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
background = np.stack(
    [(xx * 255 // WIDTH), (yy * 255 // HEIGHT), np.full_like(xx, 160)], axis=-1
).astype(np.uint8)
background[::40, :] = 255  # stripes, so the translucent box shows
frames = []
for name, style in STYLES.items():
    subs = parse(style)
    video = CompositeVideoClip(
        [ImageClip(background).with_duration(2 * len(LINES)), *subs], size=(WIDTH, HEIGHT)
    )
    file = out / f"video-{len(frames)}.mp4"
    video.write_videofile(str(file), fps=4, codec="libx264", audio=False, logger=None)
    read = VideoFileClip(str(file))
    for n in range(len(LINES)):
        frame = Image.fromarray(read.get_frame(2 * n + 0.5))
        frames.append(frame.resize((WIDTH // 2, HEIGHT // 2)))
    read.close()
    print("video:", name, file.name)
pairs = [Image.new("RGB", (WIDTH, HEIGHT // 2), "white") for _ in range(len(frames) // 2)]
for i, pair in enumerate(pairs):
    pair.paste(frames[2 * i], (0, 0))
    pair.paste(frames[2 * i + 1], (WIDTH // 2, 0))
stack(pairs, out / "frames.png")
print("done")
