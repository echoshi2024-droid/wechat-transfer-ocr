# 飞书机器人部署指南

## 1. 创建飞书机器人应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 记录 **App ID** 和 **App Secret**

## 2. 配置机器人能力

在应用后台开启以下能力：

### 权限配置
- `im:message` - 获取与发送消息
- `im:message:send_as_bot` - 以应用身份发消息
- `im:chat:read` - 读取群聊消息
- `im:chat.members:read` - 读取群成员列表

### 事件订阅
- 接收消息：`im.message.receive_v1`

## 3. 配置回调地址

需要一台公网可访问的服务器，或使用内网穿透工具：

### 方案 A：内网穿透（推荐开发使用）
```bash
# 使用 ngrok 或 cloudflare tunnel
ngrok http 8080
# 将生成的 https://xxx.ngrok.io/webhook 填入飞书后台
```

### 方案 B：云服务器
- 在云服务器上运行机器人
- 开放 8080 端口
- 填入 `http://your-server:8080/webhook`

## 4. 启动机器人

```bash
cd ~/.openclaw/workspace/wechat_transfer_ocr

# 设置环境变量
$env:FEISHU_APP_ID="your_app_id"
$env:FEISHU_APP_SECRET="your_app_secret"
$env:FEISHU_VERIFICATION_TOKEN="your_token"  # 可选

# 启动
.\.venv\Scripts\python.exe feishu_bot.py
```

## 5. 使用方法

1. 在飞书手机 App 中搜索你的机器人
2. 发送微信转账截图
3. 机器人自动识别金额并返回结果

## 架构图

```
┌─────────────┐    发送图片     ┌─────────────┐
│  飞书手机端  │ ──────────────► │  飞书服务器  │
└─────────────┘                 └──────┬──────┘
                                       │ Webhook
                                       ▼
                                ┌─────────────┐
                                │  本地服务器  │
                                │  (OCR 识别) │
                                └──────┬──────┘
                                       │
                                       ▼
                                ┌─────────────┐
                                │  返回结果   │
                                └─────────────┘
```