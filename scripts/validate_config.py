#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 make defconfig 后的 .config：核心功能必须全部命中，缺一即中止构建，
   产出一个"看似成功但缺功能"的固件。"""

import sys
from pathlib import Path

CFG = Path(".config").read_text(encoding="utf-8", errors="ignore")

REQUIRED = [
    ("CONFIG_TARGET_DEVICE_rockchip_armv8_DEVICE_hinlink_h68k=y", "H68K 设备支持（patch 未生效？）"),
    ("CONFIG_PACKAGE_luci=y",                               "LuCI 界面"),
    ("CONFIG_PACKAGE_luci-app-openclash=y",                 "OpenClash"),
    ("CONFIG_PACKAGE_tailscale=y",                          "Tailscale 守护进程"),
    ("CONFIG_PACKAGE_samba4-server=y",                      "SMB 共享 (samba4)"),
    ("CONFIG_PACKAGE_luci-app-samba4=y",                    "SMB LuCI 界面"),
    ("CONFIG_PACKAGE_luci-app-filemanager=y",               "文件管理器"),
    ("CONFIG_PACKAGE_luci-app-store=y",                     "iStore 应用商店"),
    ("CONFIG_PACKAGE_luci-app-lucky=y",                     "Lucky"),
    ("CONFIG_PACKAGE_cups=y",                               "CUPS 打印服务"),
    ("CONFIG_PACKAGE_kmod-usb-printer=y",                   "USB 打印机驱动"),
    ("CONFIG_PACKAGE_kmod-mt7921e=y",                       "MT7921 无线驱动"),
    ("CONFIG_PACKAGE_wpad-basic-mbedtls=y",                 "WiFi AP 模式 (wpad)"),
    ("CONFIG_PACKAGE_block-mount=y",                        "磁盘挂载(文件管理依赖)"),
]

OPTIONAL = [
    ("CONFIG_PACKAGE_luci-i18n-base-zh-cn=y",        "LuCI 中文语言包"),
    ("CONFIG_PACKAGE_luci-app-tailscale-community=y","Tailscale LuCI 界面"),
    ("CONFIG_PACKAGE_luci-i18n-samba4-zh-cn=y",       "samba4 中文包"),
    ("CONFIG_PACKAGE_luci-i18n-filemanager-zh-cn=y",  "filemanager 中文包"),
    ("CONFIG_PACKAGE_dnsmasq_full=y",                "dnsmasq-full(OpenClash 推荐)"),
    ("CONFIG_PACKAGE_avahi-daemon=y",                "Avahi 网络打印机发现"),
    ("CONFIG_PACKAGE_cups-filters=y",                "CUPS 滤镜"),
    ("CONFIG_PACKAGE_kmod-usb-storage=y",            "USB 存储"),
    ("CONFIG_PACKAGE_kmod-fs-exfat=y",               "exFAT 文件系统"),
    ("CONFIG_PACKAGE_ntfs-3g=y",                     "NTFS 支持"),
    ("CONFIG_PACKAGE_luci-app-upnp=y",               "UPnP"),
]

missing = [c for c, _ in REQUIRED if c not in CFG]

print("=" * 62)
print("必需功能检查：")
for c, name in REQUIRED:
    print(f"  [{'x' if c in CFG else ' '}] {name:28s} {c}")
print("\n可选功能检查（缺失不阻断构建）：")
for c, name in OPTIONAL:
    print(f"  [{'x' if c in CFG else ' '}] {name:28s} {c}")
print("=" * 62)

if missing:
    print(f"\n[FATAL] 以下必需项未被选中（共 {len(missing)} 项）：")
    for c, name in missing:
        print(f"  - {name}: {c}")
    print("\n可能原因：")
    print(" 1) 对应 feeds 拉取失败（网络/上游仓库改名）；")
    print(" 2) patch_hinlink.py 步骤异常；")
    print(" 3) 包名在 ImmortalWrt master 中发生变化（README 有排查说明）。")
    sys.exit(1)

print("\n[OK] 全部必需功能已进入固件配置，开始编译。")
