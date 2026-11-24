#!/usr/bin/env python3
"""生成 Godot Android 导出预设 export_presets.cfg。
环境变量：PACKAGE_NAME（可选）、KEYSTORE_PATH（可选，默认 ./debug.keystore）
"""
import os
import sys

pkg = os.environ.get("PACKAGE_NAME", "com.mafucai.fortresstd").strip()
ks = os.environ.get("KEYSTORE_PATH", os.path.abspath("debug.keystore")).strip()

if not os.path.exists(ks):
    sys.exit("keystore 不存在: %s" % ks)

preset = f'''[preset.0]

name="Android"
platform="Android"
runnable=true
advanced_options=false
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="build/fortress-td.apk"
pathex=""
encryption_include_filters=""
encryption_exclude_filters=""
seed=0
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug=""
custom_template/release=""
gradle_build/use_gradle_build=false
gradle_build/gradle_build_directory=""
gradle_build/android_source_template=""
gradle_build/compress_native_libraries=false
gradle_build/export_format=0
gradle_build/min_sdk=""
gradle_build/target_sdk=""
architectures/armeabi-v7a=true
architectures/arm64-v8a=true
architectures/x86=false
architectures/x86_64=false
version/code=1
version/name="1.0"
package/unique_name="{pkg}"
package/name="堡垒塔防"
package/signed=true
keystore/debug="{ks}"
keystore/debug_user="androiddebugkey"
keystore/debug_password="android"
keystore/release=""
keystore/release_user=""
keystore/release_password=""
package/app_category=2
package/retain_data_on_uninstall=false
package/exclude_from_recents=false
package/show_in_android_tv=false
package/show_in_app_library=true
package/show_as_launcher_app=false
graphics/opengl_debug=false
xr_features/xr_mode=0
screen/immersive_mode=true
screen/support_small=true
screen/support_normal=true
screen/support_large=true
screen/support_xlarge=true
user_data_backup/allow=false
command_line/extra_args=""
apk_expansion/enable=false
apk_expansion/SALT=""
apk_expansion/public_key=""
permissions/custom_permissions=PackedStringArray()
'''

with open("export_presets.cfg", "w", encoding="utf-8") as f:
    f.write(preset)

# 自校验
for i, ln in enumerate(open("export_presets.cfg", encoding="utf-8"), 1):
    if ln.startswith(" "):
        sys.exit("第 %d 行有行首空格: %r" % (i, ln))
text = open("export_presets.cfg", encoding="utf-8").read()
for must in ('[preset.0]', '[preset.0.options]', 'package/unique_name="%s"' % pkg,
             'keystore/debug="%s"' % ks, 'package/signed=true'):
    if must not in text:
        sys.exit("缺少必需项: %s" % must)
print("export_presets.cfg 已生成并通过校验")
print("  package:", pkg)
print("  keystore:", ks)
