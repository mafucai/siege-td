#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 重画单张游戏物体（城堡/塔/建筑）
=====================================
先让视觉模型「看懂」原图，再用它的描述去文生图。
这样避免我瞎猜 prompt。

流程：
  1. grok-4.7 看图 → 生成详细文字描述（材质/结构/颜色/视角）
  2. 把描述 + 风格约束 → gpt-image-2.5 出图
  3. 白底转透明 + 裁剪 + 缩放到目标尺寸

用法：
  python3 tools/ai_redraw.py art/ai_src/castle_3.png art/ai_hd/castle_3.png --scale 4
"""
import os
import sys
import io
import json
import time
import base64
import urllib.request
import argparse
from PIL import Image

BASE = 'https://api.catcat.top/v1'
KEY = 'sk-F1gwL1J5igJRWbYTYgNDbSHTO0aUkeR46K8PuRdZ0JvVY23E'

VISION_MODEL = 'glm-5-3-flash'
IMAGE_MODEL = 'gpt-image-2.5'


def _post(path, payload, timeout=240):
    req = urllib.request.Request(BASE + path,
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + KEY,
                 'Content-Type': 'application/json',
                 'User-Agent': 'curl/7.68'},
        method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, '%d %s' % (e.code, e.read()[:300].decode('utf-8', 'replace'))
    except Exception as e:
        return None, '%s %s' % (type(e).__name__, str(e)[:200])


def describe_image(png_path, retries=2):
    """让视觉模型描述这张图，返回文字描述"""
    im = Image.open(png_path).convert('RGBA')
    # 放大 + 白底，方便模型看清
    k = max(1, 480 // max(im.width, im.height))
    big = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    canvas = Image.new('RGB', big.size, (255, 255, 255))
    canvas.paste(big, (0, 0), big)
    buf = io.BytesIO()
    canvas.save(buf, 'PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()

    prompt = (
        "这是一张老式2D游戏里单个建筑/物体的贴图（已放大显示）。"
        "请用英文详细描述它的外观，用于让另一个AI照着重画："
        "1) 具体是什么建筑或物体；"
        "2) 建筑结构（几层、几个塔楼、屋顶形状、门窗位置）；"
        "3) 材质（石头/木头/茅草/金属，纹理特征）；"
        "4) 主色调和配色（具体颜色）；"
        "5) 视角（正面/等距/俯视）和光照方向；"
        "6) 有没有旗帜、装饰、破损等细节。"
        "只输出描述，不要评价。200词以内。"
        "\n最后单独一行输出 STRUCTURE: 用逗号分隔列出可见的建筑构件清单，"
        "例如 tower_count=2, floors=3, roof=conical red, windows=4, door=wood, flag=yes"
    )
    payload = {
        'model': VISION_MODEL,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + b64}},
        ]}],
        'max_tokens': 700,
    }
    for i in range(retries + 1):
        r, err = _post('/chat/completions', payload, timeout=150)
        if r:
            return r['choices'][0]['message']['content'].strip(), None
        if i < retries:
            time.sleep(3 * (i + 1))
    return None, err


def generate_image(desc, target_w, target_h, retries=2):
    """按描述生成高清图"""
    aspect = target_h / target_w if target_w else 1
    if aspect > 1.35:
        shape = 'tall vertical building, portrait orientation'
    elif aspect < 0.75:
        shape = 'wide horizontal building, landscape orientation'
    else:
        shape = 'roughly square building'

    # 从描述里抽 STRUCTURE 行
    struct = ''
    for line in desc.split('\n'):
        if line.strip().upper().startswith('STRUCTURE:'):
            struct = line.split(':', 1)[1].strip()
            desc = desc.replace(line, '').strip()
            break

    prompt = (
        f"Medieval 2D game building asset. {desc} "
        f"REQUIRED STRUCTURE (must match exactly, do not invent extra elements): {struct}. "
        f"CRITICAL: the building must have a {aspect:.2f} height-to-width ratio "
        f"({shape}), same silhouette and same architectural structure as described. "
        "Do NOT add or remove towers, arches, or floors. Do NOT change the perspective. "
        "Only increase resolution and add surface detail (stone joints, wood grain, window frames). "
        "Style: hand-painted 2D game asset for a medieval strategy game, "
        "clean crisp outlines, rich saturated colors, soft top-left lighting, "
        "isolated on pure white background, no ground shadow, no scenery, "
        "single centered building filling the frame vertically."
    )

    # 选择 API 支持的尺寸
    if aspect > 1.3:
        size = '1024x1536'
    elif aspect < 0.77:
        size = '1536x1024'
    else:
        size = '1024x1024'

    payload = {
        'model': IMAGE_MODEL,
        'prompt': prompt,
        'n': 1,
        'size': size,
        'response_format': 'b64_json',
    }
    for i in range(retries + 1):
        r, err = _post('/images/generations', payload, timeout=280)
        if r and r.get('data'):
            d = r['data'][0]
            if 'b64_json' in d:
                return base64.b64decode(d['b64_json']), None
            if 'url' in d:
                return urllib.request.urlopen(d['url'], timeout=120).read(), None
        if i < retries:
            time.sleep(4 * (i + 1))
    return None, err or '空返回'


def white_to_alpha(im, thr=236):
    im = im.convert('RGBA')
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > thr and g > thr and b > thr:
                px[x, y] = (r, g, b, 0)
    return im


def autocrop(im, pad=2):
    bbox = im.getchannel('A').getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(im.width, x1 + pad); y1 = min(im.height, y1 + pad)
    return im.crop((x0, y0, x1, y1))


def fit_to(im, tw, th, mode='cover'):
    """把图放进 tw x th 的画布
    cover: 填满画布（可能裁边）
    contain: 完整放进（留透明边）
    """
    if mode == 'cover':
        r = max(tw / im.width, th / im.height)
    else:
        r = min(tw / im.width, th / im.height)
    nw, nh = max(1, int(im.width * r)), max(1, int(im.height * r))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    canvas.paste(im2, ((tw - nw) // 2, (th - nh) // 2), im2)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--scale', type=int, default=4)
    ap.add_argument('--desc', default=None, help='跳过视觉分析，直接用给定描述')
    args = ap.parse_args()

    fn = os.path.basename(args.src)
    src = Image.open(args.src)
    w, h = src.size
    tw, th = w * args.scale, h * args.scale

    print('=== %s  %dx%d -> %dx%d ===' % (fn, w, h, tw, th))

    if args.desc:
        desc = args.desc
        print('  使用给定描述')
    else:
        print('  1/3 视觉分析...')
        desc, err = describe_image(args.src)
        if not desc:
            print('  视觉分析失败:', err)
            sys.exit(2)
        print('  描述: %s' % desc[:120].replace('\n', ' ') + '...')

    print('  2/3 生成图像...')
    raw, err = generate_image(desc, tw, th)
    if not raw:
        print('  生成失败:', err)
        sys.exit(3)

    im = Image.open(io.BytesIO(raw))
    print('  模型输出 %dx%d' % im.size)

    print('  3/3 后处理...')
    im = white_to_alpha(im)
    im = autocrop(im)
    im = fit_to(im, tw, th, 'contain')

    os.makedirs(os.path.dirname(args.dst) or '.', exist_ok=True)
    im.save(args.dst)

    # 存描述，方便复查
    with open(args.dst + '.desc.txt', 'w', encoding='utf-8') as f:
        f.write(desc)

    print('  保存 %s  %dx%d' % (args.dst, im.width, im.height))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
