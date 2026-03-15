# Flet 应用打包指南

## 打包要求

| 平台 | 打包环境 | 必需工具 |
|------|---------|---------|
| Android APK | Windows/Mac/Linux | Flutter SDK, Android SDK |
| iOS App | Mac only | Flutter SDK, Xcode |

---

## 方法一：使用 Flet 官方打包服务（推荐）

Flet 提供云端打包服务，无需本地配置：

```powershell
# 安装 flet
pip install flet

# 打包 Android
flet build apk

# 打包 iOS（需要 Mac）
flet build ipa
```

---

## 方法二：本地打包

### 1. 安装 Flutter SDK

下载地址：https://docs.flutter.dev/get-started/install

### 2. 验证安装

```powershell
flutter doctor
```

### 3. 打包命令

```powershell
cd C:\Users\Michael\.openclaw\workspace\wechat_transfer_ocr

# 打包 Android APK
flet build apk

# 打包 iOS（仅 Mac）
flet build ipa
```

---

## 注意事项

### Android 打包

1. 需要 Java JDK 11+
2. 需要 Android SDK（通过 Android Studio 安装）
3. 打包后的 APK 在 `build/` 目录

### iOS 打包

1. **必须在 Mac 上进行**
2. 需要 Xcode 14+
3. 需要 Apple 开发者账号（发布到 App Store）

---

## 当前限制

由于 OCR 引擎（PaddleOCR）体积较大：
- APK 约 100-200 MB
- 需要较长的打包时间

---

## 替代方案

如果打包困难，可以考虑：

### 1. PWA 网页应用
将应用部署到服务器，手机浏览器访问后可"添加到主屏幕"

### 2. 飞书机器人（已实现）
通过飞书发送图片，自动识别金额

### 3. 网页版（已实现）
http://localhost:7860