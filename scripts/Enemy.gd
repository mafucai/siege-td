## 敌人：沿路径推进，到达终点扣血
class_name Enemy
extends Node2D

var type_id: String = "grunt"
var data: Dictionary = {}
var hp: float = 40.0
var max_hp: float = 40.0
var speed: float = 72.0
var damage: int = 1
var gold: int = 8
var armor: float = 0.0
var radius: float = 13.0
var flying: bool = false
var color: Color = Color.RED

var dist: float = 0.0           # 沿路径距离
var slow_timer: float = 0.0
var frozen_timer: float = 0.0
var dead: bool = false
var wobble: float = 0.0

signal reached_end(enemy)
signal died(enemy)

func setup(p_type: String, wave: int) -> void:
	type_id = p_type
	data = GameConfig.ENEMIES[p_type]
	var mul := 1.0 + 0.18 * (wave - 1)
	max_hp = data["hp"] * mul
	hp = max_hp
	speed = data["speed"]
	damage = data["damage"]
	gold = data["gold"]
	armor = data.get("armor", 0.0)
	radius = data["radius"]
	flying = data.get("flying", false)
	color = data["color"]
	wobble = randf() * TAU

func tick(delta: float, path: PathMap) -> void:
	if dead:
		return
	if frozen_timer > 0.0:
		frozen_timer -= delta
		queue_redraw()
		return
	if slow_timer > 0.0:
		slow_timer -= delta

	var mul := 0.45 if slow_timer > 0.0 else 1.0
	dist += speed * mul * delta

	var p := path.pos_at(dist)
	if flying:
		# 飞行单位直接在起点终点之间插值
		var t := path.progress_at(dist)
		p.y -= 38.0 + sin(wobble + Time.get_ticks_msec() * 0.004) * 4.0
	position = p

	if dist >= path.total_length:
		dead = true
		reached_end.emit(self)
		return

func take_damage(amount: float, ignore_armor: bool = false) -> void:
	if dead:
		return
	var real := amount if ignore_armor else maxf(1.0, amount - armor)
	hp -= real
	if hp <= 0.0:
		dead = true
		died.emit(self)

func apply_slow(duration: float) -> void:
	slow_timer = maxf(slow_timer, duration)

func apply_freeze(duration: float) -> void:
	frozen_timer = maxf(frozen_timer, duration)

func _draw() -> void:
	var c := color
	if frozen_timer > 0.0:
		c = Color("#93c5fd")
	elif slow_timer > 0.0:
		c = c.lerp(Color("#60a5fa"), 0.5)

	# 主体
	if type_id == "flyer":
		# 菱形
		var pts := PackedVector2Array([
			Vector2(0, -radius), Vector2(radius, 0),
			Vector2(0, radius), Vector2(-radius, 0)
		])
		draw_colored_polygon(pts, c)
	elif type_id == "ram":
		draw_rect(Rect2(-radius, -radius * 0.8, radius * 2, radius * 1.6), c)
	else:
		draw_circle(Vector2.ZERO, radius, c)

	# 描边
	draw_arc(Vector2.ZERO, radius, 0, TAU, 20, c.darkened(0.35), 2.0)

	# 血条
	var w := radius * 2.2
	var bar_y := -radius - 9.0
	draw_rect(Rect2(-w / 2, bar_y, w, 4), Color(0, 0, 0, 0.55))
	var ratio := clampf(hp / max_hp, 0.0, 1.0)
	var bc := Color("#4ade80") if ratio > 0.5 else (Color("#fbbf24") if ratio > 0.22 else Color("#ef4444"))
	draw_rect(Rect2(-w / 2, bar_y, w * ratio, 4), bc)
