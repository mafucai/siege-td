# 玩法数据说明

> 从原版 `com.easytech.fortressEgame` v3.2.1 全量导出
> 生成脚本：`data/export_gamedata.py`
> 交叉校验：8 项全部与原 XML 一致

---

## 文件一览

| 文件 | 大小 | 内容 |
|---|---|---|
| `gamedata.json` | 994 KB | 全部数据（含 levels 完整波次） |
| `units.json` | 22 KB | 55 兵种 |
| `towers.json` | 3 KB | 6 塔 |
| `bases.json` | 1.3 KB | 4 城堡 |
| `buildings.json` | 3.6 KB | 11 建筑 |
| `upgrades.json` | 9.3 KB | 41 升级项（3 组） |
| `levels.json` | 848 KB | 14 关完整时间线 |
| `levels/level01-14.json` | - | 单关拆分（复刻时按关实现） |
| `strings.json` | 9.6 KB | 180 条对话/提示文本 |
| `asset_manifest.json` | 6.4 KB | 素材清单（bin/pvr/png/map/eff/fnt/wav/mp3） |

---

## 数据规模

```
兵种     55（玩家 18 / 敌方 37）
塔        6（bow ×2, crossbow ×2, catapult ×2）
城堡      4（4 级）
建筑     11
升级项   41（unit 16 / building 10 / stronghold 15）
关卡     14（共 6450 个出兵点）
文本    180 条
```

---

## 兵种字段（21 个）

```json
{
  "name": "Swordman",
  "id": 6,
  "ai": 1,
  "camp": 1,              // 1=玩家 2=敌方
  "shadow": 0,
  "type": "swordman",
  "level": 1,
  "maxhp": 500,
  "price": 80,
  "attack": 100,
  "defense": 20,
  "speed": 9,
  "animspeed": 11.5,
  "cd": 1.4,              // 攻击冷却（秒）
  "attackrange": 1,       // 攻击距离（格）
  "guardrange": 4,        // 警戒距离（格）
  "scale": 1,
  "motions": "swordsman_3",
  "weapon": "sword",
  "runspeed": 2,
  "arrowpenetration": 1
}
```

### 兵种类型分布

| type | 数量 | 说明 |
|---|---|---|
| swordman | 14 | 剑士系 |
| spearman | 11 | 长矛系（含 Axeman/Pikeman/RoyalGuard） |
| archer | 7 | 弓手系 |
| knight | 6 | 骑士系（含 Arthur/Paladin） |
| cavalry | 6 | 骑兵系 |
| hammer | 4 | 锤兵系 |
| crossboman | 2 | 弩手（原文拼写如此） |
| bugler | 2 | 号手（关卡触发用） |
| batteringram | 1 | 攻城锤 |
| catapult | 1 | 投石车 |
| churchman | 1 | 牧师 |

---

## 塔字段

```json
{
  "name": "Arrow Tower",
  "type": "bow",
  "id": 207,
  "range": 16,            // 射程（格）
  "attack": 15,
  "cd": 1.4,
  "attackspeed": 1,
  "attime": 0.5,          // 出手动画时间
  "price": 280,
  "gw": 2, "gh": 2,       // 占地格数
  "amount": 1,            // 同时攻击目标数
  "maxhp": 1000,
  "defense": 0,
  "height": 75,           // 视觉高度（z 排序用）
  "image1": "generaltower_1.png",       // 主体
  "image2": "generaltower_1_b1.png",    // 底座
  "image3": "generaltower_1_b2.png",    // 阴影层
  "shadow": "2x2.png",
  "flyname": "towerarrow",              // 弹道动画名
  "flyx": 0, "flyz": -20                // 弹道起点偏移
}
```

### 6 塔对比

| name | type | range | attack | cd | price | gw×gh | amount |
|---|---|---|---|---|---|---|---|
| Arrow Tower | bow | 16 | 15 | 1.4 | 280 | 2×2 | 1 |
| Big Arrow Tower | bow | 16 | 28 | 1.2 | 420 | 2×2 | 1 |
| Square Tower | crossbow | 16 | 60 | 2.0 | 500 | 3×3 | 1 |
| Big Square Tower | crossbow | 16 | 85 | 1.8 | 700 | 3×3 | 1 |
| Round Tower | catapult | 17 | 120 | 2.4 | 950 | 4×4 | 3 |
| Big Round Tower | catapult | 17 | 150 | 2.0 | 1200 | 4×4 | 4 |

---

## 城堡（4 级）

| level | name | maxhp | gw×gh | height | price |
|---|---|---|---|---|---|
| 1 | Wooden Keep | 1600 | 5×4 | 80 | 100 |
| 2 | Wooden Base | 2400 | 5×4 | 95 | 100 |
| 3 | Fortress | 3200 | 5×4 | 80 | 100 |
| 4 | Stronghold | 4000 | 5×4 | 100 | 100 |

---

## 建筑（11 种）

| name | type | price | gw×gh | maxhp | height |
|---|---|---|---|---|---|
| Church | BuildingDefense | 280 | 3×3 | 500 | 50 |
| Bow Workshop | RangeAttack | 260 | 3×3 | 400 | 42 |
| Shield Workshop | UnitDefense | 250 | 3×3 | 400 | 38 |
| Sword Workshop | MeleeAttack | 220 | 3×3 | 400 | 40 |
| Stables | Speed | 230 | 3×3 | 400 | 40 |
| Magic Tower | Magic | 300 | 3×3 | 450 | 60 |
| Wooden House | House | 50 | 2×2 | 250 | 50 |
| （其余 4 种见 JSON） | | | | | |

---

## 升级系统（3 组共 41 项）

```json
"upgrades": {
  "unit": [       // 16 项：兵种升级
    {"name":"Spearman","id":0,"maxlevel":10,"unlockatlevel":1,"price":50,
     "icon":"icon_troops_spearman.png","description":"Spearman Description"}
  ],
  "building": [   // 10 项：建筑升级
    {"name":"...","type":"...","id":..,"maxlevel":10,"unlockatlevel":..,
     "price":..,"icon":"...","description":"..."}
  ],
  "stronghold": [ // 15 项：城堡/要塞升级
    ...
  ]
}
```

**关键机制**：
- `unlockatlevel` = 玩家等级达到多少解锁
- `maxlevel` = 最高等级（多为 10）
- `price` = 每级升级花费基数
- `unlockatlevel: 99` 表示**未开放**（原版留的坑，如 RoyalGuard）

---

## 关卡结构

每关的 `timeline` 是按时间排序的节点数组，两种类型：

```json
// 出兵群组
{"_node":"group", "_wave":2, "time":6,
 "units":[{"name":"bugler","gx":-3,"gy":20}], "unit_count":1}

// 对话
{"_node":"dialog", "dialog":19, "head":0, "_wave":1}
```

**字段含义**：
- `time` = 相对关卡开始的秒数
- `gx/gy` = 出生格坐标（负数是屏幕外，从边缘进场）
- `dialog` = 文本 id，去 `strings.json` 查 `dialogue{N}`
- `_wave` = 第几个 group（用于波次计数）

### 14 关概览

| 关 | 地图 | 波数 | 总兵力 | 对话 | award | goldrate |
|---|---|---|---|---|---|---|
| 1 | 1 | 22 | 219 | 12 | 100 | 1 |
| 2 | 2 | 28 | 344 | 6 | 200 | 0.95 |
| 3 | 3 | 22 | 344 | 7 | 300 | 0.9 |
| 4 | 4 | 30 | 364 | 6 | 400 | 0.85 |
| 5 | 5 | 26 | 293 | 8 | 500 | 0.8 |
| 6 | 6 | 26 | 453 | 6 | 600 | 0.7 |
| 7 | 7 | 27 | 348 | 6 | 700 | 0.6 |
| 8 | 8 | 25 | 233 | 6 | 800 | 0.5 |
| 9 | 9 | 23 | 260 | 7 | 900 | 0.4 |
| 10 | 10 | 27 | 322 | 6 | 1000 | 0.3 |
| **11** | 11 | **118** | **1586** | **33** | 1000 | 0.1 |
| 12 | 12 | 52 | 679 | 8 | 600 | 0.2 |
| 13 | 13 | 46 | 546 | 12 | 800 | 0.2 |
| 14 | 14 | 32 | 459 | 10 | 1000 | 0.2 |

**第 11 关是最终决战**：118 波、1586 个敌人、33 段对话，`goldrate=0.1`（金币收入极低，逼迫精打细算）。

**`goldrate` 机制**：关卡内金币获取倍率。1.0 = 正常，0.1 = 只有 10%，也就是同样杀敌只拿到十分之一的钱。数值越低越难。

---

## 文本（180 条）

```json
{
  "dialogue1": "侦察兵报告有一支敌军正在\n靠近我军。",
  "dialogue2": "他们又来了！",
  ...
}
```

`\n` 是原版的换行位置，复刻时要保留（对话框有固定换行）。

除了 `dialogue*`，还有 UI 文案、按钮文字等。

---

## 素材清单

```json
{
  "anim_bin": ["archer_1.bin", ...],      "anim_bin_count": 59,
  "texture_pvr": [...],                   "texture_pvr_count": 40,
  "image_png": [...],                     "image_png_count": 130,
  "map": ["map01.map", ...],              "map_count": 14,
  "effect": ["effect_fire.eff", ...],     "effect_count": 11,
  "font": ["font1_cn_hd.fnt", ...],       "font_count": 7,
  "sound_wav": [...],                     "sound_wav_count": 29,
  "sound_mp3": [...],                     "sound_mp3_count": 8
}
```

---

## 重新生成

```bash
cd /root/workspace/siege-td
python3 data/export_gamedata.py
```

脚本会自动交叉校验并打印汇总。

---

## 复刻时的注意事项

### 1. 坐标系统
原版是 **480×320 逻辑坐标**。复刻到 1280×720 需要 ×2.667。
但 `gx/gy` 是**格子坐标**（不是像素），需要知道原版格子大小才能换算。

### 2. 数值平衡
`cd`（攻击冷却）、`attackrange`（攻击距离）、`guardrange`（警戒距离）这三个字段决定战斗手感，改动会破坏平衡。**建议先照搬，跑通后再调。**

### 3. 兵种 ai 字段
`ai=1` 的具体行为需要从原版 `CActionAI` 反汇编推断，目前只有编号。复刻时可先统一用「前进 + 遇敌攻击」简化，后续细化。

### 4. 塔的 `flyname`
弹道动画名对应 `.bin` 文件（如 `towerarrow.bin`、`ballista_arrow1.bin`）。复刻时如果没有骨骼动画系统，可以用简单的飞行物替代。

### 5. `unlockatlevel: 99`
表示**原版就没开放**（如 RoyalGuard 皇家卫队）。复刻时可以自己决定是否启用。
