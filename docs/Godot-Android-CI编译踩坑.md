# Godot 游戏用 GitHub Actions 编译 Android APK · 踩坑记录

> 项目：堡垒塔防（`mafucai/siege-td`）· Godot 4.3 · 2026-11-25
> 结果：CI 10 次失败后全绿，出 45.5MB 双架构 APK
> 适用：任何「无桌面环境、只能用手机 + GitHub Actions」做 Godot Android 导出的场景

---

## 零、一句话总结

**Godot 4.3 的 Android 导出必须在 `project.godot` 里写 `textures/vram_compression/import_etc2_astc=true`，否则导出失败且错误信息是空的。**

这一个坑占了全部调试时间的 60%。

---

## 一、整体架构

```
手机 proot Ubuntu（无桌面）
   ↓ 写 GDScript + project.godot（纯文本，不需要编辑器）
   ↓ git push
GitHub Actions ubuntu-24.04（原生 x86_64）
   ↓ 下载 Godot headless + 导出模板
   ↓ --headless --import → --export-debug
   ↓ apksigner 签名
   ↓ upload artifact
手机下载 APK 安装
```

**关键点**：Godot 编辑器不需要图形界面也能导出，`--headless` 就够。这打通了「只有手机」的限制。

---

## 二、本地验证环境（重要）

本机是 **arm64**，而 Godot 官方只发 **x86_64** Linux 版。用 qemu 可以跑起来：

```bash
# 装 x86_64 交叉库
apt-get install -y libc6-amd64-cross

# 下载 Godot
python3 -c "
import urllib.request
url='https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip'
req=urllib.request.Request(url, headers={'User-Agent':'curl/7.68'})
open('godot.zip','wb').write(urllib.request.urlopen(req,timeout=280).read())
"
unzip -q godot.zip && chmod +x Godot_v4.3-stable_linux.x86_64

# 用 qemu 跑
qemu-x86_64-static -L /usr/x86_64-linux-gnu ./Godot_v4.3-stable_linux.x86_64 --version
# 输出: 4.3.stable.official.77dcf97d8
```

### 本地能验证什么、不能验证什么

| 能力 | 本地 qemu | GitHub Actions |
|---|---|---|
| GDScript 语法检查 | ✅ | ✅ |
| 项目导入 | ✅ | ✅ |
| `--export-pack`（生成 .pck） | ✅ | ✅ |
| **Android APK 导出** | ❌ | ✅ |

**为什么本地不能导出 APK**：Godot 在导出最后一步要调用 `keytool`/`javac` 签名。qemu 模拟的 x86_64 Godot 无法调用 arm64 的 java：

```
qemu-x86_64-static: /usr/lib/jvm/.../java: Invalid ELF image for this architecture
```

所以**本地验语法，CI 验导出**，分工明确。

---

## 三、坑清单（按遇到顺序）

### 坑 1：`class_name` 在 CI 环境不注册

**症状**（30+ 条同类错误）：

```
SCRIPT ERROR: Parse Error: Identifier "GameConfig" not declared in the current scope.
SCRIPT ERROR: Parse Error: Could not find type "PathMap" in the current scope.
```

**原因**：Godot 4 的 `class_name` 需要在 `.godot/global_script_class_cache.cfg` 里注册，注册发生在**完整项目导入**时。CI 里如果不先 `--import` 就直接导出，缓存是空的。

**解决**：**不用 `class_name`，改用 `preload`**。

```gdscript
extends Node2D

const GameConfig = preload("res://scripts/GameConfig.gd")
const PathMap    = preload("res://scripts/PathMap.gd")
const Enemy      = preload("res://scripts/Enemy.gd")
const Tower      = preload("res://scripts/Tower.gd")
```

优点：加载顺序确定、不依赖导入缓存、CI 稳。
**前提**：不能有循环引用。检查方法：

```python
deps = {
 'GameConfig': [],
 'PathMap': ['GameConfig'],
 'Enemy': ['GameConfig'],
 'Tower': ['GameConfig','PathMap','Enemy'],
 'Main': ['GameConfig','PathMap','Enemy','Tower'],
}
# 拓扑排序，有环就报错
```

---

### 坑 2：`preload` 的 const 不能当类型标注

**症状**：

```
Parse Error: Could not find type "PathMap" in the current scope.
```

**原因**：`const PathMap = preload(...)` 引入的是**值**，不是**类型**。GDScript 的类型系统不认。

**解决**：去掉自定义类的类型标注，用 `Variant`（不写类型）。

```gdscript
# ✗ 错
var path: PathMap
func tick(delta: float, path: PathMap) -> void:
func find_target(enemies: Array) -> Enemy:

# ✓ 对
var path
func tick(delta: float, path) -> void:
func find_target(enemies: Array):
```

---

### 坑 3：`:=` 从无类型表达式推断失败

**症状**：

```
Parse Error: Cannot infer the type of "st" variable because the value doesn't have a set type.
```

**原因**：`:=` 要求右边类型明确。若右边是 `Variant`（比如访问 `Dictionary` 的键、或调用无返回类型标注的函数），推断失败。

**解决**：显式标注。

```gdscript
# ✗ 错
var st := selected_tower.stats()       # stats() 没标返回类型
var p  := path.pos_at(dist)            # pos_at 的 path 是 Variant
var c  := color                        # color 是 Variant
var t  := Tower.new()                  # Tower 是 preload 的 const

# ✓ 对
var st: Dictionary = selected_tower.stats()
var p:  Vector2    = path.pos_at(dist)
var c:  Color      = color
var t             = Tower.new()        # 不加 := 就不用推断
```

**速查表**：

| 右边是 | 写法 |
|---|---|
| 有明确返回类型的函数 | `var x := f()` |
| 无返回类型标注的函数 / Variant | `var x: Type = f()` |
| `Dictionary` 取值 | `var x: Type = d["k"]` |
| `preload` 的 const `.new()` | `var x = Cls.new()`（不用 `:=`） |

---

### 坑 4：GitHub Actions 的 heredoc 缩进破坏 `.tres` / `.cfg`

**症状**：Godot 报配置错误，但看不出哪里错。

**原因**：YAML 里 `run: |` 块内所有行相对缩进会被保留。写

```yaml
run: |
  cat > file.tres <<'EOF'
  [gd_resource type="EditorSettings" format=3]
  ...
  EOF
```

生成的文件**每行前面有空格**，`.tres` / `export_presets.cfg` 解析失败。

`sed -i 's/^          //'` 这种补救很脆（缩进层数一变就失效）。

**解决**：**把生成逻辑抽成 Python 脚本放进仓库，CI 只调用**。

```
tools/
  gen_editor_settings.py    # 生成 ~/.config/godot/editor_settings-4.3.tres
  gen_export_presets.py     # 生成 export_presets.cfg
```

```yaml
- name: Write export presets
  env:
    PACKAGE_NAME: ${{ env.PACKAGE_NAME }}
    KEYSTORE_PATH: ${{ github.workspace }}/debug.keystore
  run: python3 tools/gen_export_presets.py
```

脚本里加**自校验**，出问题立刻失败而不是让 Godot 报空错误：

```python
for i, ln in enumerate(open("export_presets.cfg", encoding="utf-8"), 1):
    if ln.startswith(" "):
        sys.exit("第 %d 行有行首空格: %r" % (i, ln))
```

---

### 坑 5：Editor Settings 必须写，光有 export_presets 不够

**症状**：

```
ERROR: Cannot export project with preset "Android" due to configuration errors:
Debug keystore not configured in the Editor Settings nor in the preset.
A valid Java SDK path is required in Editor Settings.
A valid Android SDK path is required in Editor Settings.
```

**原因**：Godot 的 Android 导出校验读的是 **EditorSettings**（`~/.config/godot/editor_settings-4.3.tres`），不是 export presets。

**解决**：CI 里生成这个文件。

```python
# tools/gen_editor_settings.py
out = os.path.expanduser("~/.config/godot/editor_settings-4.3.tres")
lines = [
    '[gd_resource type="EditorSettings" format=3]',
    '',
    '[resource]',
    'export/android/java_sdk_path = "%s"' % java_sdk,
    'export/android/android_sdk_path = "%s"' % android_sdk,
    'export/android/debug_keystore = "%s"' % keystore,
    'export/android/debug_keystore_user = "androiddebugkey"',
    'export/android/debug_keystore_pass = "android"',
    'export/android/force_system_user = false',
    'export/android/shutdown_adb_on_exit = true',
    '',
]
```

**三个路径的可靠来源**：

| 键 | 来源 |
|---|---|
| `java_sdk_path` | `${JAVA_HOME}`（`actions/setup-java` 自动设置） |
| `android_sdk_path` | `${ANDROID_HOME}`（`android-actions/setup-android` 自动设置） |
| `debug_keystore` | `${GITHUB_WORKSPACE}/debug.keystore`（自己 keytool 生成） |

**别用 `dirname(dirname(readlink -f $(which javac)))` 推导** —— 在不同 runner 上层级不一致，会算错。

---

### 坑 6：keystore 走预设级 `keystore/debug*` 更可靠

Godot 的 Android 导出有两套 keystore 键：

| 位置 | 键名 |
|---|---|
| EditorSettings | `export/android/debug_keystore` |
| **export_presets.cfg** | `keystore/debug` / `keystore/debug_user` / `keystore/debug_password` |

预设级的好处：路径跟着项目走，不依赖用户级配置。

但**最简单的做法是根本不签名**：

```ini
package/signed=false
```

让 Godot 导出未签名 APK，CI 里自己签：

```bash
"${BUILD_TOOLS}/zipalign" -p -f 4 build/unsigned.apk build/aligned.apk
"${BUILD_TOOLS}/apksigner" sign \
  --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias androiddebugkey \
  --out build/signed.apk build/aligned.apk
"${BUILD_TOOLS}/apksigner" verify build/signed.apk
```

这样 Godot 完全不碰 keystore，少一个失败点。

---

### 坑 7（最坑）：`import_etc2_astc` 未启用，且报错为空

**症状**：

```
ERROR: Cannot export project with preset "Android" due to configuration errors:
                                        ↑ 冒号后面一个字都没有
   at: _fs_changed (editor/editor_node.cpp:1012)
```

前面所有配置看起来都对：模板齐全、SDK 路径正确、keystore 存在、`export-pack` 能成功生成 30KB 的 `.pck`。**唯独 APK 导出失败，且不给任何原因。**

**定位过程**（这一段值得记）：

1. 下载 Godot 4.3 源码：`platform/android/export/export_plugin.cpp`
   - GitHub raw 直连被重置 → 用镜像 `https://ghproxy.net/https://raw.githubusercontent.com/...`
2. 找到 `has_valid_export_configuration()` —— 这个函数有 `r_error = err`，错误非空
3. 找到 `has_valid_project_configuration()` —— **这个函数里有一段只置 `valid = false` 却不写 `err`**：

```cpp
bool EditorExportPlatformAndroid::has_valid_project_configuration(...) {
    String err;
    bool valid = true;
    ...
    if (!ResourceImporterTextureSettings::should_import_etc2_astc()) {
        valid = false;          // ← 不追加 err！
    }
    ...
    if (!err.is_empty()) {
        r_error = err;
    }
    return valid;               // valid=false 但 r_error 为空 → 报错信息空白
}
```

4. 再查 `should_import_etc2_astc()`：

```cpp
bool ResourceImporterTextureSettings::should_import_etc2_astc() {
    if (GLOBAL_GET("rendering/textures/vram_compression/import_etc2_astc")) {
        return true;
    }
    return OS::get_singleton()->get_preferred_texture_format()
           == OS::PREFERRED_TEXTURE_FORMAT_ETC2_ASTC;
}
```

**解决**：`project.godot` 加一行

```ini
[rendering]

textures/vram_compression/import_etc2_astc=true
```

加完立刻成功。

**为什么这是硬要求**：Android 移动 GPU 主要支持 ETC2/ASTC 压缩纹理。桌面 Linux 默认用 S3TC/BPTC，所以**在桌面导出时不会触发这个检查，只有 Android 平台会**。

---

## 四、完整可用的 CI 骨架

```yaml
name: Build Android APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  GODOT_VERSION: 4.3
  PACKAGE_NAME: com.example.mygame

jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 40
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'

      - uses: android-actions/setup-android@v3
        with:
          packages: 'platform-tools'

      - name: Install Android platform & build-tools
        run: |
          sdkmanager --install "platforms;android-33" "platforms;android-34" \
            "build-tools;33.0.2" "build-tools;34.0.0" "platform-tools"

      - name: Download Godot headless
        run: |
          mkdir -p "$HOME/godot" && cd "$HOME/godot"
          curl -fL --retry 3 -o godot.zip \
            "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip"
          unzip -q godot.zip
          mv "Godot_v${GODOT_VERSION}-stable_linux.x86_64" godot
          chmod +x godot

      - name: Download export templates
        run: |
          cd "$HOME/godot"
          curl -fL --retry 3 -o templates.tpz \
            "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_export_templates.tpz"
          mkdir -p "$HOME/.local/share/godot/export_templates"
          unzip -q templates.tpz -d "$HOME/.local/share/godot/export_templates"
          mv "$HOME/.local/share/godot/export_templates/templates" \
             "$HOME/.local/share/godot/export_templates/${GODOT_VERSION}.stable"

      - name: Create debug keystore
        run: |
          keytool -genkeypair -v -keystore debug.keystore \
            -storepass android -keypass android -alias androiddebugkey \
            -keyalg RSA -keysize 2048 -validity 10000 \
            -dname "CN=Android Debug,O=Android,C=US"

      - name: Write export presets & editor settings
        env:
          PACKAGE_NAME: ${{ env.PACKAGE_NAME }}
          KEYSTORE_PATH: ${{ github.workspace }}/debug.keystore
          JAVA_SDK: ${{ env.JAVA_HOME }}
        run: |
          python3 tools/gen_export_presets.py
          python3 tools/gen_editor_settings.py

      - name: Import project
        run: "$HOME/godot/godot" --headless --path . --import

      - name: Export APK
        run: |
          mkdir -p build
          "$HOME/godot/godot" --headless --path . \
            --export-debug "Android" build/game.apk

      - name: Sign APK
        run: |
          BT="${ANDROID_HOME}/build-tools/34.0.0"
          "${BT}/zipalign" -p -f 4 build/game.apk build/aligned.apk
          "${BT}/apksigner" sign --ks debug.keystore \
            --ks-pass pass:android --key-pass pass:android \
            --ks-key-alias androiddebugkey \
            --out build/game-signed.apk build/aligned.apk
          "${BT}/apksigner" verify build/game-signed.apk

      - uses: actions/upload-artifact@v4
        with:
          name: apk
          path: build/game-signed.apk
```

配套的 `project.godot` 必需项：

```ini
[application]
config/name="游戏名"
run/main_scene="res://scenes/Main.tscn"
config/features=PackedStringArray("4.3", "GL Compatibility")

[rendering]
textures/vram_compression/import_etc2_astc=true    ; ← Android 导出硬要求
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"

[display]
window/size/viewport_width=1280
window/size/viewport_height=720
window/stretch/mode="canvas_items"
window/handheld/orientation=4
```

---

## 五、排查速查表

| 症状 | 原因 | 解法 |
|---|---|---|
| `Identifier "X" not declared` | `class_name` 未注册 | 改 `preload` |
| `Could not find type "X"` | `preload` const 不能作类型 | 去掉类型标注 |
| `Cannot infer the type of "x"` | `:=` 右边是 Variant | 显式标注或去掉 `:=` |
| 配置错误但**消息为空** | `import_etc2_astc` 未启用 | `project.godot` 加该键 |
| `Debug keystore not configured` | 没写 EditorSettings | 生成 `editor_settings-4.3.tres` |
| `Invalid Java SDK path` | 路径推导错 | 用 `${JAVA_HOME}` |
| `Missing 'platform-tools'` | SDK 不完整 | `sdkmanager --install platform-tools` |
| `Could not find version of build tools` | build-tools 版本名不匹配 | 装 `33.0.2` 和 `34.0.0` |
| `.tres` 解析失败 | heredoc 带缩进 | 改用 Python 脚本生成 |
| `cannot connect to daemon at tcp:5037` | 无 emulator（**无害**） | 忽略 |
| 无效 ELF image（本地） | qemu x86_64 调 arm64 java | 本地只验语法，导出交给 CI |

---

## 六、下载 CI 日志的正确姿势

GitHub 的日志/artifact 下载会 302 到签名 URL。**重定向时不能带 Authorization 头**，否则 401：

```python
class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        n = super().redirect_request(req, fp, code, msg, headers, newurl)
        if n is not None:
            for k in list(n.headers):
                if k.lower() == 'authorization':
                    del n.headers[k]
        return n

opener = urllib.request.build_opener(NoAuthRedirect())
# 用 opener 请求 api.github.com/.../artifacts/{id}/zip
```

`/actions/jobs/{id}/logs` 和 `/actions/artifacts/{id}/zip` 都是这个行为。

---

## 七、时间成本记录

| 阶段 | 失败次数 | 主要耗时 |
|---|---|---|
| GDScript 语法（坑 1-3） | 4 | 本地 qemu 验证，快 |
| CI 配置（坑 4-6） | 5 | 每次 CI 约 3-5 分钟，共约 40 分钟 |
| **空错误定位（坑 7）** | **1** | **读源码 20 分钟，一次命中** |

**教训**：
- 前 3 个坑靠本地 qemu 验证，改了立刻知道对不对，效率最高
- 中间 5 个坑每次都靠 CI 反馈，一轮 5 分钟，很慢
- **最后一个坑没有继续猜**，而是直接读 Godot 源码 —— 20 分钟解决，比再猜 5 轮快

**如果重来一次**：遇到「报错为空」时应该**立刻去读源码**，而不是反复调配置。错误信息为空的 bug，只能从源码层面找到。

---

## 八、相关文件

| 文件 | 说明 |
|---|---|
| `workspace/siege-td/project.godot` | 项目配置（含 ETC2 关键项） |
| `workspace/siege-td/tools/gen_export_presets.py` | 生成 export_presets.cfg |
| `workspace/siege-td/tools/gen_editor_settings.py` | 生成 EditorSettings |
| `workspace/siege-td/.github/workflows/build.yml` | CI 流程 |
| `workspace/siege-td/scripts/*.gd` | 游戏逻辑（preload 风格） |
| 仓库 | https://github.com/mafucai/siege-td |
| 成品 | `workspace/siege-td/out/堡垒塔防.apk`（45.5MB） |
