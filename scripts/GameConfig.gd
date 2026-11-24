## 游戏配置与数值表
## 所有可调参数集中在这里，方便平衡性调整
extends RefCounted

# ============ 屏幕与网格 ============
const VIEW_W := 1280
const VIEW_H := 720
const GRID_SIZE := 64              # 每格像素
const GRID_COLS := 20
const GRID_ROWS := 11

# ============ 经济 ============
const START_GOLD := 150
const START_LIVES := 20
const WAVE_CLEAR_BONUS := 25        # 每波清完奖励（+ 波数 × 5）

# ============ 兵种（敌方）============
# speed 单位：像素/秒（按 1280 宽换算）
# hp 随波数增长：hp * (1 + 0.18 * (wave-1))
const ENEMIES := {
	"grunt": {
		"name": "步兵", "hp": 40, "speed": 72, "damage": 1, "gold": 8,
		"color": Color("#ef4444"), "radius": 13, "armor": 0,
	},
	"runner": {
		"name": "快贼", "hp": 26, "speed": 130, "damage": 1, "gold": 9,
		"color": Color("#f97316"), "radius": 10, "armor": 0,
	},
	"shield": {
		"name": "盾兵", "hp": 120, "speed": 54, "damage": 2, "gold": 16,
		"color": Color("#a78bfa"), "radius": 15, "armor": 6,
	},
	"flyer": {
		"name": "飞行兵", "hp": 55, "speed": 100, "damage": 1, "gold": 12,
		"color": Color("#22d3ee"), "radius": 12, "armor": 0, "flying": true,
	},
	"ram": {
		"name": "攻城锤", "hp": 420, "speed": 34, "damage": 5, "gold": 40,
		"color": Color("#94a3b8"), "radius": 20, "armor": 12,
	},
}

# ============ 塔 ============
const TOWERS := {
	"arrow": {
		"name": "箭塔", "cost": 70, "range": 190, "damage": 12,
		"rate": 1.6, "color": Color("#6ee7b7"), "desc": "单体快射 · 反人海",
		"splash": 0.0, "slow": 0.0, "pierce": false,
	},
	"cannon": {
		"name": "炮塔", "cost": 110, "range": 210, "damage": 34,
		"rate": 0.65, "color": Color("#fbbf24"), "desc": "范围溅射 · 反集群",
		"splash": 62.0, "slow": 0.0, "pierce": false,
	},
	"frost": {
		"name": "冰塔", "cost": 90, "range": 170, "damage": 6,
		"rate": 1.1, "color": Color("#60a5fa"), "desc": "减速 55%",
		"splash": 0.0, "slow": 1.8, "pierce": false,
	},
	"ballista": {
		"name": "弩炮", "cost": 140, "range": 260, "damage": 58,
		"rate": 0.45, "color": Color("#f472b6"), "desc": "破甲高伤 · 反重甲",
		"splash": 0.0, "slow": 0.0, "pierce": true,
	},
}

const MAX_TOWER_LEVEL := 5
const UPGRADE_DAMAGE_MUL := 1.55     # 每级伤害倍率
const UPGRADE_RANGE_MUL := 1.06
const UPGRADE_RATE_MUL := 1.05
const SELl_RATIO := 0.5              # 拆除返还比例

# ============ 主动技能 ============
const SKILLS := {
	"meteor": {"name": "陨石", "cd": 22.0, "damage": 90, "radius": 110, "count": 3},
	"gaze":   {"name": "石化", "cd": 28.0, "freeze": 2.6},
	"repair": {"name": "修复", "cd": 18.0, "amount": 3},
}

# ============ 波次 ============
# 每波的兵种组合：{类型: 数量}
func get_wave(wave: int) -> Array:
	var out := []
	var n := wave
	# 基础步兵
	for i in range(4 + int(n * 1.2)):
		out.append("grunt")
	if n >= 2:
		for i in range(2 + int(n * 0.7)):
			out.append("runner")
	if n >= 3:
		for i in range(1 + int(n * 0.5)):
			out.append("shield")
	if n >= 5:
		for i in range(1 + int(n * 0.6)):
			out.append("flyer")
	if n >= 6:
		for i in range(1 + int((n - 6) / 3)):
			out.append("ram")
	return out

func hp_multiplier(wave: int) -> float:
	return 1.0 + 0.18 * (wave - 1)
