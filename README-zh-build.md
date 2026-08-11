# StrykerOSS 汉化版自动化构建（GitHub Actions）

本仓库内置一套 **一键编译 + 汉化 + JDK 17 签名** 的 GitHub Actions 流水线。
Fork 后配置好 Secrets，点击一个按钮即可拿到 `StrykerOSS-6.0-zh-rCN-signed.apk`。

> ⚠️ 仅限**授权测试**使用。原作者/本仓库对滥用不承担任何责任。

---

## 一、新增的文件

| 文件 | 作用 |
|---|---|
| `.github/workflows/build-localized.yml` | 主流水线：生成汉化资源 → JDK 17 编译 → 签名 → 上传 APK / 发布 Release |
| `scripts/localize_zh.py` | 汉化资源生成器：读取 `res/values`，按词典生成 `res/values-zh-rCN` |
| `scripts/zh_dict.py` | 简体中文翻译词典（**1279 条**，覆盖全部 UI 文案，含占位符保留与校验） |
| `scripts/gen_keystore.sh` | 用 JDK 17 `keytool` 生成签名密钥并输出 Secrets 配置值 |

**不修改任何上游源码**：汉化通过 Android 资源本地化（`values-zh-rCN`）实现，
中文用户自动生效，英文用户不受影响；上游更新后可直接合并，脚本可重复运行。

---

## 二、快速开始（约 3 分钟）

### 1. Fork 并添加 Secrets

```bash
# 本地生成密钥（需要 JDK 17，或任意含 keytool 的 JDK）
bash scripts/gen_keystore.sh stryker-release stryker-release.jks 你的强密码
```

把脚本打印的 4 个值填到仓库
`Settings → Secrets and variables → Actions`（New repository secret）：

| Secret 名 | 值 |
|---|---|
| `STRYKER_KEYSTORE_B64` | base64 编码的 keystore 内容（脚本已打印） |
| `STRYKER_KEYSTORE_PASSWORD` | keystore 密码 |
| `STRYKER_KEY_ALIAS` | 别名（默认 `stryker-release`） |
| `STRYKER_KEY_PASSWORD` | 密钥密码 |

> 不配置 Secrets 也能跑，产物为**未签名 APK**（流水线会打印 warning）。

### 2. 触发构建

- **手动**：`Actions` → `Build localized StrykerOSS (JDK 17)` → `Run workflow`
- **打 tag 自动发布**：`git tag v6.0 && git push origin v6.0`

### 3. 获取 APK

- 构建完成后在 **Actions 运行页底部 Artifacts** 下载
  `StrykerOSS-6.0-zh-rCN-signed.apk`（附 `.sha256` 校验值）
- 打 tag 时自动生成 **GitHub Release**（含 APK 与校验文件）

---

## 三、流水线做了什么

```text
checkout
  └─ setup-java (Temurin JDK 17 + Gradle 缓存)
       └─ sdkmanager: platforms;android-33 / build-tools;34.0.0 / ndk;25.1.8937393 / cmake;3.22.1
            └─ python3 scripts/localize_zh.py --strict     ← 生成 values-zh-rCN（0 回退才继续）
                 └─ 解码 STRYKER_KEYSTORE_B64 → 导出签名环境变量
                      └─ ./gradlew assembleRelease          ← R8 压缩/混淆 + ndk-build
                           └─ apksigner verify --print-certs（有密钥时校验签名）
                                └─ upload-artifact / gh release create
```

- **JDK 17**：与上游官方 CI 一致（AGP 8.2.0 + Gradle 8.5 要求 JDK 17）
- **R8**：release 构建默认 `minifyEnabled true`，产物更小、更难逆向
- **签名**：复用项目自带的 `signingConfigs.release`
  （读 `STRYKER_RELEASE_*` 环境变量），未配置时按官方设计产出未签名 APK

---

## 四、本地构建（可选）

```bash
# 1. 汉化
python3 scripts/localize_zh.py --strict

# 2. 配置签名（或跳过则产出未签名 APK）
export STRYKER_RELEASE_STORE_FILE=/path/to/stryker-release.jks
export STRYKER_RELEASE_STORE_PASSWORD=你的密码
export STRYKER_RELEASE_KEY_ALIAS=stryker-release
export STRYKER_RELEASE_KEY_PASSWORD=你的密码

# 3. 编译（JDK 17）
./gradlew assembleRelease
# 产物: app/build/outputs/apk/release/app-release.apk
```

---

## 五、维护翻译词典

- 词典在 `scripts/zh_dict.py` 的 `TRANSLATIONS`（`name → 中文`）。
- 上游新增字符串后，重跑脚本会打印 `[warn] 未翻译: xxx`；
  补上对应条目即可（`--strict` 模式下缺失会直接失败，适合 CI）。
- 占位符（`%1$s`、`%d`、`\n` 等）必须与英文原文一致，脚本会校验并打印差异。
- `translatable="false"` 的品牌名/URL 条目自动原样保留。

---

## 六、常见问题

| 问题 | 解决 |
|---|---|
| 构建报 NDK 相关错误 | 确认网络可达 `dl.google.com`（NDK 约 600 MB，首次较慢） |
| APK 显示未签名 | 检查 4 个 Secret 是否已配置；`apksigner verify` 步骤会打印证书 |
| 想改包名/版本号 | 编辑 `app/build.gradle` 的 `applicationId` / `versionName` |
| 密钥丢了 | 无法更换（Android 签名不可变），务必备份 `stryker-release.jks` |
| 上游更新想重新汉化 | `git pull` 后重新触发 workflow 即可，词典会自动补齐未覆盖项 |

---

*StrykerOSS 上游：https://github.com/zalexdev/strykerapp （GPL-3.0）*
