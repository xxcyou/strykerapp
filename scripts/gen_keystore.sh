#!/usr/bin/env bash
# ============================================================================
# gen_keystore.sh — 用 JDK 17 keytool 生成 release 签名密钥，并输出
# GitHub Actions Secrets 所需的 base64 值。
#
# 用法:
#   bash scripts/gen_keystore.sh [别名] [keystore文件] [密码]
#
# 示例:
#   bash scripts/gen_keystore.sh stryker-release stryker-release.jks ChangeMe123!
#
# 生成后把打印出的 4 个值配置到仓库 Secrets:
#   STRYKER_KEYSTORE_B64 / STRYKER_KEYSTORE_PASSWORD /
#   STRYKER_KEY_ALIAS / STRYKER_KEY_PASSWORD
# ============================================================================
set -euo pipefail

ALIAS="${1:-stryker-release}"
KEYSTORE="${2:-stryker-release.jks}"
PASSWORD="${3:-$(openssl rand -hex 12)}"
DNAME="CN=StrykerOSS Localized Build, OU=CI, O=StrykerOSS, L=Internet, ST=Internet, C=CN"
VALIDITY_DAYS=10000

JAVA_HOME_JDK17="${JAVA_HOME_JDK17:-}"
KEYTOOL="keytool"
if [ -n "$JAVA_HOME_JDK17" ]; then
    KEYTOOL="$JAVA_HOME_JDK17/bin/keytool"
fi

echo "==> 使用: $("$KEYTOOL" -help 2>&1 | head -1 || true)"
"$KEYTOOL" -genkeypair -v \
    -keystore "$KEYSTORE" \
    -alias "$ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity "$VALIDITY_DAYS" \
    -storepass "$PASSWORD" \
    -keypass "$PASSWORD" \
    -dname "$DNAME" || { echo "[!] keytool 失败，请确认已安装 JDK 17 并设置 JAVA_HOME"; exit 1; }

echo
echo "=================================================================="
echo " 1) 把以下 4 个值配置到 GitHub Secrets:"
echo "    STRYKER_KEYSTORE_B64      = $(base64 -w0 "$KEYSTORE")"
echo "    STRYKER_KEYSTORE_PASSWORD = $PASSWORD"
echo "    STRYKER_KEY_ALIAS         = $ALIAS"
echo "    STRYKER_KEY_PASSWORD      = $PASSWORD"
echo "=================================================================="
echo
echo " 2) 本地构建并签名（可选）:"
echo "    export STRYKER_RELEASE_STORE_FILE=\"$(pwd)/$KEYSTORE\""
echo "    export STRYKER_RELEASE_STORE_PASSWORD=\"$PASSWORD\""
echo "    export STRYKER_RELEASE_KEY_ALIAS=\"$ALIAS\""
echo "    export STRYKER_RELEASE_KEY_PASSWORD=\"$PASSWORD\""
echo "    ./gradlew assembleRelease"
echo
echo " 3) 密钥泄露后无法更换（Android 应用签名不可变），请妥善保管 $KEYSTORE"
