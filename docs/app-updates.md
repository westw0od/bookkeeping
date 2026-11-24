# Android 应用内更新

当前交付 2.4.2 恢复版（versionCode 10），界面及功能与 2.4.1 相同。2.5.0 已撤回，新增的模型预设及修改模型入口已移除；不回退数据库，不更改已保存的账号、账单或密钥配置。

Android 按内部 versionCode 判断更新，因此恢复包使用 10，能够直接覆盖 2.5.0（9）或 2.4.1（8），无需卸载。保留原签名和应用 ID，恢复包的显示版本号为 2.4.2。2.5.0 的 GitHub 发布、标签和服务器公开安装包已撤下，Git 历史通过撤销提交记录此操作。

App 启动时自动检查，账号页也提供「检查更新」。从 2.4.1 起支持此流程，更早版本需手动覆盖安装一次。网页刷新即可载入最新界面。

## 用户流程

发现新版本后显示更新说明和包大小，用户可选择稍后。点击立即更新才开始下载，可取消、失败后重试。下载完成检查 SHA256、实际包名、版本号、Android 兼容性和当前安装包签名，再打开系统安装器。首次可能需要在系统设置中允许此应用安装更新，返回后点击继续安装。

覆盖安装保留 Preferences、localStorage 和服务器账单。更新代码不清除会话、草稿或账本。用户清除应用数据、卸载或系统清理缓存不在此保证范围内。

APK 只从当前配置的 HTTPS 服务器获取，不接受重定向、跨站下载地址或前端传入的本地文件路径。下载不携带账号令牌。原生缓存目录只保留一个更新包，临时下载失败会清理。不进行静默安装，不提供后台推送或网页资源热更新。

## 服务器发布格式

- `GET /api/app/releases/latest`：公开版本信息，禁止缓存，不访问用户数据库。
- `GET /downloads/android/{version_code}/{sha256}.apk`：与版本和哈希绑定的不可变安装包。
- `GET /downloads/bookkeeping.apk`：兼容之前的公开下载链接，返回当前最新版。

文件位于 `artifacts/android/releases/{version_code}/manifest.json` 和 `app.apk`；`artifacts/android/latest.json` 是唯一可变的最新版指针。

每次发布递增 `frontend/android/app/build.gradle` 的 versionCode 和 versionName，保留同一签名密钥。当前延续此前自用 APK 的签名，签名密钥需妥善备份，不能在后续构建时换成另一台机器自动生成的调试密钥，否则无法覆盖更新。

```powershell
./scripts/build-apk.ps1 -ServerUrl 'https://39.107.13.249'
# 使用 Android SDK 的 apksigner 验证新 APK，并核对与当前版本的签名一致。
.venv/Scripts/python.exe scripts/prepare-android-release.py --note '本次更新的具体说明'
```

准备脚本从 Gradle 输出元数据提取版本，生成哈希、大小及更新说明，拒绝覆写已准备的版本。同一版本不可替换 APK，修订时需递增版本号。

将该版本的 `app.apk` 和 `manifest.json` 通过 SSH 上传到服务器的私有暂存目录，再执行：

```bash
/opt/bookkeeping/.venv/bin/python /opt/bookkeeping/scripts/publish-android-release.py /root/此次上传目录
```

发布脚本校验文件后先创建不可变的版本目录，再原子替换最新版指针；拒绝降级或改写已发布版本。上传未完成、文件损坏或元数据不一致时，不改变现有版本。旧版下载链接仍可使用，避免发布过程中打断已开始的更新。保持旧版本目录直到不再需要回退及旧链接。

## 验证

更新模块和 AI 网络错误的独立后端测试位于 `backend/unit_tests`，无需启动本地 MySQL。浏览器使用原生桥模拟测试下载、权限及安装流程；原生 `UpdatePolicyTest` 检查 HTTPS 来源约束、元数据边界及损坏检测。实际 APK 安装还需 Android 设备测试。

云服务器无法直接连接学校 AI 的问题与应用更新独立。连接失败现在返回明确错误并尽快结束等待。仅在用户电脑或手机上连接校园 VPN，不会自动让云服务器接入校园网络。
