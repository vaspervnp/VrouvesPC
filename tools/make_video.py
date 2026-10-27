"""Make the YouTube video, build/video/LetsGoForVrouves-en.mp4 (1920 x 1080, 60 fps, 5 min).

It cuts the Movie Maker recordings of tools/record.sh (scratch/video/*.avi, recorded without
music) into scenes, puts each one over a blurred copy of itself to fill 16:9, opens with a
title card and closes with an end card, and lays the game's tune under the whole thing.

    tools/record.sh ... (see README), then .venv/bin/python tools/make_video.py [en|gr]   (English unless told)
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "scratch", "video")
WORK = os.path.join(REC, "work")
OUT = os.path.join(ROOT, "build", "video")
W, H, GW = 1920, 1080, 1350            # the video, and the game picture in the middle
SIDE = (W - GW) // 2
FADE = 0.6                              # crossfade between scenes, seconds
FONT_BIG = os.path.join(ROOT, "art", "fonts", "NotoSansDisplay-Black.ttf")
FONT_BOLD = os.path.join(ROOT, "art", "fonts", "NotoSans-Bold.ttf")
GOLD, RED, WHITE = (255, 217, 51), (255, 106, 85), (255, 255, 255)

# recording, start, length, and the title or end card laid over it: the title screen, a
# stretch of every stage (the bot playing, from just after it calls the first wave), the ending
SCENES = ([("title", 0.0, 9.5, "title")]
          + [(f"s{n}", 8.0, 39.5, None) for n in range(1, 8)]
          + [("end", 0.0, 11.0, None), ("end", 11.0, 6.0, "end")])
TITLE = ["Let's Go For Vrouves", "Πάμε για Βρούβες"]
TAGLINE = ["A cute tower defence from Crete", "Ένα χαριτωμένο tower defence από την Κρήτη"]
PLATFORMS = "Windows · Linux · macOS"


def font(path, size):
    return ImageFont.truetype(path, size)


def outlined(d, xy, text, f, fill, anchor="la", stroke=5):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(20, 24, 40))


def card(lang, path, end):
    """the title card (over the title screen) or the end card (over the ending)"""
    im = Image.new("RGBA", (W, H), (12, 16, 30, 200))
    d = ImageDraw.Draw(im)
    icon = Image.open(os.path.join(ROOT, "art", "icon_1024.png")).convert("RGBA").resize((330, 330), Image.LANCZOS)
    im.alpha_composite(icon, ((W - 330) // 2, 120))
    outlined(d, (W // 2, 480), TITLE[0], font(FONT_BIG, 104), GOLD, "ma", 8)
    outlined(d, (W // 2, 620), TITLE[1], font(FONT_BIG, 72), RED, "ma", 7)
    sub = PLATFORMS if end else TAGLINE[lang]
    outlined(d, (W // 2, 745), sub, font(FONT_BOLD, 44), WHITE, "ma", 5)
    if end:
        outlined(d, (W // 2, 830), "REVIVE8BIT · 2026", font(FONT_BOLD, 32), WHITE, "ma", 4)
    im.save(path)


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, check=True)


def scene(i, sc, lang, tag):
    """one scene as a 1920 x 1080 clip with its sound effects"""
    rec, start, length, kind = sc
    src = os.path.join(REC, f"{rec}_{tag}.avi")
    over = os.path.join(WORK, f"card{i}_{tag}.png")
    if kind:
        card(lang, over, kind == "end")
    out = os.path.join(WORK, f"scene{i}_{tag}.mp4")
    # a still at the end of the recording is held, so the end card can be longer than it
    v = (f"[0:v]tpad=stop_mode=clone:stop_duration={length},trim=0:{length},setpts=PTS-STARTPTS,split[a][b];"
         f"[a]scale={W}:-2,crop={W}:{H},gblur=sigma=28,eq=brightness=-0.12:saturation=0.8[bg];"
         f"[bg][b]overlay=x={SIDE}:y=0[g];")
    if kind == "title":
        # the title card fades away into the title screen
        v += f"[1:v]format=rgba,fade=t=out:st=2.6:d=1:alpha=1[o];[g][o]overlay,fade=t=in:d=0.6[v]"
    elif kind == "end":
        v += f"[1:v]format=rgba,fade=t=in:st=0:d=1:alpha=1[o];[g][o]overlay,fade=t=out:st={length - 1.2}:d=1.2[v]"
    else:
        v += "[g]null[v]"
    run(["-ss", str(start), "-t", str(length + 1), "-i", src] + (["-loop", "1", "-i", over] if kind else []) + [
         "-filter_complex", v + f";[0:a]aresample=48000,volume={0 if kind == 'title' else 1},apad,atrim=0:{length},asetpts=PTS-STARTPTS[s]",
         "-map", "[v]", "-map", "[s]", "-t", str(length), "-r", "60",
         "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p",
         "-c:a", "pcm_s16le", "-ac", "2", out])
    return out, length


def main():
    langs = sys.argv[1:] or ["en"]
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for tag in langs:
        lang = 0 if tag == "en" else 1
        clips = [scene(i, sc, lang, tag) for i, sc in enumerate(SCENES)]
        # crossfade the scenes into one another, picture and sound effects alike
        ins, f, t = [], "", 0.0
        for path, _ in clips:
            ins += ["-i", path]
        v, a = "[0:v]", "[0:a]"
        for k in range(1, len(clips)):
            t += clips[k - 1][1] - FADE
            f += (f"{v}[{k}:v]xfade=transition=fade:duration={FADE}:offset={t:.3f}[v{k}];"
                  f"{a}[{k}:a]acrossfade=d={FADE}[a{k}];")
            v, a = f"[v{k}]", f"[a{k}]"
        total = t + clips[-1][1]
        music = os.path.join(ROOT, "art", "audio", "music.wav")
        n = len(clips)
        f += (f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total},"
              f"volume=0.55,afade=t=in:d=0.5,afade=t=out:st={total - 2.5}:d=2.5[m];"
              f"{a}volume=1.0[fx];[m][fx]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        out = os.path.join(OUT, f"LetsGoForVrouves-{tag}.mp4")
        run(ins + ["-stream_loop", "-1", "-i", music, "-filter_complex", f,
                   "-map", v, "-map", "[aout]", "-t", f"{total:.3f}",
                   "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
                   "-profile:v", "high", "-movflags", "+faststart",
                   "-c:a", "aac", "-b:a", "192k", out])
        print(out, f"{total:.1f} s", os.path.getsize(out) // (1 << 20), "MB")


if __name__ == "__main__":
    main()
