## 主游戏：状态机、波次调度、输入、渲染
extends Node2D


const GameConfig = preload("res://scripts/GameConfig.gd")
const PathMap = preload("res://scripts/PathMap.gd")
const Enemy = preload("res://scripts/Enemy.gd")
const Tower = preload("res://scripts/Tower.gd")

enum Phase { PREP, COMBAT, OVER }

# --- 运行状态 ---
var gold: int = GameConfig.START_GOLD
var lives: int = GameConfig.START_LIVES
var wave: int = 0
var phase: Phase = Phase.PREP
var speed_mul: int = 1

var path
var buildable: Array[Vector2i] = []
var towers: Dictionary = {}          # Vector2i -> Tower
var enemies: Array[Enemy] = []
var shots: Array = []                # 飞行中的子弹
var floats: Array = []               # 飘字

var queue: Array[String] = []
var wave_timer: float = 0.0
var spawn_interval: float = 0.55

var selected_cell: Vector2i = Vector2i(-1, -1)
var selected_tower = null
var hover_cell: Vector2i = Vector2i(-1, -1)

var skills: Dictionary = {}
var game_over_timer: float = 0.0

# --- UI 节点（代码生成，避免场景文件依赖）---
var ui_layer: CanvasLayer
var lbl_wave: Label
var lbl_gold: Label
var lbl_lives: Label
var btn_start: Button
var btn_speed: Button
var panel_build: PanelContainer
var panel_tower: PanelContainer
var btn_skills: Dictionary = {}

func _ready() -> void:
	randomize()
	path = PathMap.new(PathMap.default_path())
	buildable = PathMap.buildable_cells(path.points)
	for k in GameConfig.SKILLS:
		skills[k] = {"cd": 0.0}
	_build_ui()
	queue_redraw()

# ============================================================
# UI 构建（全部用代码，不依赖 .tscn 里的节点树）
# ============================================================
func _build_ui() -> void:
	ui_layer = CanvasLayer.new()
	add_child(ui_layer)

	var top := HBoxContainer.new()
	top.position = Vector2(16, 12)
	top.add_theme_constant_override("separation", 24)
	ui_layer.add_child(top)

	lbl_wave = _mk_label("第 0 波")
	lbl_gold = _mk_label("金币 150")
	lbl_lives = _mk_label("生命 20")
	top.add_child(lbl_wave)
	top.add_child(lbl_gold)
	top.add_child(lbl_lives)

	btn_start = Button.new()
	btn_start.text = "开战"
	btn_start.custom_minimum_size = Vector2(120, 44)
	btn_start.position = Vector2(GameConfig.VIEW_W - 150, 12)
	btn_start.pressed.connect(_on_start_pressed)
	ui_layer.add_child(btn_start)

	btn_speed = Button.new()
	btn_speed.text = "1x"
	btn_speed.custom_minimum_size = Vector2(64, 44)
	btn_speed.position = Vector2(GameConfig.VIEW_W - 220, 12)
	btn_speed.pressed.connect(_on_speed_pressed)
	ui_layer.add_child(btn_speed)

	# 技能条
	var skill_box := HBoxContainer.new()
	skill_box.position = Vector2(16, GameConfig.VIEW_H - 62)
	skill_box.add_theme_constant_override("separation", 10)
	ui_layer.add_child(skill_box)
	for key in GameConfig.SKILLS:
		var b := Button.new()
		b.text = GameConfig.SKILLS[key]["name"]
		b.custom_minimum_size = Vector2(96, 46)
		b.pressed.connect(_on_skill.bind(key))
		skill_box.add_child(b)
		btn_skills[key] = b

	# 建造面板
	panel_build = PanelContainer.new()
	panel_build.position = Vector2(GameConfig.VIEW_W - 300, GameConfig.VIEW_H - 210)
	panel_build.custom_minimum_size = Vector2(284, 196)
	ui_layer.add_child(panel_build)

	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 6)
	panel_build.add_child(vb)
	vb.add_child(_mk_label("建造"))
	for key in GameConfig.TOWERS:
		var td: Dictionary = GameConfig.TOWERS[key]
		var b := Button.new()
		b.text = "%s  %d金  %s" % [td["name"], td["cost"], td["desc"]]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(268, 34)
		b.pressed.connect(_on_build.bind(key))
		vb.add_child(b)
	panel_build.visible = false

	# 塔操作面板
	panel_tower = PanelContainer.new()
	panel_tower.position = Vector2(GameConfig.VIEW_W - 300, GameConfig.VIEW_H - 170)
	panel_tower.custom_minimum_size = Vector2(284, 156)
	ui_layer.add_child(panel_tower)

	var vb2 := VBoxContainer.new()
	vb2.add_theme_constant_override("separation", 6)
	panel_tower.add_child(vb2)
	var lbl_t := _mk_label("塔")
	lbl_t.name = "Title"
	vb2.add_child(lbl_t)

	var btn_up := Button.new()
	btn_up.name = "Upgrade"
	btn_up.text = "升级"
	btn_up.custom_minimum_size = Vector2(268, 40)
	btn_up.pressed.connect(_on_upgrade)
	vb2.add_child(btn_up)

	var btn_sell := Button.new()
	btn_sell.name = "Sell"
	btn_sell.text = "拆除"
	btn_sell.custom_minimum_size = Vector2(268, 36)
	btn_sell.pressed.connect(_on_sell)
	vb2.add_child(btn_sell)
	panel_tower.visible = false

func _mk_label(txt: String) -> Label:
	var l := Label.new()
	l.text = txt
	l.add_theme_font_size_override("font_size", 22)
	l.add_theme_color_override("font_color", Color("#e2e8f0"))
	return l

# ============================================================
# 输入
# ============================================================
func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		hover_cell = _cell_from_pos(event.position)
		queue_redraw()
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var cell := _cell_from_pos(event.position)
		# 点在 UI 区域就不处理
		if event.position.y > GameConfig.VIEW_H - 230 and event.position.x > GameConfig.VIEW_W - 310:
			return
		_on_cell_clicked(cell)

func _cell_from_pos(p: Vector2) -> Vector2i:
	return Vector2i(int(p.x / GameConfig.GRID_SIZE), int(p.y / GameConfig.GRID_SIZE))

func _on_cell_clicked(cell: Vector2i) -> void:
	if towers.has(cell):
		selected_tower = towers[cell]
		selected_cell = Vector2i(-1, -1)
		panel_tower.visible = true
		panel_build.visible = false
		_refresh_tower_panel()
	elif buildable.has(cell):
		selected_cell = cell
		selected_tower = null
		panel_build.visible = true
		panel_tower.visible = false
	else:
		selected_cell = Vector2i(-1, -1)
		selected_tower = null
		panel_build.visible = false
		panel_tower.visible = false
	queue_redraw()

# ============================================================
# 建造 / 升级 / 拆除
# ============================================================
func _on_build(type_id: String) -> void:
	if selected_cell == Vector2i(-1, -1):
		return
	var cost: int = GameConfig.TOWERS[type_id]["cost"]
	if gold < cost:
		_toast("金币不足")
		return
	gold -= cost
	var t := Tower.new()
	add_child(t)
	t.setup(type_id, selected_cell)
	t.fired.connect(_on_tower_fired)
	towers[selected_cell] = t
	selected_cell = Vector2i(-1, -1)
	panel_build.visible = false
	_refresh_top()
	queue_redraw()

func _on_upgrade() -> void:
	if selected_tower == null:
		return
	if not selected_tower.can_upgrade():
		_toast("已满级")
		return
	var c: int = selected_tower.upgrade_cost()
	if gold < c:
		_toast("金币不足")
		return
	gold -= c
	selected_tower.paid += c
	selected_tower.do_upgrade()
	_refresh_top()
	_refresh_tower_panel()

func _on_sell() -> void:
	if selected_tower == null:
		return
	gold += selected_tower.sell_value()
	towers.erase(selected_tower.cell)
	selected_tower.queue_free()
	selected_tower = null
	panel_tower.visible = false
	_refresh_top()
	queue_redraw()

func _refresh_tower_panel() -> void:
	if selected_tower == null:
		panel_tower.visible = false
		return
	var vb := panel_tower.get_child(0)
	var title: Label = vb.get_node("Title")
	var up: Button = vb.get_node("Upgrade")
	var sl: Button = vb.get_node("Sell")
	var d: Dictionary = selected_tower.data
	title.text = "%s  Lv%d" % [d["name"], selected_tower.level]
	if selected_tower.can_upgrade():
		up.text = "升级  %d金" % selected_tower.upgrade_cost()
		up.disabled = gold < selected_tower.upgrade_cost()
	else:
		up.text = "已满级"
		up.disabled = true
	sl.text = "拆除  +%d金" % selected_tower.sell_value()

# ============================================================
# 技能
# ============================================================
func _on_skill(key: String) -> void:
	if skills[key]["cd"] > 0.0 or phase == Phase.OVER:
		return
	var cfg: Dictionary = GameConfig.SKILLS[key]
	skills[key]["cd"] = cfg["cd"]
	match key:
		"meteor":
			_cast_meteor(cfg)
		"gaze":
			for e in enemies:
				e.apply_freeze(cfg["freeze"])
			_toast("石化！")
		"repair":
			lives = min(GameConfig.START_LIVES, lives + cfg["amount"])
			_refresh_top()
			_toast("+%d 生命" % cfg["amount"])

func _cast_meteor(cfg: Dictionary) -> void:
	var sorted := enemies.duplicate()
	sorted.sort_custom(func(a, b): return a.dist > b.dist)
	var picks := sorted.slice(0, cfg["count"])
	if picks.is_empty():
		picks = [null]
	for e in picks:
		var pos: Vector2 = e.position if e != null else Vector2(GameConfig.VIEW_W * 0.5, GameConfig.VIEW_H * 0.4)
		floats.append({"pos": pos, "text": "陨石", "life": 0.5, "tt": 0.5, "color": Color("#f87171")})
		for en in enemies:
			if not en.dead and en.position.distance_to(pos) < cfg["radius"]:
				en.take_damage(cfg["damage"], true)
	queue_redraw()

# ============================================================
# 波次控制
# ============================================================
func _on_start_pressed() -> void:
	if phase != Phase.PREP:
		return
	wave += 1
	queue = _make_wave(wave)
	wave_timer = 0.0
	phase = Phase.COMBAT
	_refresh_top()
	queue_redraw()

func _on_speed_pressed() -> void:
	speed_mul = 2 if speed_mul == 1 else 1
	btn_speed.text = "%dx" % speed_mul

# ============================================================
# 主循环
# ============================================================
func _physics_process(delta: float) -> void:
	if phase == Phase.OVER:
		game_over_timer += delta
		queue_redraw()
		return

	for k in skills:
		if skills[k]["cd"] > 0.0:
			skills[k]["cd"] = maxf(0.0, skills[k]["cd"] - delta)

	for s in range(speed_mul):
		_step(delta)

	_update_ui_state()
	queue_redraw()

func _step(delta: float) -> void:
	# 出怪
	if phase == Phase.COMBAT:
		wave_timer += delta
		if not queue.is_empty() and wave_timer >= spawn_interval:
			wave_timer = 0.0
			var type_id: String = queue.pop_front()
			var e := Enemy.new()
			add_child(e)
			e.setup(type_id, wave)
			e.reached_end.connect(_on_enemy_reached)
			e.died.connect(_on_enemy_died)
			enemies.append(e)

	# 敌人
	for e in enemies.duplicate():
		e.tick(delta, path)

	# 清掉已经 free 的引用
	enemies = enemies.filter(func(x): return is_instance_valid(x) and not x.dead)

	# 塔
	for t in towers.values():
		t.tick(delta, enemies)

	# 子弹
	for i in range(shots.size() - 1, -1, -1):
		var s: Dictionary = shots[i]
		s["life"] -= delta
		if s["life"] <= 0.0:
			_resolve_shot(s)
			shots.remove_at(i)

	# 飘字
	for i in range(floats.size() - 1, -1, -1):
		var f: Dictionary = floats[i]
		f["life"] -= delta
		f["pos"] += Vector2(0, -30 * delta)
		if f["life"] <= 0.0:
			floats.remove_at(i)

	# 波次结束判定
	if phase == Phase.COMBAT and queue.is_empty() and _alive_count() == 0:
		phase = Phase.PREP
		var bonus := 25 + wave * 5
		gold += bonus
		_toast("守住第 %d 波  +%d" % [wave, bonus])

func _alive_count() -> int:
	var n := 0
	for e in enemies:
		if not e.dead:
			n += 1
	return n

# ============================================================
# 战斗结算
# ============================================================
func _on_tower_fired(tower, target, st: Dictionary) -> void:
	shots.append({
		"from": tower.position,
		"to": target.position,
		"target": target,
		"damage": st["damage"],
		"splash": st["splash"],
		"slow": st["slow"],
		"pierce": st["pierce"],
		"color": tower.data["color"],
		"life": 0.12,
		"tt": 0.12,
	})

func _resolve_shot(s: Dictionary) -> void:
	var tgt = s["target"]
	if tgt == null or tgt.dead:
		return
	tgt.take_damage(s["damage"], s["pierce"])
	if s["slow"] > 0.0:
		tgt.apply_slow(s["slow"])
	if s["splash"] > 0.0:
		for e in enemies:
			if e == tgt or e.dead:
				continue
			if e.position.distance_to(tgt.position) < s["splash"]:
				e.take_damage(s["damage"] * 0.55, s["pierce"])

func _on_enemy_died(e) -> void:
	gold += e.gold
	_toast_at(e.position, "+%d" % e.gold, Color("#fbbf24"))
	e.queue_free()

func _on_enemy_reached(e) -> void:
	lives -= e.damage
	e.queue_free()
	_refresh_top()
	if lives <= 0:
		lives = 0
		phase = Phase.OVER

# ============================================================
# 渲染
# ============================================================
func _draw() -> void:
	# 背景
	draw_rect(Rect2(0, 0, GameConfig.VIEW_W, GameConfig.VIEW_H), Color("#0b1220"))

	# 网格
	var s := GameConfig.GRID_SIZE
	for cx in range(GameConfig.GRID_COLS + 1):
		draw_line(Vector2(cx * s, 0), Vector2(cx * s, GameConfig.GRID_ROWS * s), Color(1, 1, 1, 0.03), 1.0)
	for cy in range(GameConfig.GRID_ROWS + 1):
		draw_line(Vector2(0, cy * s), Vector2(GameConfig.VIEW_W, cy * s), Color(1, 1, 1, 0.03), 1.0)

	# 路径
	var pts: PackedVector2Array = path.points
	draw_polyline(pts, Color("#1f2937"), 54.0, true)
	draw_polyline(pts, Color("#2b3648"), 34.0, true)

	# 城堡
	var endp: Vector2 = pts[pts.size() - 1]
	_draw_castle(endp)

	# 可建格提示
	if hover_cell != Vector2i(-1, -1) and buildable.has(hover_cell) and not towers.has(hover_cell):
		var c: Vector2 = PathMap.cell_center(hover_cell)
		draw_rect(Rect2(c - Vector2(s, s) * 0.42, Vector2(s, s) * 0.84), Color(0.4, 0.9, 0.7, 0.12))

	# 选中格
	if selected_cell != Vector2i(-1, -1):
		var c: Vector2 = PathMap.cell_center(selected_cell)
		draw_rect(Rect2(c - Vector2(s, s) * 0.42, Vector2(s, s) * 0.84), Color(0.98, 0.8, 0.2, 0.28))

	# 选中塔的射程
	if selected_tower != null:
		var st: Dictionary = selected_tower.stats()
		draw_circle(selected_tower.position, st["range"], Color(1, 1, 0.4, 0.06))
		draw_arc(selected_tower.position, st["range"], 0, TAU, 48, Color(1, 1, 0.4, 0.35), 2.0)

	# 子弹
	for sh in shots:
		var k: float = 1.0 - sh["life"] / sh["tt"]
		var p: Vector2 = sh["from"].lerp(sh["to"], k)
		draw_circle(p, 5.0, sh["color"])

	# 飘字
	for f in floats:
		var a: float = clampf(f["life"] / f["tt"], 0.0, 1.0)
		var col: Color = f["color"]
		col.a = a
		draw_string(ThemeDB.fallback_font, f["pos"], f["text"], HORIZONTAL_ALIGNMENT_CENTER, -1, 22, col)

	# 结束画面
	if phase == Phase.OVER:
		draw_rect(Rect2(0, 0, GameConfig.VIEW_W, GameConfig.VIEW_H), Color(0, 0, 0, 0.72))
		draw_string(ThemeDB.fallback_font,
			Vector2(GameConfig.VIEW_W * 0.5 - 120, GameConfig.VIEW_H * 0.42),
			"城堡失守", HORIZONTAL_ALIGNMENT_LEFT, -1, 52, Color("#ef4444"))
		draw_string(ThemeDB.fallback_font,
			Vector2(GameConfig.VIEW_W * 0.5 - 90, GameConfig.VIEW_H * 0.52),
			"坚守到第 %d 波" % wave, HORIZONTAL_ALIGNMENT_LEFT, -1, 26, Color("#cbd5e1"))

func _draw_castle(c: Vector2) -> void:
	var w := 100.0
	# 城墙
	draw_rect(Rect2(c.x - w * 0.5, c.y - 34, w, 40), Color("#334155"))
	draw_rect(Rect2(c.x - w * 0.5, c.y - 34, w, 8), Color("#475569"))
	# 门
	draw_rect(Rect2(c.x - 14, c.y - 10, 28, 16), Color("#1e293b"))
	# 主楼
	draw_rect(Rect2(c.x - 22, c.y - 74, 44, 40), Color("#3f4b5e"))
	# 旗
	var flag := PackedVector2Array([Vector2(c.x, c.y - 108), Vector2(c.x + 26, c.y - 96), Vector2(c.x, c.y - 84)])
	draw_colored_polygon(flag, Color("#f87171"))

# ============================================================
# UI 刷新
# ============================================================
func _make_wave(n: int) -> Array[String]:
	var out: Array[String] = []
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
	out.shuffle()
	return out

func _refresh_top() -> void:
	lbl_wave.text = "第 %d 波" % wave
	lbl_gold.text = "金币 %d" % gold
	lbl_lives.text = "生命 %d" % lives

func _update_ui_state() -> void:
	_refresh_top()
	btn_start.disabled = phase != Phase.PREP
	btn_start.text = "开战" if phase == Phase.PREP else "战斗中"
	for key in btn_skills:
		var cd: float = skills[key]["cd"]
		var b: Button = btn_skills[key]
		var base: String = GameConfig.SKILLS[key]["name"]
		b.text = base if cd <= 0.0 else "%s %.0fs" % [base, cd]
		b.disabled = cd > 0.0

func _toast(msg: String) -> void:
	_toast_at(Vector2(GameConfig.VIEW_W * 0.5, 90), msg, Color("#fbbf24"))

func _toast_at(pos: Vector2, msg: String, col: Color) -> void:
	floats.append({"pos": pos, "text": msg, "life": 1.1, "tt": 1.1, "color": col})
