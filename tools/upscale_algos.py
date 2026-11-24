#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
像素画放大算法集合（纯代码渲染，不依赖 AI）
=============================================
针对原版那种 16×18 小部件的放大需求。

算法对比：
  nearest     最近邻    —— 硬块，零模糊，但锯齿明显
  scale2x/4x  EPX 系    —— 边缘平滑，保留像素风，无插值糊
  xbr         高级边缘  —— 曲线最圆润，适合椭圆/圆弧
  lanczos     通用插值  —— 平滑但会糊
  hybrid      混合      —— EPX 打底 + 轻锐化 + 边缘增强

用法：
  from upscale_algos import upscale
  upscale(src_img, 4, 'epx')   # 返回放大后的 PIL Image
"""
import numpy as np
from PIL import Image, ImageFilter


# ============================================================
# EPX / Scale2x —— 像素画放大经典算法
# 规则：对每个像素 P，看 4 邻域 A(上) B(右) C(左) D(下)
#   若 C==A 且 C!=D 且 A!=B  -> 左上角取 A
#   若 A==B 且 A!=C 且 B!=D  -> 右上角取 B
#   若 D==C 且 D!=B 且 C!=A  -> 左下角取 C
#   若 B==D 且 B!=A 且 D!=C  -> 右下角取 D
#   否则保持 P
# ============================================================
def scale2x_once(arr):
    """arr: (H,W,4) uint8 RGBA。返回 (2H,2W,4)"""
    h, w = arr.shape[:2]
    # 边界复制
    padded = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode='edge')
    P = padded[1:-1, 1:-1]
    A = padded[0:-2, 1:-1]   # 上
    B = padded[1:-1, 2:]     # 右
    C = padded[1:-1, 0:-2]   # 左
    D = padded[2:,   1:-1]   # 下

    out = np.empty((h * 2, w * 2, 4), dtype=np.uint8)

    # 用整条通道比较（RGBA 全等才算同色）
    def eq(x, y):
        return np.all(x == y, axis=-1)

    # 默认：四个子像素都取 P
    p00 = P.copy()
    p01 = P.copy()
    p10 = P.copy()
    p11 = P.copy()

    m1 = eq(C, A) & ~eq(C, D) & ~eq(A, B)
    p00[m1] = A[m1]

    m2 = eq(A, B) & ~eq(A, C) & ~eq(B, D)
    p01[m2] = B[m2]

    m3 = eq(D, C) & ~eq(D, B) & ~eq(C, A)
    p10[m3] = C[m3]

    m4 = eq(B, D) & ~eq(B, A) & ~eq(D, C)
    p11[m4] = D[m4]

    out[0::2, 0::2] = p00
    out[0::2, 1::2] = p01
    out[1::2, 0::2] = p10
    out[1::2, 1::2] = p11
    return out


def epx_upscale(im, factor=4):
    """EPX/Scale2x 放大，factor 必须是 2 的幂"""
    if factor & (factor - 1):
        raise ValueError('factor 必须是 2 的幂: 2,4,8')
    arr = np.array(im.convert('RGBA'))
    steps = int(np.log2(factor))
    for _ in range(steps):
        arr = scale2x_once(arr)
    return Image.fromarray(arr, 'RGBA')


# ============================================================
# xBR 简化版 —— 边缘检测插值，曲线更圆
# 参考 Hyllian 的 xBR-lv1 思路，针对 4 通道简化
# ============================================================
def xbr_upscale(im, factor=4, strength=1.0):
    """
    简化 xBR：
    1. 先做 EPX 得到干净边缘
    2. 再按梯度方向做加权平滑，只作用于半透明/<边缘> 区域
    这样既保留像素风的硬边，又让圆弧变圆润。
    """
    base = epx_upscale(im, factor)
    arr = np.array(base).astype(np.float32)

    # 权重图：alpha 边界附近才平滑
    a = arr[:, :, 3]
    gy = np.abs(np.gradient(a, axis=0))
    gx = np.abs(np.gradient(a, axis=1))
    edge = np.clip((gx + gy) / 64.0, 0, 1) * strength

    # 双线性平滑（只在边缘区生效）
    smoothed = np.array(
        base.filter(ImageFilter.GaussianBlur(radius=factor * 0.28))
    ).astype(np.float32)

    w = edge[:, :, None]
    out = arr * (1 - w) + smoothed * w
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


# ============================================================
# 混合方案：EPX + 锐化 + 边缘增强
# ============================================================
def hybrid_upscale(im, factor=4, sharpen=1.4, contrast=1.08):
    """
    先把 alpha 二值化保住轮廓，再 EPX 放大，最后轻锐化。
    适合小部件：既清晰又不糊。
    """
    src = im.convert('RGBA')

    # 1) alpha 保边：<32 全透明，>200 全不透明（去掉半透明脏边）
    arr = np.array(src)
    a = arr[:, :, 3]
    a2 = np.where(a < 32, 0, np.where(a > 200, 255, a))
    arr[:, :, 3] = a2
    src2 = Image.fromarray(arr, 'RGBA')

    # 2) EPX 放大
    up = epx_upscale(src2, factor)

    # 3) 颜色锐化（不碰 alpha）
    rgb = up.convert('RGB').filter(
        ImageFilter.UnsharpMask(radius=factor * 0.6, percent=int(sharpen * 100), threshold=2))
    out = rgb.convert('RGBA')
    out.putalpha(up.getchannel('A'))

    # 4) 轻微对比度提升，让金属/木质层次更明显
    if contrast != 1.0:
        from PIL import ImageEnhance
        rgb2 = ImageEnhance.Contrast(out.convert('RGB')).enhance(contrast)
        out2 = rgb2.convert('RGBA')
        out2.putalpha(out.getchannel('A'))
        out = out2

    return out


# ============================================================
# 统一入口
# ============================================================
def upscale(im, factor=4, algo='hybrid'):
    """
    algo:
      'nearest' 最近邻
      'epx'     EPX/Scale2x
      'xbr'     xBR 简化版
      'lanczos' 通用插值
      'hybrid'  EPX+锐化（推荐）
    """
    im = im.convert('RGBA')
    if algo == 'nearest':
        return im.resize((im.width * factor, im.height * factor), Image.NEAREST)
    if algo == 'epx':
        return epx_upscale(im, factor)
    if algo == 'xbr':
        return xbr_upscale(im, factor)
    if algo == 'lanczos':
        return im.resize((im.width * factor, im.height * factor), Image.LANCZOS)
    if algo == 'hybrid':
        return hybrid_upscale(im, factor)
    raise ValueError('未知算法: %s' % algo)


if __name__ == '__main__':
    import sys, os
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    factor = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    algo = sys.argv[4] if len(sys.argv) > 4 else 'hybrid'
    im = Image.open(src)
    out = upscale(im, factor, algo)
    out.save(dst)
    print('%s -> %s  %dx%d  algo=%s' % (src, dst, out.width, out.height, algo))
