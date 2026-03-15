#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信转账截图金额识别工具 - Web版
启动方式：python web.py
访问：http://localhost:7860
"""

import os
import re
from typing import List, Tuple
import gradio as gr
from paddleocr import PaddleOCR

# 全局 OCR 实例（避免重复初始化）
ocr_engine = None


def get_ocr():
    """获取或初始化 OCR 引擎"""
    global ocr_engine
    if ocr_engine is None:
        print("正在初始化 OCR 引擎...")
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        print("OCR 引擎初始化完成 ✓")
    return ocr_engine


def extract_amounts(text: str) -> List[Tuple[float, str]]:
    """
    从文本中提取所有带 ¥ 符号的金额
    
    Args:
        text: OCR 识别的文本
        
    Returns:
        List[Tuple[float, str]]: [(金额, 原始文本), ...]
    """
    results = []
    pattern = r'[¥￥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'
    
    matches = re.finditer(pattern, text, re.IGNORECASE)
    for match in matches:
        amount_str = match.group(1)
        amount_str_clean = amount_str.replace(',', '')
        try:
            amount = float(amount_str_clean)
            if 0.01 <= amount <= 100000:  # 合理范围
                results.append((amount, match.group(0)))
        except ValueError:
            continue
    
    # 去重
    seen = {}
    for amount, source in results:
        if amount not in seen:
            seen[amount] = (amount, source)
    
    return list(seen.values())


def recognize_image(image) -> Tuple[str, str, float]:
    """
    识别图片中的转账金额
    
    Args:
        image: Gradio 上传的图片
        
    Returns:
        Tuple[str, str, float]: (详情文本, 汇总文本, 总金额)
    """
    if image is None:
        return "请上传图片", "", 0.0
    
    try:
        ocr = get_ocr()
        result = ocr.ocr(image, cls=True)
        
        if not result or not result[0]:
            return "未识别到任何文本", "", 0.0
        
        # 收集所有识别到的文本
        all_texts = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0]
                confidence = line[1][1]
                all_texts.append((text, confidence))
        
        # 提取金额
        all_amounts = []
        for text, conf in all_texts:
            amounts = extract_amounts(text)
            for amount, source in amounts:
                all_amounts.append((amount, conf, source))
        
        # 去重
        unique_amounts = {}
        for amount, conf, source in all_amounts:
            if amount not in unique_amounts or unique_amounts[amount][1] < conf:
                unique_amounts[amount] = (amount, conf, source)
        
        amounts = list(unique_amounts.values())
        amounts.sort(key=lambda x: x[0], reverse=True)
        
        if not amounts:
            detail = "### 识别到的文本：\n"
            for text, conf in all_texts[:10]:
                detail += f"- {text} (置信度: {conf:.1%})\n"
            return detail, "⚠️ 未识别到转账金额（没有找到 ¥ 符号开头的数字）", 0.0
        
        # 构建详情
        detail = "### 识别结果：\n\n"
        for amount, conf, source in amounts:
            detail += f"💰 **¥{amount:.2f}** (置信度: {conf:.1%})\n"
        
        # 构建汇总
        total = sum(a[0] for a in amounts)
        summary = f"""### 📊 汇总
- 识别到的转账笔数：**{len(amounts)} 笔**
- 总金额：**¥{total:.2f}**"""
        
        return detail, summary, total
        
    except Exception as e:
        return f"识别出错：{str(e)}", "", 0.0


def process_images(images) -> Tuple[str, str, float]:
    """
    批量处理多张图片
    
    Args:
        images: Gradio 上传的图片列表
        
    Returns:
        Tuple[str, str, float]: (详情文本, 汇总文本, 总金额)
    """
    if not images:
        return "请上传图片", "", 0.0
    
    all_results = []
    grand_total = 0.0
    
    for i, image in enumerate(images, 1):
        detail, _, total = recognize_image(image)
        if total > 0:
            all_results.append(f"### 图片 {i}\n{detail}\n小计：¥{total:.2f}\n---")
            grand_total += total
        else:
            all_results.append(f"### 图片 {i}\n{detail}\n---")
    
    detail_text = "\n\n".join(all_results)
    summary = f"""### 📊 总汇总
- 处理图片：**{len(images)} 张**
- 总金额：**¥{grand_total:.2f}**"""
    
    return detail_text, summary, grand_total


# 创建界面
with gr.Blocks(
    title="微信转账金额识别",
    theme=gr.themes.Soft(),
    css="""
    .amount-display { font-size: 2em; font-weight: bold; color: #22c55e; }
    """
) as app:
    
    gr.Markdown("""
    # 💰 微信转账金额识别
    
    上传微信转账截图，自动识别图片中 **¥** 符号开头的转账金额。
    """)
    
    with gr.Tabs():
        with gr.TabItem("单张图片"):
            with gr.Row():
                with gr.Column():
                    single_input = gr.Image(label="上传转账截图", type="filepath")
                    single_btn = gr.Button("🔍 识别金额", variant="primary", size="lg")
                
                with gr.Column():
                    single_detail = gr.Markdown(label="识别详情")
                    single_summary = gr.Markdown(label="汇总")
                    single_total = gr.Number(label="总金额", precision=2)
        
        with gr.TabItem("批量处理"):
            with gr.Row():
                with gr.Column():
                    batch_input = gr.File(
                        label="上传多张转账截图",
                        file_count="multiple",
                        file_types=["image"]
                    )
                    batch_btn = gr.Button("🔍 批量识别", variant="primary", size="lg")
                
                with gr.Column():
                    batch_detail = gr.Markdown(label="识别详情")
                    batch_summary = gr.Markdown(label="汇总")
                    batch_total = gr.Number(label="总金额", precision=2)
    
    gr.Markdown("""
    ---
    ### 使用说明
    1. 上传微信转账截图（支持 JPG、PNG 等格式）
    2. 点击识别按钮
    3. 系统会自动识别 **¥** 符号后面的转账金额
    4. 多笔转账会自动汇总计算总金额
    """)
    
    # 绑定事件
    single_btn.click(
        recognize_image,
        inputs=[single_input],
        outputs=[single_detail, single_summary, single_total]
    )
    
    batch_btn.click(
        process_images,
        inputs=[batch_input],
        outputs=[batch_detail, batch_summary, batch_total]
    )


if __name__ == "__main__":
    print("=" * 50)
    print("微信转账金额识别 - Web版")
    print("=" * 50)
    print("启动中...")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )