## 高清贴图仓库
## 把 assets/sprites/ 里的 AI 重画图按原版逻辑尺寸显示
class_name SpriteBank
extends RefCounted

# 原版尺寸表（逻辑像素），从原游戏 XML 提取
# 高清图是它的 4 倍，显示时按原尺寸
const SIZES := {
	# 城堡（basedef.xml: gw×gh 格，height 视觉高度）
	"castle_0": {"w": 85,  "h": 171, "name": "木寨"},
	"castle_1": {"w": 109, "h": 202, "name": "木堡"},
	"castle_2": {"w": 90,  "h": 167, "name": "要塞"},
	"castle_3": {"w": 121, "h": 211, "name": "坚城"},

	# 塔（towerdef.xml）
	"tower_Arrow_Tower":       {"w": 58,  "h": 136, "name": "箭塔"},
	"tower_Big_Arrow_Tower":   {"w": 60,  "h": 173, "name": "大箭塔"},
	"tower_Square_Tower":      {"w": 94,  "h": 172, "name": "方塔"},
	"tower_Big_Square_Tower":  {"w": 94,  "h": 182, "name": "大方塔"},
	"tower_Round_Tower":       {"w": 100, "h": 191, "name": "圆塔"},
	"tower_Big_Round_Tower":   {"w": 100, "h": 211, "name": "大圆塔"},

	# 建筑（buildingdef.xml）
	"building_Church":          {"w": 61, "h": 134, "name": "教堂"},
	"building_Bow_Workshop":    {"w": 56, "h": 102, "name": "弓作坊"},
	"building_Shield_Workshop": {"w": 55, "h": 98,  "name": "盾作坊"},
	"building_Sword_Workshop":  {"w": 56, "h": 110, "name": "剑作坊"},
	"building_Stables":         {"w": 54, "h": 117, "name": "马厩"},
	"building_Magic_Tower":     {"w": 60, "h": 141, "name": "魔法塔"},
	"building_Wooden_House":    {"w": 45, "h": 92,  "name": "木屋"},
	"building_House":           {"w": 44, "h": 96,  "name": "石屋"},
	"building_Enemy_Tent":      {"w": 52, "h": 95,  "name": "敌营帐"},
	"building_Big_Enemy_Tent":  {"w": 59, "h": 110, "name": "大敌营帐"},
}

# 缓存
static var _cache := {}
static var _missing := {}


## 加载贴图（首次调用时读盘，之后走缓存）
static func tex(key: String) -> Texture2D:
	if _cache.has(key):
		return _cache[key]
	if _missing.has(key):
		return null
	var path := "res://assets/sprites/%s.png" % key
	if not ResourceLoader.exists(path):
		_missing[key] = true
		return null
	var t := load(path)
	_cache[key] = t
	return t


## 原版逻辑尺寸
static func size_of(key: String) -> Vector2:
	var d = SIZES.get(key, null)
	if d == null:
		return Vector2(64, 128)
	return Vector2(d["w"], d["h"])


## 中文名
static func display_name(key: String) -> String:
	var d = SIZES.get(key, null)
	return d["name"] if d != null else key
