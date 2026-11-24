#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
要塞围城 · 玩法数据全量导出
============================
从 assets/*.xml 提取全部游戏数据，输出为 JSON。

数据源（原版 3.2.1）：
  unitdef.xml      55 兵种
  towerdef.xml      6 塔
  basedef.xml       4 城堡
  buildingdef.xml  11 建筑
  upgradedef.xml   41 升级项（unit 16 / building 10 / stronghold 15）
  level01-14.xml   14 关卡（含波次、编队、对话）

输出：data/gamedata.json + 分项 json
"""
import os
import re
import json
import glob
import sys

ASSETS = '/root/workspace/siege/apk/unpacked/assets'
OUT = '/root/workspace/siege-td/data'

# ---- 数值字段（转成数字，保留整数/浮点原貌）----
NUM_FIELDS = {
    'id', 'ai', 'camp', 'shadow', 'level', 'maxhp', 'price', 'attack',
    'defense', 'speed', 'animspeed', 'cd', 'attackrange', 'guardrange',
    'scale', 'runspeed', 'arrowpenetration', 'range', 'attackspeed',
    'attime', 'gw', 'gh', 'amount', 'height', 'flyx', 'flyz', 'parma',
    'maxlevel', 'unlockatlevel', 'user', 'time', 'gx', 'gy', 'goldrate',
    'award', 'map', 'dialog', 'head',
}
# 这些即使看似数字也保持字符串（id 用作 key 时常需精确原文）
STR_FIELDS = {'name', 'type', 'motions', 'weapon', 'icon', 'description',
              'image1', 'image2', 'image3', 'shadow', 'flyname', 'res', 'mode'}


def conv(k, v):
    v = v.strip()
    if k in STR_FIELDS:
        return v
    if k in NUM_FIELDS:
        try:
            return int(v)
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return v
    # 未列出的字段：能转数字就转，否则原样
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def parse_attrs(s):
    """解析 `a="1" b="2"` 形式的属性串"""
    out = {}
    for m in re.finditer(r'(\w+)="([^"]*)"', s):
        k, v = m.group(1), m.group(2)
        out[k] = conv(k, v)
    return out


def read_xml(fn):
    p = os.path.join(ASSETS, fn)
    if not os.path.exists(p):
        sys.exit('缺少文件: %s' % p)
    return open(p, encoding='utf-8-sig', errors='replace').read()


# ============================================================
# 1. 兵种
# ============================================================
def export_units():
    s = read_xml('unitdef.xml')
    items = []
    for m in re.finditer(r'<Unit\s+([^/>]+)/>', s):
        items.append(parse_attrs(m.group(1)))
    return items


# ============================================================
# 2. 塔
# ============================================================
def export_towers():
    s = read_xml('towerdef.xml')
    items = []
    for m in re.finditer(r'<Tower\s+([^/>]+)/>', s):
        items.append(parse_attrs(m.group(1)))
    return items


# ============================================================
# 3. 城堡
# ============================================================
def export_bases():
    s = read_xml('basedef.xml')
    items = []
    for m in re.finditer(r'<Base\s+([^/>]+)/>', s):
        items.append(parse_attrs(m.group(1)))
    return items


# ============================================================
# 4. 建筑
# ============================================================
def export_buildings():
    s = read_xml('buildingdef.xml')
    items = []
    for m in re.finditer(r'<Building\s+([^/>]+)/>', s):
        items.append(parse_attrs(m.group(1)))
    return items


# ============================================================
# 5. 升级项（三个分组）
# ============================================================
def export_upgrades():
    s = read_xml('upgradedef.xml')
    groups = {}
    for m in re.finditer(r'<Upgrade\s+type="(\w+)">(.*?)</Upgrade>', s, re.S):
        gtype, body = m.group(1), m.group(2)
        items = []
        for im in re.finditer(r'<Item\s+([^/>]+)/>', body):
            items.append(parse_attrs(im.group(1)))
        groups[gtype] = items
    return groups


# ============================================================
# 6. 关卡（波次 + 编队 + 对话）
# ============================================================
def export_levels():
    levels = []
    for i in range(1, 15):
        fn = 'level%02d.xml' % i
        p = os.path.join(ASSETS, fn)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8-sig', errors='replace').read()

        root_m = re.search(r'<level\s+([^>]+)>', s)
        meta = parse_attrs(root_m.group(1)) if root_m else {}

        # 按出现顺序解析 group 与 dialog
        timeline = []
        wave_idx = 0
        for m in re.finditer(
                r'<group\s+([^>]*)>(.*?)</group>|<dialog\s+([^/>]*)/>', s, re.S):
            if m.group(3) is not None:
                # dialog 节点
                d = parse_attrs(m.group(3))
                d['_node'] = 'dialog'
                d['_wave'] = wave_idx
                timeline.append(d)
            else:
                wave_idx += 1
                attrs = parse_attrs(m.group(1))
                units = []
                for um in re.finditer(r'<unit\s+([^/>]+)/>', m.group(2)):
                    units.append(parse_attrs(um.group(1)))
                timeline.append({
                    '_node': 'group',
                    '_wave': wave_idx,
                    'time': attrs.get('time', 0),
                    'units': units,
                    'unit_count': len(units),
                })

        # 统计该关出兵总数
        total_units = sum(
            t['unit_count'] for t in timeline if t['_node'] == 'group')
        groups = [t for t in timeline if t['_node'] == 'group']
        dialogs = [t for t in timeline if t['_node'] == 'dialog']

        levels.append({
            'level': i,
            'file': fn,
            'meta': meta,
            'wave_count': len(groups),
            'total_units': total_units,
            'dialog_count': len(dialogs),
            'timeline': timeline,
        })
    return levels



# ============================================================
# 6.5 字符串表（plist 格式的对话/提示文本）
# ============================================================
def export_strings():
    """解析 stringtable_cn.xml（Apple plist），返回 {key: value}"""
    p = os.path.join(ASSETS, 'stringtable_cn.xml')
    if not os.path.exists(p):
        return {}
    s = open(p, encoding='utf-8-sig', errors='replace').read()
    out = {}
    # plist: <key>NAME</key>  <string>VALUE</string>
    for m in re.finditer(r'<key>([^<]+)</key>\s*<string>(.*?)</string>', s, re.S):
        k = m.group(1).strip()
        v = m.group(2)
        # 反转义
        v = v.replace('\\n', '\n').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # 去掉 XML 里可能残留的转义反斜杠
        out[k] = v.replace('\\', '')
    return out



# ============================================================
# 6.6 资源清单（动画 / 图集 / 音效），复刻时按清单准备素材
# ============================================================
def export_assets():
    """扫描 assets 目录，按类型列出文件清单"""
    out = {}
    groups = {
        'anim_bin':   '*.bin',
        'texture_pvr': '*.pvr',
        'image_png':  '*.png',
        'map':        '*.map',
        'effect':     '*.eff',
        'font':       '*.fnt',
        'sound_wav':  '*.wav',
        'sound_mp3':  '*.mp3',
    }
    for key, pat in groups.items():
        files = sorted(glob.glob(os.path.join(ASSETS, pat)))
        out[key] = [os.path.basename(f) for f in files]
        out[key + '_count'] = len(files)

    # 兵种用到的动作资源（motions 字段 -> 对应 .bin）
    return out


# ============================================================
# 7. 其他：Config.xml、对话文本、字符串表
# ============================================================
def export_misc():
    misc = {}

    # Config.xml
    p = os.path.join(ASSETS, 'Config.xml')
    if os.path.exists(p):
        s = open(p, encoding='utf-8-sig', errors='replace').read()
        misc['config_raw'] = s.strip()

    # 对话（dialog 文件）
    for cand in ['dialog.xml', 'dialogs.xml', 'stringtable_cn.xml']:
        fp = os.path.join(ASSETS, cand)
        if os.path.exists(fp):
            s = open(fp, encoding='utf-8-sig', errors='replace').read()
            misc[cand.replace('.xml', '_raw_len')] = len(s)

    # 用到的动画资源（从兵种 motions 汇总）
    return misc


def main():
    os.makedirs(OUT, exist_ok=True)

    print('读取中...')
    units = export_units()
    towers = export_towers()
    bases = export_bases()
    buildings = export_buildings()
    upgrades = export_upgrades()
    levels = export_levels()
    strings = export_strings()
    assets = export_assets()
    misc = export_misc()

    print('  兵种     %3d' % len(units))
    print('  塔       %3d' % len(towers))
    print('  城堡     %3d' % len(bases))
    print('  建筑     %3d' % len(buildings))
    print('  升级     %3d（%s）' % (
        sum(len(v) for v in upgrades.values()),
        ', '.join('%s:%d' % (k, len(v)) for k, v in upgrades.items())))
    print('  关卡     %3d' % len(levels))
    print('  文本     %3d 条' % len(strings))
    print('  资源     bin=%d pvr=%d png=%d map=%d eff=%d fnt=%d wav=%d mp3=%d' % (
        assets['anim_bin_count'], assets['texture_pvr_count'], assets['image_png_count'],
        assets['map_count'], assets['effect_count'], assets['font_count'],
        assets['sound_wav_count'], assets['sound_mp3_count']))
    print()

    data = {
        '_meta': {
            'game': '要塞围城 (Fortress Siege)',
            'package': 'com.easytech.fortressEgame',
            'version': '3.2.1',
            'engine': 'easytech (ARM32, 480x320 logic)',
            'exported_by': 'siege-td/data/export_gamedata.py',
            'counts': {
                'units': len(units), 'towers': len(towers),
                'bases': len(bases), 'buildings': len(buildings),
                'upgrades': sum(len(v) for v in upgrades.values()),
                'levels': len(levels),
            },
        },
        'units': units,
        'towers': towers,
        'bases': bases,
        'buildings': buildings,
        'upgrades': upgrades,
        'levels': levels,
        'strings': strings,
        'asset_manifest': assets,
        'misc': misc,
    }

    full = os.path.join(OUT, 'gamedata.json')
    with open(full, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('写入 %s  (%.1f KB)' % (full, os.path.getsize(full) / 1024))

    # 分项文件，方便单独查看/给 AI 用
    parts = {
        'units.json': units,
        'towers.json': towers,
        'bases.json': bases,
        'buildings.json': buildings,
        'upgrades.json': upgrades,
        'levels.json': levels,
        'strings.json': strings,
        'asset_manifest.json': assets,
    }
    for name, obj in parts.items():
        fp = os.path.join(OUT, name)
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print('写入 %-18s (%.1f KB)' % (fp, os.path.getsize(fp) / 1024))

    # 关卡再拆成单独文件（复刻时按关实现）
    lv_dir = os.path.join(OUT, 'levels')
    os.makedirs(lv_dir, exist_ok=True)
    for lv in levels:
        fp = os.path.join(lv_dir, 'level%02d.json' % lv['level'])
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(lv, f, ensure_ascii=False, indent=2)
    print('写入 %s/  %d 个关卡文件' % (lv_dir, len(levels)))

    # 汇总校验
    print()
    print('=== 汇总 ===')
    print('兵种阵营分布:', end=' ')
    camp = {}
    for u in units:
        camp[u.get('camp')] = camp.get(u.get('camp'), 0) + 1
    print(camp, '（1=玩家 2=敌方）')
    print('兵种类型分布:', end=' ')
    types = {}
    for u in units:
        types[u.get('type')] = types.get(u.get('type'), 0) + 1
    print(types)
    print('塔类型:', [t['type'] for t in towers])
    print('关卡出兵总数:', sum(l['total_units'] for l in levels))


if __name__ == '__main__':
    main()
