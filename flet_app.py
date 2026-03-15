#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信转账金额识别 - Flet 版本
支持批量上传多张图片
"""

import flet as ft
import os
import re
from typing import List, Tuple

# OCR 引擎
ocr_engine = None

def get_ocr():
    global ocr_engine
    if ocr_engine is None:
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
    return ocr_engine

def extract_amounts(text: str) -> List[Tuple[float, str]]:
    results = []
    pattern = r'[¥￥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        try:
            amount = float(match.group(1).replace(',', ''))
            if 0.01 <= amount <= 100000:
                results.append((amount, match.group(0)))
        except:
            continue
    seen = {}
    for a, s in results:
        if a not in seen:
            seen[a] = (a, s)
    return list(seen.values())

def recognize_image(image_path: str):
    ocr = get_ocr()
    result = ocr.ocr(image_path, cls=True)
    if not result or not result[0]:
        return [], 0.0
    all_amounts = []
    for line in result[0]:
        if line and len(line) >= 2:
            for amount, source in extract_amounts(line[1][0]):
                all_amounts.append((amount, line[1][1], source))
    unique = {}
    for a, c, s in all_amounts:
        if a not in unique or unique[a][1] < c:
            unique[a] = (a, c, s)
    amounts = sorted(unique.values(), key=lambda x: x[0], reverse=True)
    return [a[0] for a in amounts], sum(a[0] for a in amounts)

def main(page: ft.Page):
    page.title = "微信转账金额识别"
    page.window.width = 600
    page.window.height = 800
    
    results = []
    
    # 标题
    title_text = ft.Text("💰 微信转账金额识别", size=28, weight=ft.FontWeight.BOLD, text_align="center")
    
    # 多行输入框
    path_field = ft.TextField(
        label="图片路径（每行一个）",
        hint_text="粘贴多个图片路径，每行一个\n例如：\nC:\\Users\\Desktop\\img1.jpg\nC:\\Users\\Desktop\\img2.jpg",
        width=550,
        multiline=True,
        min_lines=5,
        max_lines=15
    )
    
    # 状态
    status = ft.Text("", size=14, color="orange")
    
    # 结果
    result_text = ft.Text("", size=15, selectable=True)
    
    # 总金额
    total_text = ft.Text("", size=24, weight=ft.FontWeight.BOLD, color="green")
    
    def process_images(e=None):
        text = path_field.value.strip()
        if not text:
            status.value = "❌ 请输入图片路径"
            page.update()
            return
        
        # 解析多个路径（每行一个）
        paths = []
        for line in text.split('\n'):
            path = line.strip().strip('"').strip("'").strip()
            if path:
                paths.append(path)
        
        if not paths:
            status.value = "❌ 请输入图片路径"
            page.update()
            return
        
        status.value = f"🔄 正在识别 {len(paths)} 张图片..."
        page.update()
        
        success = 0
        failed = 0
        
        for i, path in enumerate(paths, 1):
            if not os.path.exists(path):
                failed += 1
                status.value = f"❌ [{i}/{len(paths)}] 文件不存在: {os.path.basename(path)}"
                page.update()
                continue
            
            try:
                amounts, total = recognize_image(path)
                if amounts:
                    results.append((os.path.basename(path), amounts, total))
                    success += 1
                else:
                    failed += 1
                    status.value = f"⚠️ [{i}/{len(paths)}] 未识别到金额: {os.path.basename(path)}"
            except Exception as ex:
                failed += 1
                status.value = f"❌ [{i}/{len(paths)}] 错误: {str(ex)}"
            
            status.value = f"🔄 处理中... {i}/{len(paths)}"
            page.update()
        
        # 显示结果
        if results:
            lines = []
            grand = 0
            for name, amts, t in results:
                lines.append(f"📷 {name}")
                for a in amts:
                    lines.append(f"   💰 ¥{a:.2f}")
                lines.append(f"   小计: ¥{t:.2f}")
                lines.append("")
                grand += t
            
            result_text.value = "\n".join(lines)
            total_text.value = f"💵 总金额: ¥{grand:.2f} (共{len(results)}张图片)"
        
        status.value = f"✅ 完成！成功 {success} 张，失败 {failed} 张"
        page.update()
    
    def clear_all(e):
        results.clear()
        path_field.value = ""
        result_text.value = ""
        total_text.value = ""
        status.value = ""
        page.update()
    
    # 按钮
    btn_recognize = ft.ElevatedButton("🔍 批量识别", on_click=process_images, width=180, height=40)
    btn_clear = ft.ElevatedButton("🗑️ 清空结果", on_click=clear_all, width=180, height=40)
    
    # 帮助
    help_text = ft.Text(
        "💡 支持批量识别：粘贴多个图片路径（每行一个），点击识别\n"
        "只识别 ¥ 符号开头的转账金额",
        size=12, color="grey"
    )
    
    # 添加控件
    page.add(
        ft.Column([
            ft.Divider(height=10, color="transparent"),
            title_text,
            ft.Divider(height=20, color="transparent"),
            path_field,
            ft.Divider(height=15, color="transparent"),
            ft.Row([btn_recognize, btn_clear], alignment="center"),
            ft.Divider(height=15, color="transparent"),
            status,
            ft.Divider(height=10, color="transparent"),
            total_text,
            ft.Divider(height=10, color="transparent"),
            result_text,
            ft.Divider(height=20, color="transparent"),
            help_text,
        ], scroll="auto")
    )
    
    # 初始化OCR
    status.value = "🔄 初始化OCR引擎..."
    page.update()
    try:
        get_ocr()
        status.value = "✅ 就绪 - 支持批量识别多张图片"
    except Exception as ex:
        status.value = f"❌ OCR初始化失败: {str(ex)}"
    page.update()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=7861)