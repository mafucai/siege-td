#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 重画游戏精灵图（走 /v1/images/generations，不用 edit 端点）。

原理：
  edit 端点在这个网关超时（504），但 generations 正常。
  所以把原图信息转成详细文字描述，让模型文生图。
  描述由像素分析自动生成（主色、轮廓比例、材质），保证「同一个东西」。
"""
import os
import sys
import io
import json
import base64
import urllib.request
import collections
from PIL import Image

API = 'https://api.catcat.top/v1/images/generations'
KEY = 'sk-F1gwL1J5igJRWbYTYgNDbSHTO0aUkeR46K8PuRdZ0JvVY23E'


# ---- 由文件名推断物体类型 ----
NAME_HINTS = {
    'spearman': 'a medieval spearman soldier holding a long wooden spear, standing front view',
    'pikeman': 'a medieval pikeman soldier with an extra-long pike, standing front view',
    'swordman': 'a medieval swordsman soldier holding a steel sword and round shield, standing front view',
    'swordsman': 'a medieval swordsman soldier holding a steel sword and round shield, standing front view',
    'soldier': 'a medieval foot soldier with leather armor and short sword, standing front view',
    'peasant': 'a medieval peasant fighter with a wooden club and ragged tunic, standing front view',
    'axeman': 'a medieval axeman with a large battle axe, standing front view',
    'maceman': 'a medieval maceman with a spiked mace and chainmail, standing front view',
    'archer': 'a medieval archer drawing a wooden bow, standing front view',
    'crossbow': 'a medieval crossbowman aiming a heavy crossbow, standing front view',
    'knight': 'a medieval knight in full plate armor with a sword, standing front view',
    'paladin': 'a medieval paladin knight in ornate blessed plate armor, standing front view',
    'cavalry': 'a medieval cavalryman on horseback with lance',
    'horseman': 'a medieval horseman on horseback with sword',
    'arthur': 'King Arthur in royal medieval armor with cape, standing front view',
    'hammer': 'a medieval hammer soldier with a war hammer, standing front view',
    'royalguard': 'a royal guard in crimson and gold medieval armor with halberd, standing front view',
    'churchman': 'a medieval priest in white and gold robes holding a staff, standing front view',
    'bugler': 'a medieval bugler soldier blowing a brass horn, standing front view',
    'batteringram': 'a medieval wooden battering ram siege engine with iron head',
    'catapult': 'a medieval wooden catapult siege engine',
    'tower': 'a medieval stone watchtower with wooden roof and battlements',
    'castle': 'a medieval stone castle keep with towers and battlements',
    'church': 'a medieval stone church with a tall spire and stained glass windows',
    'workshop': 'a medieval wooden workshop building with tools and anvil',
    'stable': 'a medieval wooden stable building with horse stalls',
    'magic': 'a medieval stone magic tower with glowing blue runes',
    'house': 'a medieval wooden peasant house with thatched roof',
    'tent': 'a medieval military tent with banners',
    'wall': 'a medieval stone wall segment with battlements',
    'gate': 'a medieval wooden castle gate with iron bands',
    'flag': 'a medieval heraldic battle flag on a pole',
    'crusader': 'a medieval crusader knight in white surcoat with red cross',
    'doodad': 'a medieval scenery prop, wooden barrel and crate',
    'trebuchet': 'a medieval wooden trebuchet siege engine with counterweight',
    'ballista': 'a medieval ballista bolt thrower siege engine',
    'generaltower': 'a medieval wooden watchtower with a flag on top',
    'catapulttower': 'a medieval stone tower housing a catapult',
    'trebuchettower': 'a medieval stone tower housing a trebuchet',
    'bighchurch': 'a large medieval cathedral with twin spires',
}


def guess_subject(fn):
    low = fn.lower()
    # 去掉 _1 _2 _a _e _b1 _b2 等后缀
    base = low.replace('.png', '')
    for key in sorted(NAME_HINTS.keys(), key=len, reverse=True):
        if key in base:
            return NAME_HINTS[key]
    return 'a medieval fantasy game object'


def analyze(path):
    """分析原图：尺寸、主色、材质倾向"""
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    px = list(im.getdata())
    op = [p for p in px if p[3] > 32]
    if not op:
        return None
    cnt = collections.Counter(p[:3] for p in op)
    top = cnt.most_common(6)
    # 主色描述
    def cname(r, g, b):
        mx, mn = max(r, g, b), min(r, g, b)
        if mx < 60: return 'dark grey/black'
        if mx - mn < 25:
            return 'grey stone' if mx > 100 else 'dark metal'
        if r > g and r > b:
            if g > b * 1.3: return 'brown wood'
            if b > g * 1.3: return 'crimson red'
            return 'warm ochre'
        if g > r and g > b: return 'olive green'
        if b > r and b > g: return 'steel blue'
        return 'mixed'
    colors = []
    seen = set()
    for c, n in top:
        name = cname(*c)
        if name not in seen:
            seen.add(name)
            colors.append(name)
    ratio = h / w if w else 1
    return {
        'size': (w, h),
        'aspect': ratio,
        'colors': colors[:4],
        'opaque_pct': 100 * len(op) / len(px),
    }


def build_prompt(fn, info, scale):
    subject = guess_subject(fn)
    tw, th = info['size'][0] * scale, info['size'][1] * scale
    aspect = info['aspect']
    if aspect > 1.6:
        shape = 'tall vertical composition'
    elif aspect < 0.7:
        shape = 'wide horizontal composition'
    else:
        shape = 'roughly square composition'

    colors = ', '.join(info['colors']) if info['colors'] else 'earth tones'
    return (
        f"{subject}, isolated on pure white background, "
        f"{shape}, dominant colors: {colors}, "
        "hand-painted 2D game asset in the style of classic medieval strategy games, "
        "clean crisp outlines, detailed textures on armor and wood, "
        "soft top-left lighting, no drop shadow on ground, no background scenery, "
        "single centered object filling most of the frame, "
        "high resolution detailed illustration, game sprite art"
    )


def call_api(prompt, size, model='gpt-image-2.5', timeout=240):
    payload = {
        'model': model,
        'prompt': prompt,
        'n': 1,
        'size': size,
        'response_format': 'b64_json',
    }
    req = urllib.request.Request(API,
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + KEY,
                 'Content-Type': 'application/json',
                 'User-Agent': 'curl/7.68'},
        method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, '%d %s' % (e.code, e.read()[:200].decode('utf-8', 'replace'))
    except Exception as e:
        return None, '%s %s' % (type(e).__name__, str(e)[:150])


def white_to_alpha(im, thr=238):
    im = im.convert('RGBA')
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > thr and g > thr and b > thr:
                px[x, y] = (r, g, b, 0)
    return im


def trim(im):
    bbox = im.getchannel('A').getbbox()
    return im.crop(bbox) if bbox else im


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    scale = 4
    model = 'gpt-image-2.5'
    args = sys.argv[3:]
    for i, a in enumerate(args):
        if a == '--scale': scale = int(args[i + 1])
        if a == '--model': model = args[i + 1]

    fn = os.path.basename(src)
    info = analyze(src)
    if not info:
        print('原图为空:', src)
        sys.exit(2)

    w, h = info['size']
    tw, th = w * scale, h * scale

    # API 支持的 size
    if max(tw, th) <= 1024:
        api_size = '%dx%d' % (tw, th)
        if api_size not in ('256x256', '512x512', '1024x1024',
                            '1024x1536', '1536x1024', '1024x1792', '1792x1024'):
            api_size = '1024x1024'
    else:
        api_size = '1024x1536' if th > tw else '1536x1024'

    prompt = build_prompt(fn, info, scale)
    print('=== %s ===' % fn)
    print('  原图 %dx%d  目标 %dx%d  API尺寸 %s' % (w, h, tw, th, api_size))
    print('  主色: %s' % ', '.join(info['colors']))
    print('  prompt: %s' % prompt[:150] + '...')

    r, err = call_api(prompt, api_size, model)
    if err:
        print('  API 失败:', err)
        sys.exit(3)

    d = r.get('data', [])
    if not d:
        print('  返回空')
        sys.exit(4)

    item = d[0]
    if 'b64_json' in item:
        raw = base64.b64decode(item['b64_json'])
    elif 'url' in item:
        raw = urllib.request.urlopen(item['url'], timeout=120).read()
    else:
        print('  未知格式', list(item.keys()))
        sys.exit(5)

    im = Image.open(io.BytesIO(raw))
    print('  模型输出 %dx%d %s' % (im.size[0], im.size[1], im.mode))

    im = white_to_alpha(im)
    im = trim(im)
    # 缩放到目标尺寸，保持宽高比
    im.thumbnail((tw * 2, th * 2), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    im.save(dst)
    print('  保存 %s  %dx%d' % (dst, im.size[0], im.size[1]))


if __name__ == '__main__':
    main()
