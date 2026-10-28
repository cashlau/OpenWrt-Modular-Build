#!/bin/bash
set -euo pipefail
# -------- 内置 Momo 规则集 --------

RULE_DIR="files/etc/momo/rules"
mkdir -p "$RULE_DIR"

while read -r name url; do
    echo "下载 Momo 规则：$name"

    if ! wget -q --tries=3 --timeout=30 -O "$RULE_DIR/$name" "$url"; then
        echo "❌ 规则下载失败：$name"
        exit 1
    fi

    if [ ! -s "$RULE_DIR/$name" ]; then
        echo "❌ 规则文件为空：$name"
        exit 1
    fi
done <<'EOF'
geosite-fakeipfilter.json https://raw.githubusercontent.com/qichiyuhub/rule/main/rules/fakeipfilter.json
geosite-ai.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-ai-!cn.srs
geosite-youtube.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/youtube.srs
geosite-google.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/google.srs
geosite-github.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/github.srs
geosite-onedrive.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/onedrive.srs
geosite-microsoft.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/microsoft.srs
geosite-apple.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/apple.srs
geosite-telegram.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/telegram.srs
geosite-tiktok.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/tiktok.srs
geosite-netflix.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/netflix.srs
geosite-paypal.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/paypal.srs
geosite-steamcn.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/steam@cn.srs
geosite-steam.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/steam.srs
geosite-!cn.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/geolocation-!cn.srs
geosite-cn.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/cn.srs
geoip-google.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geoip/google.srs
geoip-apple.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo-lite/geoip/apple.srs
geoip-telegram.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geoip/telegram.srs
geoip-netflix.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geoip/netflix.srs
geoip-cn.srs https://raw.githubusercontent.com/qljsyph/ruleset-icon/main/sing-box/geoip/China-ASN-combined-ip.srs
geosite-speedtest.srs https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/speedtest.srs
geosite-anti-ad.srs https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblocksingbox.srs
geosite-siri.srs https://raw.githubusercontent.com/cashlau/sing-box-rules/main/rules/siri.srs
EOF

echo "✅ Momo 初始规则已写入固件"

