#!/usr/bin/env python3
"""生成 Godot 4.3 EditorSettings，写入 Android 导出所需的三个路径。
环境变量：JAVA_SDK、ANDROID_HOME、KEYSTORE_PATH
"""
import os
import sys

out = os.path.expanduser("~/.config/godot/editor_settings-4.3.tres")
java_sdk = os.environ.get("JAVA_SDK", "").strip()
android_sdk = os.environ.get("ANDROID_HOME", "").strip()
keystore = os.environ.get("KEYSTORE_PATH", "").strip()

checks = [
    ("JAVA_SDK", java_sdk, os.path.join(java_sdk, "bin", "javac")),
    ("ANDROID_HOME", android_sdk, android_sdk),
    ("KEYSTORE", keystore, keystore),
]
for label, base, probe in checks:
    ok = base and os.path.exists(probe)
    print("%-14s %-62s %s" % (label, base or "(空)", "OK" if ok else "MISSING"))
    if not ok:
        sys.exit("路径无效: %s -> %s" % (label, probe))

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

os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# 自校验：不能有行首空格（会让 tres 解析失败）
with open(out, encoding="utf-8") as f:
    for i, ln in enumerate(f, 1):
        if ln.startswith(" "):
            sys.exit("第 %d 行有行首空格: %r" % (i, ln))
print("写入 %s 并通过格式校验" % out)
