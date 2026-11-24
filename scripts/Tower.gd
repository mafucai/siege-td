## 塔：自动索敌、开火、可升级
extends Node2D


const GameConfig = preload("res://scripts/GameConfig.gd")
const PathMap = preload("res://scripts/PathMap.gd")

var type_id: String = "arrow"
var data: Dictionary = {}
var level: int = 1
var cell: Vector2i = Vector2i.ZERO
var paid: int = 0

var cooldown: float = 0.0
var aim_angle: float = 0.0
var target = null
var range_ring_alpha: float = 0.0

signal fired(tower, target, stats)

func setup(p_type: String, p_cell: Vector2i) -> void:
	type_id = p_type
	data = GameConfig.TOWERS[p_type]
	cell = p_cell
	paid = data["cost"]
	level = 1
	position = PathMap.cell_center(p_cell)

func stats() -> Dictionary:
	var k := pow(GameConfig.UPGRADE_DAMAGE_MUL, level - 1)
	return {
		"damage": data["damage"] * k,
		"range": data["range"] * pow(GameConfig.UPGRADE_RANGE_MUL, level - 1),
		"rate": data["rate"] * pow(GameConfig.UPGRADE_RATE_MUL, level - 1),
		"splash": data.get("splash", 0.0),
		"slow": data.get("slow", 0.0),
		"pierce": data.get("pierce", false),
	}

func upgrade_cost() -> int:
	return int(data["cost"] * 0.75 * level)

func can_upgrade() -> bool:
	return level < GameConfig.MAX_TOWER_LEVEL

func do_upgrade() -> void:
	level += 1
	queue_redraw()

func sell_value() -> int:
	return int(paid * GameConfig.SELl_RATIO)

func find_target(enemies: Array):
	var st: Dictionary = stats()
	var best = null
	var best_dist := -1.0
	for e in enemies:
		if e.dead:
			continue
		if e.flying and type_id == "cannon":
			continue  # 炮塔打不到飞行
		var d: float = position.distance_to(e.position)
		if d > st["range"] + e.radius:
			continue
		if e.dist > best_dist:
			best_dist = e.dist
			best = e
	return best

func tick(delta: float, enemies: Array) -> void:
	cooldown -= delta
	var st: Dictionary = stats()
	if target == null or target.dead:
		target = find_target(enemies)
	if target != null:
		aim_angle = (target.position - position).angle()
		if cooldown <= 0.0:
			cooldown = 1.0 / st["rate"]
			fired.emit(self, target, st)
	queue_redraw()

func _draw() -> void:
	var c: Color = data["color"]
	var r := 22.0

	# 底座
	draw_circle(Vector2.ZERO, r, Color(0.06, 0.09, 0.15))
	draw_arc(Vector2.ZERO, r, 0, TAU, 28, c, 3.0)

	# 炮管
	var dir := Vector2.from_angle(aim_angle)
	draw_line(Vector2.ZERO, dir * 26.0, c, 7.0)
	draw_circle(dir * 26.0, 4.0, c.lightened(0.3))

	# 等级
	var f := ThemeDB.fallback_font
	draw_string(f, Vector2(-6, r + 16), "Lv%d" % level, HORIZONTAL_ALIGNMENT_CENTER, -1, 13, c)
