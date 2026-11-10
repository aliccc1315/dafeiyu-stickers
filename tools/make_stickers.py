"""表情包 v4：毒舌配文版。渲染逻辑同 v3（白字黑描边，无底条）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(r"C:\Users\Administrator\.dsh\dsh_wechat\dafeiyu-pet\assets\pet")
OUT = Path(r"C:\Users\Administrator\.dsh\dsh_wechat\stickers_v4")
FONT_PATH = r"C:\Windows\Fonts\msyhbd.ttc"

SCALE = 0.66
GIF_FPS = 12

# 毒舌版：(动图配文, 静态配文)
CAPTIONS: dict[str, tuple[str, str]] = {
    "idle": ("本鱼在，安静点", "看什么看，没见过鱼"),
    "idle_yawn": ("困了，闭嘴", "你吵到我做梦了"),
    "idle_stretch": ("别催，在摸了", "急什么，反正也做不完"),
    "eat_token": ("白饭！token！", "你的钱真香"),
    "head_pat": ("摸头收费，一次五毛", "摸够了没有，鳞都乱了"),
    "poke": ("戳我干嘛，手贱？", "再戳咬你"),
    "tail": ("尾巴不是进度条", "摸尾巴要加钱"),
    "error": ("呜……这锅我不背", "又翻车？怪你"),
    "success": ("搞定，夸我", "轻轻松松，你行你上"),
    "thinking": ("让本鱼想想", "这需求狗都不做"),
    "working": ("忙，勿扰", "你写你的，我睡我的"),
    "working_search": ("翻箱倒柜中", "自己找，我累了"),
    "working_command": ("命令发了，听天由命", "跑吧，炸了别找我"),
    "waiting": ("就等你一句话", "倒是快点啊"),
    "dragging": ("放我下来", "拎着我干嘛，重不重"),
    "dragging_release": ("差点被你摔死", "稳住了，算你厉害"),
}


def load_frames(clip: str) -> list[Image.Image]:
    folder = ASSETS / clip
    if not folder.is_dir():
        return []
    frames = []
    for path in sorted(folder.glob("*.webp")):
        try:
            frames.append(Image.open(path).convert("RGBA"))
        except OSError:
            continue
    return frames


def pick_distinct(frames: list[Image.Image], count: int = 2) -> list[Image.Image]:
    if len(frames) <= count:
        return frames
    small = [np.asarray(f.resize((48, 40)).convert("L"), dtype=np.float32) for f in frames]
    stack = np.stack(small)
    mean = stack.mean(axis=0)
    distance = np.abs(stack - mean).sum(axis=(1, 2))
    order = list(np.argsort(distance)[::-1])
    chosen: list[int] = []
    min_gap = max(4, len(frames) // 8)
    for index in order:
        if all(abs(index - other) >= min_gap for other in chosen):
            chosen.append(int(index))
        if len(chosen) >= count:
            break
    while len(chosen) < count:
        chosen.append(len(frames) // 2)
    return [frames[i] for i in sorted(chosen)]


def compose(frame: Image.Image, text: str) -> Image.Image:
    width = max(1, int(frame.width * SCALE))
    height = max(1, int(frame.height * SCALE))
    pet = frame.resize((width, height), Image.LANCZOS)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(pet, (0, 0), pet)

    size = max(20, int(height * 0.135))
    if len(text) > 8:
        size = int(size * 0.78)
    elif len(text) > 6:
        size = int(size * 0.88)
    font = ImageFont.truetype(FONT_PATH, size)

    draw = ImageDraw.Draw(canvas)
    stroke = max(4, size // 7)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) / 2 - bbox[0]
    y = height - int(height * 0.085) - bbox[3]
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255),
              stroke_width=stroke, stroke_fill=(16, 20, 32, 255))
    return canvas


def make_all() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    for clip, (primary, secondary) in CAPTIONS.items():
        frames = load_frames(clip)
        if not frames:
            print(f"  跳过 {clip}")
            continue
        chosen = pick_distinct(frames, 2)
        for index, text in enumerate((primary, secondary)):
            still = compose(chosen[min(index, len(chosen) - 1)], text)
            path = OUT / f"{clip}_{index + 1}.png"
            still.save(path)
            made.append(path)
        sampled = frames[::2][:30]
        gif_frames = [compose(f, primary) for f in sampled]
        gif_path = OUT / f"{clip}.gif"
        gif_frames[0].save(
            gif_path, save_all=True, append_images=gif_frames[1:],
            duration=int(1000 / GIF_FPS), loop=0, disposal=2,
        )
        made.append(gif_path)
        print(f"  {clip:16s} {primary} / {secondary}")
    return made


def contact_sheet(files: list[Path]) -> Path:
    tiles = [Image.open(p).convert("RGBA") for p in files if p.suffix == ".png"]
    columns = 5
    rows = (len(tiles) + columns - 1) // columns
    cell_w = max(t.width for t in tiles)
    cell_h = max(t.height for t in tiles)
    sheet = Image.new("RGBA", (cell_w * columns, cell_h * rows), (232, 238, 246, 255))
    for index, tile in enumerate(tiles):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        sheet.paste(tile, (x, y), tile)
    out = OUT / "_contact_sheet_v4.png"
    sheet.convert("RGB").save(out, quality=92)
    return out


if __name__ == "__main__":
    files = make_all()
    sheet = contact_sheet(files)
    statics = sum(1 for f in files if f.suffix == ".png")
    gifs = sum(1 for f in files if f.suffix == ".gif")
    total = sum(f.stat().st_size for f in files) / 1024
    print(f"\n完成：{statics} 张静态 + {gifs} 个动图，合计 {total:.0f} KB")
    print(f"预览：{sheet}")
