# 独立云服务器运行说明

服务器为 Ubuntu 24.04，公网入口 `https://39.107.13.249`，安装包入口 `/downloads/bookkeeping.apk`。此部署不使用学校服务器或本机内网穿透，本机可以关机。

## 服务与目录

- 项目：`/opt/bookkeeping`；Python 环境：`/opt/bookkeeping/.venv`。
- 后端：`bookkeeping.service`，以无登录权限的 `bookkeeping` 用户运行，监听 `127.0.0.1:8000`。
- Nginx：公网 80/443；80 仅提供 ACME 验证及 HTTPS 跳转。
- MySQL：仅监听 `127.0.0.1:3306`，独立应用账号只拥有 `bookkeeping` 数据库权限。
- 配置：`/opt/bookkeeping/backend/.env`，root 所有、应用组可读。保留原有 `KEY_ENCRYPTION_SECRET`，否则无法解密已保存的 AI Key。
- 附件：`/opt/bookkeeping/backend/uploads`。客户端草稿仍保存在各设备的本地存储中，不属于服务器数据库。
- UFW 放行 SSH、80、443；数据库及后端端口不向公网开放。

```bash
systemctl status bookkeeping nginx mysql
systemctl restart bookkeeping
curl --fail http://127.0.0.1:8000/api/health
journalctl -u bookkeeping -n 50 --no-pager
systemctl list-timers 'bookkeeping-*'
```

应用、MySQL、Nginx 均开机自启。应用异常退出后由 systemd 自动重启。应用执行迁移后启动，不在公网以 root 运行。

## 证书

使用 Let's Encrypt 的 `shortlived` IP 证书，覆盖 `39.107.13.249`，有效期约六天。Certbot 安装在 `/opt/certbot`，证书位于 `/etc/letsencrypt/live/bookkeeping-ip/`。

`bookkeeping-certbot.timer` 每六小时检查续期，续期成功后通过 deploy hook 验证并重载 Nginx。公网 80 端口和服务器访问 ACME 服务的出站网络必须保持可用。

```bash
systemctl status bookkeeping-certbot.timer
/opt/certbot/bin/certbot certificates
/opt/certbot/bin/certbot renew --dry-run --run-deploy-hooks --max-log-backups 3 --no-random-sleep-on-renew
journalctl -u bookkeeping-certbot -n 30 --no-pager
```

参考：[Let's Encrypt 的 Certbot/IP 证书说明](https://letsencrypt.org/2026/03/11/shorter-certs-certbot/)。

## 日志与备份

应用日志位于 `/opt/bookkeeping/.local/logs/`；app/access 每类 5 MiB × 5 份，已轮转文件超过 14 天清理。访问日志省略查询参数，不记录请求正文、密码和认证头。

Nginx/MySQL 使用 logrotate：每天轮转、每小时检查 5 MiB 阈值、保留四个归档并压缩，最长 14 天。大小阈值按小时检查，检查间隔内可能暂时超过。MySQL general/slow/binlog 关闭；系统 journal 总额限制 100 MiB、运行时 30 MiB、最长 14 天。Certbot 保留三份历史日志。

`bookkeeping-backup.timer` 每天 03:15 后十分钟内备份数据库、加密配置和附件，保留七天。手动执行 `systemctl start bookkeeping-backup`。备份放在 root 专用的 `/var/backups/bookkeeping/`，不得公开下载；加密配置和数据库需要成套保留。当前备份与应用在同一服务器，不能抵御整机丢失。

## APK 与 AI

当前交付 2.4.1 APK 默认连接新公网入口，与此前版本签名相同，可覆盖安装，并加入[应用内更新](app-updates.md)。旧版可在登录页「服务器设置」保存新 HTTPS 地址；如曾手动设置过旧地址，升级后保存的地址仍优先于安装包默认值。

构建命令：

```powershell
./scripts/build-apk.ps1 -ServerUrl 'https://39.107.13.249'
```

SDU 的 `xplt.sdu.edu.cn:4000` 需要校园网或校园 VPN，校园网本机可连，云服务器直连超时；目前没有建立电脑中转。云服务器可以访问 DeepSeek 公网接口。使用 SDU Key 仍需获得可用的校内访问路径；也可在应用中添加支持的公网提供商 Key 并设为默认，不应将 SDU Key 填给其他提供商。

已将不含秘密的 Nginx、systemd、MySQL、日志轮转及备份脚本导出到 [deploy/ubuntu](../deploy/ubuntu/README.md)。数据库、`.env`、证书私钥、用户上传内容和 APK 签名密钥均不进入 Git。
