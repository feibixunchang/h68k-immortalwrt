# H68K (F版 WiFi) · ImmortalWrt 定制固件云编译仓库

针对 **Hinlink H68K / LinkStar H68K（F 版，RK3568 · 4 网口 · MT7921 WiFi）** 的
ImmortalWrt 固件 GitHub Actions 云编译工程。编译出的固件**出厂自带**：

| 功能 | 包名 | 来源 |
|---|---|---|
| Tailscale 组网 | `tailscale` + LuCI 界面 | ImmortalWrt 官方源 |
| Lucky（DDNS/反代/端口转发） | `luci-app-lucky` | sirpdboy/luci-app-lucky |
| Samba 文件共享 (SMB) | `samba4-server` + LuCI 界面 | ImmortalWrt 官方源 |
| 文件管理器 | `luci-app-filemanager` | ImmortalWrt 官方源 |
| OpenClash | `luci-app-openclash` | ImmortalWrt 官方源 |
| CUPS 打印服务（USB/网络打印机） | `cups` + `cups-filters` + `kmod-usb-printer` | ImmortalWrt 官方源 |
| iStore 应用商店（iStoreOS 同款） | `luci-app-store` | linkease/istore |
| MT7921 WiFi (AP 模式) | `kmod-mt7921e` + `wpad-basic-mbedtls` | 设备 profile 默认 |

## 为什么要"移植"？

OpenWrt 官方主线已于 **2026-01 正式合并 H66K/H68K 支持**（PR #21270），
ImmortalWrt 也已用上原生支持 hinlink 设备的 kernel 6.18 与 u-boot 2026.10，
但其 master 分支**尚未同步板级定义那几个提交**。
本仓库的 `scripts/patch_hinlink.py` 会在编译前把上游的设备支持精准移植到
ImmortalWrt 源码树（纯注册层移植，不需要任何内核补丁）：

- `armv8.mk`：`hinlink_h66k / hinlink_h68k` 设备 profile（含 MT7921 驱动）
- `01_leds / 02_network / 40-net-smp-affinity`：LED、WAN=eth1、LAN=eth0+eth2+eth3、多核中断亲和
- `uboot-rockchip Makefile`：注册 `hinlink-h6xk-rk3568` 构建目标

所有修改都带唯一锚点校验，宁可报错也不会把源码改坏。

---

## 使用说明（约 30 分钟动手 + 1.5~3 小时等待）

### 1. 建仓库并推送本目录
1. 注册/登录 [github.com](https://github.com)，新建一个**空仓库**（不要勾选初始化 README），例如 `h68k-immortalwrt`
2. 把**本文件夹的全部内容**（含看不见的 `.github` 和 `.gitignore`）推上去。推荐在你电脑上执行：
   ```powershell
   cd "本文件夹路径"
   git init .
   git add .
   git commit -m "H68K ImmortalWrt 定制构建"
   git remote add origin https://github.com/<你的用户名>/h68k-immortalwrt.git
   git push -u origin master
   ```
   （没装 Git 也可以在网页上拖拽上传 zip 后解压，注意 `.github` 目录层级必须在仓库根部）

### 2. 启动云编译（手动触发）
1. 打开你仓库的 **Actions** 页，若首次使用可能提示工作流被暂停 → 点 **I understand my workflows, go ahead and run them**
2. 选择左侧 **Build ImmortalWrt for HINLINK H68K** → **Run workflow** → 参数默认即可：
   - `iw_branch`：默认 `master`（跟随 ImmortalWrt 最新主线）
   - `upload_packages`：默认关；如需给固件离线装依赖再打开
3. 等待 1.5~3 小时，绿色 ✔ 后在运行页面最底部 **Artifacts** 下载
   `immortalwrt-h68k-runN.zip`，解压得到两个镜像：
   - `immortalwrt-*-rockchip-armv8-hinlink_h68k-squashfs-sysupgrade.img.gz` ← **建议先用这个刷 TF 卡**
   - `immortalwrt-*-rockchip-armv8-hinlink_h68k-ext4-sysupgrade.img.gz` ← 正式写入 eMMC 用（可在线升级）

### 3. 刷入 H68K（两阶段，稳妥路线）

> ⚠️ 刷机有风险。全程**不要断电**；写 eMMC 会清掉原厂系统，请务必先完成第 1 步的 TF 卡验证。

**第 1 步 · TF 卡启动（不破坏原系统）**
1. 准备一张 8~32GB 品质可靠的 microSD（闪迪/三星等）
2. [balenaEtcher](https://etcher.balena.io/) 选择 `.img.gz` 直接写入 TF 卡
3. H68K **断电**，插 TF 卡，DC 供电开机；指示灯快速闪烁为正常启动（首次启动可能需要 2~5 分钟）
4. 电脑网线接机身后部网口，访问 `http://192.168.1.1`，用户 `root`、**密码为空**
5. 逐项验证：WiFi 开关（MT7921 AP）、四个网口、SMB、OpenClash、Tailscale、Lucky、iStore、CUPS(:631) —— 见下方"插件速用"

**第 2 步 · 写入 eMMC（确认 TF 版一切正常后）**
1. TF 版系统里 SSH/终端执行 `lsblk` 确认设备对应关系：
   **TF 卡自身通常是 mmcblk1，板载 eMMC 是 mmcblk0**——写错设备就全白干了，请看清容量再动手
2. 执行：
   ```sh
   # 将 ext4-sysupgrade 镜像传到路由器 /tmp（scp、U 盘或 LuCI 文件管理器上传均可）
   wget -O /tmp/h68k.img.gz <镜像的局域网下载地址>
   gunzip /tmp/h68k.img.gz
   # ⚠️ 确认 mmcblk0 是 eMMC（容量约 29~32GB）后：
   dd if=/tmp/h68k.img of=/dev/mmcblk0 bs=4M conv=fdatasync
   sync && reboot
   ```
3. 关机**拔掉 TF 卡**再开机，即从 eMMC 启动 ImmortalWrt

## 网口与默认配置
- ImmortalWrt 官方 profile 定义：**WAN = ETH1**，**LAN = ETH0 + ETH2 + ETH3**（2×2.5G + 1×1G 归 LAN）
- 管理地址 `http://192.168.1.1`，`root` / 空密码；建议首次登录后先设置密码

## 插件速用
| 插件 | 菜单位置 | 首用要点 |
|---|---|---|
| Tailscale | 服务 → Tailscale | 启用后点界面里的链接授权登录 |
| Lucky | 服务 → Lucky | 后台 `http://192.168.1.1:16601`，做 DDNS/反代/端口转发 |
| OpenClash | 服务 → OpenClash | 首次需下载内核（国内源）；建议"覆盖防火墙"开启 |
| Samba | 网络存储 → Samba 网络共享 | 添加共享目录（配合文件管理器/USB 硬盘）|
| 文件管理器 | 系统 → 文件管理器 | 浏览/上传/下载/挂载磁盘 |
| CUPS 打印 | 网页 `http://192.168.1.1:631` | 添加 USB/网络打印机后，电脑端填 `http://192.168.1.1:631/printers/队列名`；Avahi 已内置支持网络发现 |
| iStore 商店 | 服务 → iStore | 像手机应用商店一样再装 n 个插件（arm64 支持 x86_64/arm64 库） |
| WiFi | 网络 → 无线 | MT7921 双频，默认 2.4G `ImmortalWrt` 开放，建议自行设密码/改 5G |

## 想定制插件增减？
直接编辑 `config/hinlink_h68k.config`（每行一个 `CONFIG_PACKAGE_xxx=y`），
改完推送再触发一次 workflow 即可。插件包名可在
[ImmortalWrt 软件包索引](https://downloads.immortalwrt.org/releases/packages/aarch64_generic/luci/) 检索，
不确定的把需求发给 Loomy 帮你改。

## 编译失败怎么办（按失败步骤对号入座）
1. **"移植 H68K" 步骤报 `[FATAL] 锚点命中 n 次`**
   → ImmortalWrt 上游把相关文件改了。把日志整段发回给我（Loomy），我来更新 `patch_hinlink.py` 锚点。
2. **"部署定制配置" 步骤 validate `[FATAL]`**
   → 某个第三方 feed 改名/断链（lucky、istore、openclash 最常见）。同样是发日志给我改 seed/源。
3. **编译本体失败**
   → 日志末尾会贴出 150 行错误。个别插件挂了可以把对应 `CONFIG_PACKAGE_xxx=y` 删掉重试；整体网络抖动重跑一次往往就好。
4. **Actions 提示配额/排队**
   → 免费版 GitHub Actions 每月 2000 分钟足够编译 10+ 次；重跑请点 Re-run job。

## 目录结构
```
.github/workflows/build.yml      # 云编译流水线
config/hinlink_h68k.config       # 固件 seed 配置（插件增减处）
scripts/patch_hinlink.py         # H68K 支持 → ImmortalWrt 移植脚本（锚点自校验）
scripts/validate_config.py       # 编译前功能完整性校验
```

> 本仓库生成物基于 ImmortalWrt master（GPLv2 上游代码汇编），
> H68K 板级支持版权归 OpenWrt 上游（Chukun Pan, PR openwrt/openwrt#21270）。
