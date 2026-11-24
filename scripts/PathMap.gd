## 寻路：固定路径点插值。支持飞行单位直线飞（不走路径）
class_name PathMap
extends RefCounted

var points: PackedVector2Array = []
var seg_lengths: Array[float] = []
var total_length: float = 0.0

func _init(path_points: PackedVector2Array):
	points = path_points
	seg_lengths.clear()
	total_length = 0.0
	for i in range(points.size() - 1):
		var d := points[i].distance_to(points[i + 1])
		seg_lengths.append(d)
		total_length += d

## 按路径距离取坐标（dist 从 0 到 total_length）
func pos_at(dist: float) -> Vector2:
	if points.size() < 2:
		return points[0] if points.size() > 0 else Vector2.ZERO
	if dist <= 0.0:
		return points[0]
	var remain := dist
	for i in range(seg_lengths.size()):
		var seg := seg_lengths[i]
		if remain <= seg:
			var t := remain / maxf(seg, 0.001)
			return points[i].lerp(points[i + 1], t)
		remain -= seg
	return points[points.size() - 1]

## 路径进度 0..1
func progress_at(dist: float) -> float:
	return clampf(dist / maxf(total_length, 1.0), 0.0, 1.0)

## 默认路径：从左下进场，蛇形到右下城堡
static func default_path() -> PackedVector2Array:
	var s := GameConfig.GRID_SIZE
	return PackedVector2Array([
		Vector2(-40, 9.5 * s),
		Vector2(4.5 * s, 9.5 * s),
		Vector2(4.5 * s, 6.5 * s),
		Vector2(9.5 * s, 6.5 * s),
		Vector2(9.5 * s, 3.5 * s),
		Vector2(15.5 * s, 3.5 * s),
		Vector2(15.5 * s, 8.5 * s),
		Vector2(18.5 * s, 8.5 * s),
	])

## 可建塔的格子（避开路径）
static func buildable_cells(path: PackedVector2Array) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var s := GameConfig.GRID_SIZE
	var blocked := {}
	# 把路径经过的格子标记为不可建
	for i in range(path.size() - 1):
		var a := path[i]
		var b := path[i + 1]
		var steps := int(a.distance_to(b) / (s * 0.5)) + 1
		for k in range(steps + 1):
			var p := a.lerp(b, float(k) / maxf(steps, 1))
			var cx := int(floor(p.x / s))
			var cy := int(floor(p.y / s))
			for dy in range(-1, 2):
				for dx in range(-1, 2):
					blocked[Vector2i(cx + dx, cy + dy)] = true

	for cy in range(GameConfig.GRID_ROWS):
		for cx in range(GameConfig.GRID_COLS):
			var cell := Vector2i(cx, cy)
			if blocked.has(cell):
				continue
			# 边缘不建
			if cx < 1 or cy < 1 or cx >= GameConfig.GRID_COLS - 1 or cy >= GameConfig.GRID_ROWS - 1:
				continue
			out.append(cell)
	return out

static func cell_center(cell: Vector2i) -> Vector2:
	var s := GameConfig.GRID_SIZE
	return Vector2((cell.x + 0.5) * s, (cell.y + 0.5) * s)
