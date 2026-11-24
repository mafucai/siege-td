#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 CI 里批量处理全部游戏图片（代码渲染，不依赖 AI）。
========================================================
输入：art/source_png/*.png（130 张原图）
      art/source_xml/*.xml（81 个部件图集坐标）
输出：art/hd/*.png（放大后的图）+ art/hd/*.xml（坐标同步 ×factor）

处理策略（自动判断类型）：
  1. 大图（≥512px，背景/UI）：hybrid 放大 2 倍
  2. 部件图集（有对应 xml）：xbr 放大 4 倍，xml 坐标同步 ×4
  3. 小图无 xml（杂项）：xbr 放大 4 倍
  4. 字体图集（font*_hd.png）：不处理（字体缩放会糊，保持原样）

用法：
  python3 tools/batch_upscale.py --in art/source_png --xml art/source_xml --out art/hd
"""
import os
import sys
import glob
import re
import json
import time
import argparse
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upscale_algos import upscale


MAX_TEX = 4096   # GL 纹理安全上限


def classify(fn, w, h, has_xml):
    """判断处理策略，返回 (factor, algo, reason)"""
    base = os.path.basename(fn)

    # 字体图集：不动（缩放会糊）
    if re.match(r'font\d+_cn_hd\.png', base):
        return 1, 'none', '字体图集（缩放会糊）'

    if has_xml:
        f, algo, reason = 4, 'xbr', '部件图集（骨骼动画用）'
    elif w >= 512 or h >= 512:
        f, algo, reason = 2, 'hybrid', '大图/背景/UI'
    else:
        f, algo, reason = 4, 'xbr', '小图（无骨骼）'

    # 尺寸保护：超 GL 纹理上限就降倍数
    while f > 1 and (w * f > MAX_TEX or h * f > MAX_TEX):
        f //= 2
        reason += ' [降为 x%d: 超 %d 上限]' % (f, MAX_TEX)

    if f <= 1:
        return 1, 'none', reason
    return f, algo, reason


def scale_xml(xml_path, out_path, factor):
    """把图集 xml 的所有 x/y/w/h/refx/refy 乘以 factor"""
    s = open(xml_path, encoding='utf-8-sig', errors='replace').read()
    bom = open(xml_path, 'rb').read(3) == b'\xef\xbb\xbf'

    def repl(m):
        k, v = m.group(1), int(m.group(2))
        return '%s="%d"' % (k, v * factor)

    s2 = re.sub(r'\b(x|y|w|h|refx|refy)="(-?\d+)"', repl, s)
    data = s2.encode('utf-8')
    if bom:
        data = b'\xef\xbb\xbf' + data
    with open(out_path, 'wb') as f:
        f.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='indir', default='art/source_png')
    ap.add_argument('--xml', dest='xmldir', default='art/source_xml')
    ap.add_argument('--out', dest='outdir', default='art/hd')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    pngs = sorted(glob.glob(os.path.join(args.indir, '*.png')))
    if not pngs:
        sys.exit('没有找到 PNG: %s' % args.indir)

    print('待处理 %d 张 PNG' % len(pngs))
    print()

    stats = {'processed': 0, 'skipped': 0, 'failed': 0}
    report = []
    t0 = time.time()

    for i, p in enumerate(pngs, 1):
        fn = os.path.basename(p)
        try:
            im = Image.open(p)
            w, h = im.size
        except Exception as e:
            print('[%3d/%d] %-28s 打开失败: %s' % (i, len(pngs), fn, e))
            stats['failed'] += 1
            continue

        xml_src = os.path.join(args.xmldir, fn.replace('.png', '.xml'))
        has_xml = os.path.exists(xml_src)

        factor, algo, reason = classify(fn, w, h, has_xml)
        out_png = os.path.join(args.outdir, fn)

        if algo == 'none':
            # 原样复制
            im.save(out_png)
            if has_xml:
                scale_xml(xml_src, os.path.join(args.outdir, fn.replace('.png', '.xml')), factor)
            print('[%3d/%d] %-28s %4dx%-4d 跳过（%s）' % (i, len(pngs), fn, w, h, reason))
            stats['skipped'] += 1
            report.append({'file': fn, 'w': w, 'h': h, 'factor': 1,
                           'algo': 'none', 'reason': reason})
            continue

        try:
            out = upscale(im, factor, algo)
            out.save(out_png, optimize=True)
            if has_xml:
                scale_xml(xml_src, os.path.join(args.outdir, fn.replace('.png', '.xml')), factor)
            print('[%3d/%d] %-28s %4dx%-4d -> %4dx%-4d  %-6s x%d  (%s)' % (
                i, len(pngs), fn, w, h, out.width, out.height, algo, factor, reason))
            stats['processed'] += 1
            report.append({'file': fn, 'w0': w, 'h0': h, 'w1': out.width,
                           'h1': out.height, 'factor': factor, 'algo': algo,
                           'reason': reason, 'xml': has_xml})
        except Exception as e:
            print('[%3d/%d] %-28s 处理失败: %s' % (i, len(pngs), fn, e))
            stats['failed'] += 1

    elapsed = time.time() - t0

    # 写报告
    rep_path = os.path.join(args.outdir, '_report.json')
    with open(rep_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(pngs),
            'stats': stats,
            'elapsed_sec': round(elapsed, 1),
            'items': report,
        }, f, ensure_ascii=False, indent=2)

    print()
    print('=' * 60)
    print('处理完成：成功 %d  跳过 %d  失败 %d  耗时 %.1f 秒' % (
        stats['processed'], stats['skipped'], stats['failed'], elapsed))
    print('输出目录：%s' % args.outdir)
    print('报告：%s' % rep_path)

    if stats['failed'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
