# 公共索引 · 全部文档

> 本文件是跨会话的知识入口。新增文档请在此追加一行。

## 逆向 / 安全

| 文档 | 位置 | 要点 |
|---|---|---|
| 安卓 APK 逆向改版实战 · 踩坑记录 | `workspace/siege/APK逆向改版-踩坑记录.md` | dex 三套元数据（checksum/uleb前缀/string_ids排序）· tinyxml 按属性名取值 · nop 优于改字符串 · zipalign 消 data descriptor · 最小改动验证法 |

## 游戏 / 引擎

| 文档 | 位置 | 要点 |
|---|---|---|
| **Godot Android CI 编译踩坑** | `workspace/inbox/Godot-Android-CI编译踩坑.md` | **7 个坑** · 最关键：`import_etc2_astc=true` 否则导出失败且**报错为空** · `class_name`→`preload` · heredoc 缩进毁 `.tres` · 本地 qemu 验语法/CI 验导出 · 完整 CI 骨架 |
| dsh-ui 之外的 Godot 资料 | — | 暂缺 |

## 工具 / 环境

| 文档 | 位置 | 要点 |
|---|---|---|
| GitHub 设备码登录 | `workspace/inbox/GitHub-设备码登录.md` | 纯 shell 环境手机授权拿写权限 token · client_id `178c6fc778ccc68e1d6a` · scope `repo workflow` · 15 分钟有效 |
| 一键脚本 | `workspace/inbox/gh_login.py` | `python3 gh_login.py` 授权并保存；`--status` 查有效性；已内置网络重试 |
| 已授权凭据 | `workspace/inbox/.gh_token` | `gho_` token，scope `repo,workflow`，权限 600。**下次直接用，不必重新授权** |

## 项目

| 文档 | 位置 | 要点 |
|---|---|---|
| 堡垒塔防（Godot 重制） | `workspace/siege-td/` | Godot 4.3 · 1280×720 · 4塔/5兵种/3技能 · 双架构 APK · 仓库 `mafucai/siege-td` |
| 成品 | `workspace/siege-td/out/堡垒塔防.apk` | 45.5MB · `com.mafucai.fortresstd` · arm64+v7a · debug 签名 |

---

## 快速用法（GitHub 授权）

现有 token 仍有效时，**无需重新授权**：

```bash
# 查状态
python3 /root/workspace/inbox/gh_login.py --status

# 直接用
TOK=$(cat /root/workspace/inbox/.gh_token)
git remote set-url origin https://x-access-token:$TOK@github.com/OWNER/REPO.git
git push origin HEAD:refs/heads/BRANCH
```

token 失效时才需要跑完整授权：

```bash
python3 /root/workspace/inbox/gh_login.py
# 手机打开 https://github.com/login/device 输入码，自动覆盖旧 token
```
