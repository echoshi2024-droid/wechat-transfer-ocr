#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信转账金额识别 - 飞书机器人版
用户在飞书上发送图片，机器人自动识别转账金额并返回结果
"""

import os
import re
import json
import hashlib
import tempfile
import requests
import sys
from typing import List, Tuple, Optional
from flask import Flask, request, jsonify

# 强制刷新输出
def log(msg):
    print(msg, flush=True)

# 飞书配置 - 从环境变量读取
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
FEISHU_ENCRYPT_KEY = os.environ.get("FEISHU_ENCRYPT_KEY", "")

# 全局变量
tenant_access_token = None
ocr_engine = None

app = Flask(__name__)


def get_tenant_access_token() -> str:
    """获取飞书 tenant_access_token"""
    global tenant_access_token
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    resp = requests.post(url, headers=headers, json=data)
    result = resp.json()
    
    if result.get("code") == 0:
        tenant_access_token = result.get("tenant_access_token")
        return tenant_access_token
    else:
        raise Exception(f"获取 token 失败: {result}")


def download_image(file_key: str) -> str:
    """下载飞书图片到本地临时文件"""
    global tenant_access_token
    
    if not tenant_access_token:
        get_tenant_access_token()
    
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{file_key}/resources"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}"
    }
    
    resp = requests.get(url, headers=headers)
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(resp.content)
        return f.name


def get_ocr():
    """初始化 OCR 引擎"""
    global ocr_engine
    if ocr_engine is None:
        from paddleocr import PaddleOCR
        log("正在初始化 OCR 引擎...")
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        log("OCR 引擎初始化完成 ✓")
    return ocr_engine


def extract_amounts(text: str) -> List[Tuple[float, str]]:
    """从文本中提取所有带 ¥ 符号的金额"""
    results = []
    pattern = r'[¥￥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'
    
    matches = re.finditer(pattern, text, re.IGNORECASE)
    for match in matches:
        amount_str = match.group(1).replace(',', '')
        try:
            amount = float(amount_str)
            if 0.01 <= amount <= 100000:
                results.append((amount, match.group(0)))
        except ValueError:
            continue
    
    # 去重
    seen = {}
    for amount, source in results:
        if amount not in seen:
            seen[amount] = (amount, source)
    
    return list(seen.values())


def recognize_image(image_path: str) -> Tuple[List[float], float]:
    """识别图片中的转账金额"""
    ocr = get_ocr()
    result = ocr.ocr(image_path, cls=True)
    
    if not result or not result[0]:
        return [], 0.0
    
    all_amounts = []
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]
            confidence = line[1][1]
            amounts = extract_amounts(text)
            for amount, source in amounts:
                all_amounts.append((amount, confidence, source))
    
    # 去重
    unique_amounts = {}
    for amount, conf, source in all_amounts:
        if amount not in unique_amounts or unique_amounts[amount][1] < conf:
            unique_amounts[amount] = (amount, conf, source)
    
    amounts = list(unique_amounts.values())
    amounts.sort(key=lambda x: x[0], reverse=True)
    
    total = sum(a[0] for a in amounts)
    return [a[0] for a in amounts], total


def send_message(open_id: str, content: str, msg_type: str = "text"):
    """发送飞书消息"""
    global tenant_access_token
    
    if not tenant_access_token:
        get_tenant_access_token()
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "receive_id": open_id,
        "msg_type": msg_type,
        "content": json.dumps({"text": content}) if msg_type == "text" else content
    }
    
    resp = requests.post(url, headers=headers, json=data)
    return resp.json()


def format_result(amounts: List[float], total: float) -> str:
    """格式化识别结果"""
    if not amounts:
        return "❌ 未识别到转账金额\n\n请发送包含 ¥ 符号的微信转账截图"
    
    lines = ["✅ 识别结果：\n"]
    for amount in amounts:
        lines.append(f"💰 ¥{amount:.2f}")
    
    if len(amounts) > 1:
        lines.append(f"\n📊 共 {len(amounts)} 笔")
        lines.append(f"💵 总金额：¥{total:.2f}")
    
    return "\n".join(lines)


@app.route("/webhook", methods=["POST"])
def webhook():
    """飞书事件回调入口"""
    data = request.json
    log(f"[DEBUG] 收到请求: {json.dumps(data, ensure_ascii=False)[:1000]}")
    
    # URL 验证
    if data.get("type") == "url_verification":
        log(f"[DEBUG] URL验证请求, challenge: {data.get('challenge')}")
        return jsonify({"challenge": data.get("challenge")})
    
    # 处理消息
    event = data.get("event", {})
    message = event.get("message", {})
    msg_type = message.get("msg_type")
    sender = event.get("sender", {})
    open_id = sender.get("sender_id", {}).get("open_id", "")
    
    log(f"[DEBUG] 消息类型: {msg_type}, 发送者: {open_id}")
    
    # 只处理图片消息
    if msg_type == "image":
        try:
            # 发送处理中提示
            send_message(open_id, "🔄 正在识别图片...")
            
            # 获取图片信息
            content = json.loads(message.get("content", "{}"))
            file_key = content.get("file_key")
            
            log(f"[DEBUG] 图片 file_key: {file_key}")
            
            if not file_key:
                send_message(open_id, "❌ 无法获取图片信息")
                return jsonify({"code": 0})
            
            # 下载图片
            image_path = download_image(file_key)
            log(f"[DEBUG] 图片已下载: {image_path}")
            
            # 识别金额
            amounts, total = recognize_image(image_path)
            log(f"[DEBUG] 识别结果: amounts={amounts}, total={total}")
            
            # 发送结果
            result = format_result(amounts, total)
            send_message(open_id, result)
            
            # 清理临时文件
            if os.path.exists(image_path):
                os.remove(image_path)
                
        except Exception as e:
            log(f"[ERROR] 处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
            send_message(open_id, f"❌ 识别失败：{str(e)}")
    
    # 处理文本消息（帮助信息）
    elif msg_type == "text":
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "").strip()
        log(f"[DEBUG] 文本消息: {text}")
        
        if text in ["帮助", "help", "?", "？"]:
            help_text = """🤖 微信转账金额识别机器人

📋 使用方法：
直接发送微信转账截图，自动识别 ¥ 符号开头的金额

💡 支持功能：
• 单张/多笔转账金额识别
• 自动汇总计算总金额
• 置信度评估

📝 示例：
发送一张包含 ¥25.00 和 ¥6.90 的截图，将返回：
✅ 识别结果：
💰 ¥25.00
💰 ¥6.90

📊 共 2 笔
💵 总金额：¥31.90"""
            send_message(open_id, help_text)
        else:
            send_message(open_id, "📸 请发送微信转账截图，我会自动识别金额\n发送「帮助」查看使用说明")
    
    return jsonify({"code": 0})


if __name__ == "__main__":
    log("=" * 50)
    log("微信转账金额识别 - 飞书机器人版")
    log("=" * 50)
    
    # 检查配置
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        log("⚠️  请设置环境变量：")
        log("   FEISHU_APP_ID=your_app_id")
        log("   FEISHU_APP_SECRET=your_app_secret")
        log("   FEISHU_VERIFICATION_TOKEN=your_token (可选)")
    
    # 初始化 OCR（预热）
    log("\n预热 OCR 引擎...")
    get_ocr()
    
    log("\n启动 Web 服务...")
    log("请将飞书机器人的事件回调地址设置为：http://your-server:8080/webhook")
    log("-" * 50)
    
    app.run(host="0.0.0.0", port=8081, debug=False)