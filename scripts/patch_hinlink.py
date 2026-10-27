#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_hinlink.py — 将 OpenWrt 官方主线 (openwrt/openwrt PR #21270) 的
HINLINK H66K / H68K 板级支持移植到 ImmortalWrt master 源码树。

背景：
- ImmortalWrt master 尚未同步上游 2026-01 的 hinlink 设备提交；
- 但 master 已使用 kernel 6.18（rk3568-hinlink-*.dts 已进内核主线）
  以及 u-boot 2026.10（已内置 hinlink-h6xk defconfig），
  所以【不需要任何内核补丁和 U-Boot 补丁】，
  只需注入 OpenWrt 侧的设备定义与 base-files 配置。

用法: python3 patch_hinlink.py <openwrt-src-root>

安全策略：所有锚点要求全文恰好命中一次，否则立即报错退出，宁可失败不乱改。
锚点基于 2026-10 抓取的 ImmortalWrt master 文件实测有效；若上游漂移导致
[FATAL]，请把 build 日志发回维护者更新锚点即可（README 有说明）。
"""

import sys
from pathlib import Path

BSL = "\\"      # 单个反斜杠（shell 续行符）
T = "\t"        # tab

def esc_backslash(s):
    """把文本中的 '<BS>' 占位符替换为真正的反斜杠"""
    return s.replace("<BS>", BSL)


class Patcher:
    def __init__(self, root: Path):
        self.root = root
        self.count = 0
        self.warns = 0

    def load(self, rel):
        p = self.root / rel
        if not p.exists():
            raise SystemExit(f"[FATAL] 源码文件不存在: {rel}\n"
                             "        ImmortalWrt 源码结构已变化，请联系维护者更新本脚本。")
        return p.read_text(encoding="utf-8")

    def save(self, rel, content):
        (self.root / rel).write_text(content, encoding="utf-8")

    def replace_once(self, rel, old, new, desc, optional=False):
        content = self.load(rel)
        if old not in content and new.replace(old, "<ALREADY?>") != new:
            pass
        n = content.count(old)
        if n != 1:
            if optional:
                self.warns += 1
                print(f"[WARN] {desc}: 锚点命中 {n} 次（要求 1 次），跳过该步。")
                return False
            raise SystemExit(f"[FATAL] {desc}: 锚点在 {rel} 中命中 {n} 次（要求恰好 1 次），放弃修改。\n"
                             "        ImmortalWrt 上游文件已变化，请联系维护者更新移植脚本。")
        self.save(rel, content.replace(old, new, 1))
        self.count += 1
        print(f"[ OK ] {desc}")
        return True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_hinlink.py <openwrt-src-root>")
    px = Patcher(Path(sys.argv[1]).resolve())

    # =====================================================================
    # 1) target/linux/rockchip/image/armv8.mk —— 设备 image profile
    #    (upstream commit cf84e8ee)
    # =====================================================================
    rel = "target/linux/rockchip/image/armv8.mk"
    c = px.load(rel)
    if "hinlink_h68k" in c:
        print("[SKIP] armv8.mk 已含 hinlink 支持")
    else:
        dev_block = (
            "define Device/hinlink_h6xk\n"
            "  $(Device/rk3568)\n"
            "  DEVICE_VENDOR := HINLINK\n"
            "  DEVICE_PACKAGES := kmod-ata-ahci-dwc kmod-mt7921e kmod-r8169 wpad-basic-mbedtls\n"
            "endef\n\n"
            "define Device/hinlink_h66k\n"
            "  $(Device/hinlink_h6xk)\n"
            "  DEVICE_MODEL := H66K\n"
            "  DEVICE_DTS := rk3568-hinlink-h66k\n"
            "  UBOOT_DEVICE_NAME := hinlink-h66k-rk3568\n"
            "endef\n"
            "TARGET_DEVICES += hinlink_h66k\n\n"
            "define Device/hinlink_h68k\n"
            "  $(Device/hinlink_h6xk)\n"
            "  DEVICE_MODEL := H68K\n"
            "  DEVICE_ALT0_VENDOR := LinkStar\n"
            "  DEVICE_ALT0_MODEL := H68K\n"
            "  DEVICE_DTS := rk3568-hinlink-h68k\n"
            "  UBOOT_DEVICE_NAME := hinlink-h68k-rk3568\n"
            "endef\n"
            "TARGET_DEVICES += hinlink_h68k\n\n"
        )
        anchor = "define Device/linkease_easepi-r1"
        if c.count(anchor) != 1:
            raise SystemExit(f"[FATAL] armv8.mk 锚点 {anchor!r} 命中 {c.count(anchor)} 次，放弃。")
        px.save(rel, c.replace(anchor, dev_block + anchor, 1))
        px.count += 1
        print("[ OK ] armv8.mk: 注入 hinlink_h66k/h68k 设备定义（含 kmod-mt7921e 无线驱动 profile）")

    # =====================================================================
    # 2) board.d/01_leds —— 注意：该文件 case 模式顶格、命令单 tab
    # =====================================================================
    rel = "target/linux/rockchip/armv8/base-files/etc/board.d/01_leds"
    c = px.load(rel)
    if "hinlink,h68k)" in c:
        print("[SKIP] 01_leds 已含 hinlink")
    else:
        anchor = "widora,mangopi-m28k)"
        if c.count(anchor) != 1:
            raise SystemExit("[FATAL] 01_leds 锚点不唯一，放弃。")
        block = (
            "hinlink,h66k)\n"
            f"{T}ucidef_set_led_netdev \"wan\" \"WAN\" \"blue:wan\" \"eth0\"\n"
            ";;\n"
            "hinlink,h68k)\n"
            f"{T}ucidef_set_led_netdev \"wan\" \"WAN\" \"blue:wan\" \"eth1\"\n"
            ";;\n"
        )
        px.save(rel, c.replace(anchor, block + anchor, 1))
        px.count += 1
        print("[ OK ] 01_leds: 注入 H66K/H68K WAN LED 定义")

    # =====================================================================
    # 3) board.d/02_network
    # =====================================================================
    rel = "target/linux/rockchip/armv8/base-files/etc/board.d/02_network"
    c = px.load(rel)
    changed = False

    if "hinlink,h66k" not in c:
        # 3a) H66K(双网口) 加入 'eth1'=LAN,'eth0'=WAN 分组（radxa,rockpi-e 之前）
        old = f"{T}radxa,rockpi-e|{BSL}\n"
        if c.count(old) != 1:
            raise SystemExit("[FATAL] 02_network: rockpi-e 锚点不唯一，放弃。")
        c = c.replace(old, f"{T}hinlink,h66k|{BSL}\n" + old, 1)
        changed = True

        # 3c) MAC 派生：插在 macaddr_generate_from_mmc_cid mmcblk0 组的 linkease 行前
        old = f"{T}linkease,easepi-r1|{BSL}\n{T}lunzn,fastrhino-r66s|{BSL}\n"
        if c.count(old) == 1:
            c = c.replace(old, f"{T}hinlink,h66k|{BSL}\n{T}hinlink,h68k|{BSL}\n" + old, 1)
            changed = True
        else:
            px.warns += 1
            print(f"[WARN] 02_network MAC 分组锚点命中 {c.count(old)} 次，跳过 MAC 派生（MAC 将随机，属可选优化）")

    # 3b) H68K 四网口分组：插在 * ) 通配之前
    if "hinlink,h68k)" not in c:
        old = f"{T}*)\n{T}{T}ucidef_set_interface_lan 'eth0'\n"
        if c.count(old) != 1:
            raise SystemExit("[FATAL] 02_network: 通配组锚点不唯一，放弃。")
        block = (
            f"{T}hinlink,h68k)\n"
            f"{T}{T}ucidef_set_interfaces_lan_wan 'eth0 eth2 eth3' 'eth1'\n"
            f"{T};;\n"
        )
        c = c.replace(old, block + old, 1)
        changed = True

    if changed:
        px.save(rel, c)
        px.count += 1
        print("[ OK ] 02_network: H68K LAN/WAN = eth0/eth2/eth3 -> br-lan, WAN = eth1" )

    # =====================================================================
    # 4) hotplug.d/net/40-net-smp-affinity
    # =====================================================================
    rel = "target/linux/rockchip/armv8/base-files/etc/hotplug.d/net/40-net-smp-affinity"
    c = px.load(rel)
    if "hinlink,h68k)" in c:
        print("[SKIP] 40-net-smp-affinity 已含 hinlink")
    else:
        old = f"linkease,easepi-r1|{BSL}\n" + f"lunzn,fastrhino-r66s|{BSL}\n"
        if c.count(old) != 1:
            raise SystemExit("[FATAL] 40-net-smp-affinity 分组锚点不唯一，放弃。")
        c = c.replace(old, f"hinlink,h66k|{BSL}\n" + old, 1)

        old = "lunzn,fastrhino-r68s)\n"
        if c.count(old) != 1:
            raise SystemExit("[FATAL] 40-net-smp-affinity r68s 锚点不唯一，放弃。")
        block = (
            "hinlink,h68k)\n"
            f"{T}set_interface_core 2 \"eth1\"\n"
            f"{T}set_interface_core 4 \"eth2\"\n"
            f"{T}set_interface_core 8 \"eth3\"\n"
            ";;\n"
        )
        c = c.replace(old, block + old, 1)
        px.save(rel, c)
        px.count += 1
        print("[ OK ] 40-net-smp-affinity: H68K 多核网卡中断亲和")

    # =====================================================================
    # 5) package/boot/uboot-rockchip/Makefile
    #    （u-boot 2026.10 已内置 hinlink defconfig，此处只做注册）
    # =====================================================================
    rel = "package/boot/uboot-rockchip/Makefile"
    c = px.load(rel)
    if "hinlink-h68k-rk3568" in c:
        print("[SKIP] uboot Makefile 已注册 hinlink")
    else:
        ub_def = (
            "define U-Boot/hinlink-h66k-rk3568\n"
            "  $(U-Boot/rk3568/Default)\n"
            "  NAME:=HINLINK H66K\n"
            '  BUILD_DEVICES:= \\\n'
            "    hinlink_h66k\n"
            "endef\n\n"
            "define U-Boot/hinlink-h68k-rk3568\n"
            "  $(U-Boot/rk3568/Default)\n"
            "  NAME:=HINLINK H68K\n"
            '  BUILD_DEVICES:= \\\n'
            "    hinlink_h68k\n"
            "endef\n\n"
        )
        anchor = "define U-Boot/easepi-r1-rk3568"
        if c.count(anchor) != 1:
            raise SystemExit("[FATAL] uboot Makefile define 锚点不唯一，放弃。")
        c = c.replace(anchor, ub_def + anchor, 1)

        anchor = f"  easepi-r1-rk3568 {BSL}\n  fastrhino-r66s-rk3568 {BSL}\n"
        if c.count(anchor) != 1:
            raise SystemExit("[FATAL] uboot Makefile UBOOT_TARGETS 锚点不唯一，放弃。")
        c = c.replace(anchor, anchor + f"  hinlink-h66k-rk3568 {BSL}\n  hinlink-h68k-rk3568 {BSL}\n", 1)
        px.save(rel, c)
        px.count += 1
        print("[ OK ] uboot-rockchip: 注册 hinlink-h66k/h68k 构建目标")

    print(f"\n[DONE] H68K 移植完成：应用修改 {px.count} 处，警告 {px.warns} 条（警告不影响启动）。")


if __name__ == "__main__":
    main()
