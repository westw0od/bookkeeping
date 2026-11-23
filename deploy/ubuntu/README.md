# Ubuntu 生产配置快照

`files/` 保存本次 2.4.1 部署从服务器核对导出的配置，目录结构与服务器绝对路径对应。例如 `files/etc/systemd/system/bookkeeping.service` 对应 `/etc/systemd/system/bookkeeping.service`。

包括：应用服务、MySQL/Nginx 异常重启设置、每日备份、证书续期、日志轮转定时器、仅回环监听的 MySQL 配置和 Nginx HTTPS 入口。

此目录不包含数据库、账号密码、`.env`、Fernet 加密秘密、证书私钥、API Key 或 Android 签名私钥。恢复实例时必须从受保护的备份恢复 `.env` 和数据，否则保存的 AI Key 无法解密。

这些是当前部署的配置快照，不是自动安装器。请先完成[云服务器部署](../../docs/cloud-deployment.md)所述的依赖、应用目录、专用运行用户和数据库初始化，再按路径安装。迁移到不同 IP 或路径时，需要同步修改 Nginx、证书以及服务文件中的路径。

安装脚本后必须保留执行权限：

```bash
chmod 700 /usr/local/sbin/bookkeeping-backup
chmod 750 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
nginx -t
systemctl daemon-reload
```

现有服务器不需要重新运行安装步骤。运维、证书续期、日志大小和备份保留规则见[运行说明](../../docs/cloud-deployment.md)，后续 APK 发布见[应用更新说明](../../docs/app-updates.md)。
