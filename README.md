# OpenWrt Modular Build

基于 [cashlau/OpenWrt-Build](https://github.com/cashlau/OpenWrt-Build) 的模块化 x86_64 固件构建仓库。原仓库独立保留，本仓库不会修改它。

## 选择要编译的插件

编辑 [`third-party/plugins.conf`](third-party/plugins.conf)：

```ini
passwall=y
nikki=y
momo=y
mosdns=y
rtp2httpd=y
pushbot=y
usb-printer=y
netspeedtest=y
bluetooth=y
temp-status=y
```

`y` 表示编入固件，`n` 表示关闭。未列出的插件默认关闭，但被启用插件要求的依赖会自动启用。依赖明确设为 `n` 时直接报错，不会偷偷覆盖选择。

默认延续原仓库的插件选择。PassWall、Nikki、Momo 是可选的不同代理管理工具；编入不代表需要同时运行。PassWall 和 Nikki 沿用原来的默认关闭自启设置。

## 目录

```text
third-party/
  plugins.conf                 # 唯一的第三方插件编译开关
  mosdns/plugin.json           # 来源、分支和软件包名称
  momo/plugin.json
  momo/prepare.sh              # 仅在启用 Momo 时下载初始规则
  bluetooth/plugin.json        # 蓝牙插件及配套依赖
  temp-status/plugin.json
  temp-status/source/          # 原仓库的自有温度插件
  proxy-deps/plugin.json       # 自动启用的共享代理依赖源
  ...
scripts/plugins.py             # 统一解析、准备源码、配置、核验
scripts/prepare-toolchain.sh   # 原仓库的 Go 工具链覆盖
config/.config                 # 迁移保留的完整基础配置
config/customize.sh            # 网口、主题、时区等设备设置
```

## 添加新的第三方插件

1. 创建 `third-party/插件名/plugin.json`。
2. 填写来源和真实的软件包名称。
3. 在 `plugins.conf` 中添加 `插件名=y`。

例如，一个仓库只包含一个插件时：

```json
{
  "packages": ["luci-app-example"],
  "sources": [
    {
      "name": "luci-app-example",
      "kind": "clone",
      "url": "https://github.com/OWNER/REPOSITORY.git",
      "ref": "main"
    }
  ],
  "requires": []
}
```

这是格式示例，OWNER、REPOSITORY 和 packages 必须换成实际信息。`packages` 填 OpenWrt 软件包名称，不能只根据 GitHub 仓库名猜测。

- `kind: clone`：源码放进 `package/third-party/`，适合单插件或小型软件包集合。
- `kind: feed`：注册为 OpenWrt feed，适合 PassWall、Nikki 等多软件包源。
- `requires`：本仓库其他插件目录的名称，用于共享依赖。
- `local: source`：使用当前插件文件夹的 `source/`，温度插件采用这种方式。
- `prepare.sh`：可选，启用时在 OpenWrt 源码根目录执行；适合规则下载或补丁。

源码目录和 feed 名称不能重复；插件关闭时不下载其独有源码，不运行其 prepare.sh。关闭插件仍可能保留其他功能共用的依赖库，系统基础软件由 config/.config 管理。

## 第三方插件如何更新

`ref` 为分支名时，每次编译获取该分支最新提交；为空时跟随上游默认分支。标签通常保持在指定版本；填写完整的 40 位提交 SHA 可固定代码。

每周三北京时间／台北时间 08:00 自动重新编译，也可在 Actions 手动运行 **OpenWrt Modular Build**。每次都重新拉取，不再只根据 OpenWrt 主版本号决定是否跳过，因此只有插件更新时也能进入新固件。GitHub 的定时执行可能延迟。

已有路由器不会因此自动升级，需要自行安装新固件。上游修改依赖、软件包名称或构建方式时，可能仍需调整对应插件配置。

## 构建与下载

1. 修改插件开关并保存。
2. 打开 Actions → OpenWrt Modular Build → Run workflow。
3. 构建成功后在 Releases 下载固件。

发布使用仓库自带的 GITHUB_TOKEN，无需配置原仓库的 IGH_TOKEN。每次构建创建独立 Release，避免同一 OpenWrt 版本的插件更新覆盖旧固件。

Release 中的 `build-info.tar.gz` 保存完整编译配置、精简配置、插件开关和实际源码提交，便于排查和回退。精简配置由 OpenWrt 自己生成；迁移阶段保留原始完整配置，避免未经验证地丢失硬件选项。

默认设备设置沿用原仓库：管理地址 `192.168.50.1`，用户名 `root`，初始密码为空；首次登录后设置密码。多网口条件满足时 eth1 为 PPPoE WAN，其他实体 eth 网口为 LAN。保留 Footstrap、Dashboard、温度显示和 MT7925 固件定制。

## 检查与限制

每次推送运行配置验证和自动测试。构建流程在 `make defconfig` 后核验所有受管理插件；启用项消失或关闭项被重新选中都会停止构建。

```sh
python3 scripts/plugins.py list
python3 -m unittest discover -s tests -v
```

脚本测试不等于完整固件编译或硬件测试；首次使用前以 Actions 的实际构建结果为准。跨大版本升级前备份配置并确认兼容性。

来源基线：原仓库提交 `ff64d04988c8a8aecc195972936e706d43185802`。原文件版权及第三方插件许可证归各自作者所有。
