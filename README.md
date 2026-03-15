# 微信转账金额识别

自动识别微信转账截图中的金额（¥ 符号开头的数字）。

## 功能

- 批量识别多张图片
- 自动汇总计算总金额
- 只识别 ¥ 符号开头的转账金额

## 本地运行

```bash
pip install -r requirements.txt
python flet_app.py
```

## 打包 APK

项目使用 GitHub Actions 自动打包。

1. Fork 或 Clone 此仓库
2. 推送代码到 GitHub
3. GitHub Actions 自动构建 APK
4. 在 Actions → Artifacts 中下载 APK