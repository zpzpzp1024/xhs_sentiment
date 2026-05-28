"""
小红书评论抓取 + 情感分析脚本
用法: python xhs_sentiment.py --keyword "防晒霜" --count 100
"""

import argparse
import json
import time
import random
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from DrissionPage import ChromiumPage, ChromiumOptions
from openai import OpenAI
import os

load_dotenv()


def create_browser():
    opts = ChromiumOptions()
    opts.set_argument("--disable-blink-features=AutomationControlled")
    
    # 手动配置浏览器路径（根据实际情况修改）
    # Windows 常见路径示例:
    # - Chrome: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    # - Edge: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
    browser_path = os.getenv("CHROME_PATH")
    if browser_path and os.path.exists(browser_path):
        opts.set_browser_path(browser_path)
        print(f"[浏览器] 使用配置的浏览器路径: {browser_path}")
    else:
        print("[浏览器] 未配置浏览器路径，尝试自动查找...")
    
    page = ChromiumPage(opts)
    return page


def scrape_comments(keyword: str="启源Q05", target_count: int = 100) -> list[dict]:
    """抓取小红书搜索结果中笔记的评论"""
    print(f"[爬虫] 正在搜索关键字: {keyword}")
    page = create_browser()

    search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
    page.get(search_url)
    time.sleep(3)

    print("[爬虫] 请在浏览器中完成登录（如需要），登录完成后按 Enter 继续...")
    input()

    page.get(search_url)
    time.sleep(3)

    comments = []
    visited_notes = set()

   # 1. 精准定位：找到 class 包含 note-item 的 section 下，class 包含 cover 的 a 标签
    note_links = page.eles("css:section.note-item a.cover")
    
    # 2. 兜底方案：如果页面结构有变，直接全局搜索含有 cover 类的 a 标签
    if not note_links:
        note_links = page.eles("css:a.cover")

    print(f"[爬虫] 找到 {len(note_links)} 篇笔记链接")

    for i, note in enumerate(note_links):
        if len(comments) >= target_count:
            break

        try:
            href = note.attr("href")
            if not href or href in visited_notes:
                continue
            visited_notes.add(href)
            
            # 确保URL完整
            if not href.startswith("http"):
                href = f"https://www.xiaohongshu.com{href}"

            # 打印提取到的链接（调试用）
            print(f"[爬虫] 提取到笔记链接 [{i+1}/{len(note_links)}]: {href}")

            # 先尝试点击方式，如果失败再用page.get()
            try:
                # 先滚动到元素位置确保可见
                note.scroll.to_center()
                time.sleep(0.5)
                note.click()
                print(f"[爬虫] 点击成功，正在加载页面...")
            except:
                # 点击失败时回退到直接访问URL
                print(f"[爬虫] 点击失败，使用URL直接访问: {href}")
                page.get(href)
            
            time.sleep(random.uniform(3, 5))

            note_title_el = page.ele("css:.note-title, css:#detail-title, css:.title")
            note_title = note_title_el.text if note_title_el else f"笔记{i+1}"

            # 滚动加载评论区域
            for _ in range(5):
                page.scroll.down(500)
                time.sleep(random.uniform(1, 2))

            # 提取评论：支持主评论和子回复结构
            # 1. 获取所有父级评论容器
            parent_comments = page.eles("css:.parent-comment")
            
            for pc in parent_comments:
                if len(comments) >= target_count:
                    break
                
                # 提取主评论内容
                main_content = pc.ele("css:.comment-item:not(.comment-item-sub) .content span")
                if main_content:
                    text = main_content.text.strip()
                    if text and len(text) > 1 and text not in [c["comment"] for c in comments]:
                        comments.append({
                            "note_title": note_title,
                            "comment": text,
                            "type": "主评论"
                        })
                
                # 尝试点击展开更多回复
                try:
                    show_more = pc.ele("css:.show-more")
                    if show_more and "展开" in show_more.text:
                        show_more.click()
                        time.sleep(1)
                except:
                    pass
                
                # 提取子回复内容
                sub_comments = pc.eles("css:.comment-item-sub .content span")
                for sub in sub_comments:
                    if len(comments) >= target_count:
                        break
                    text = sub.text.strip()
                    if text and len(text) > 1 and text not in [c["comment"] for c in comments]:
                        comments.append({
                            "note_title": note_title,
                            "comment": text,
                            "type": "回复"
                        })

            print(f"[爬虫] 已收集 {len(comments)}/{target_count} 条评论")

            page.back()
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"[爬虫] 跳过一篇笔记: {e}")
            try:
                page.back()
                time.sleep(1)
            except:
                pass
            continue

    page.quit()
    print(f"[爬虫] 抓取完成，共 {len(comments)} 条评论")
    return comments


def analyze_sentiment(comments: list[dict], batch_size: int = 10) -> list[dict]:
    """调用大模型 API 批量分析评论情感"""
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        print("[错误] 请在 .env 文件中配置 LLM_API_KEY")
        return comments

    client = OpenAI(base_url=base_url, api_key=api_key)
    print(f"[分析] 使用模型: {model}，共 {len(comments)} 条评论")

    for i in range(0, len(comments), batch_size):
        batch = comments[i:i + batch_size]
        texts = [c["comment"] for c in batch]

        prompt = f"""请分析以下评论的情感倾向，对每条评论返回 JSON 数组，每个元素包含:
- sentiment: "正面" / "中性" / "负面"
- confidence: 0-1 的置信度分数
- keywords: 关键词列表（最多3个）

评论列表:
{json.dumps(texts, ensure_ascii=False, indent=2)}

只返回 JSON 数组，不要其他内容。"""

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            results = json.loads(content)
            for j, result in enumerate(results):
                if j < len(batch):
                    batch[j]["sentiment"] = result.get("sentiment", "未知")
                    batch[j]["confidence"] = result.get("confidence", 0)
                    batch[j]["keywords"] = "、".join(result.get("keywords", []))

            print(f"[分析] 已完成 {min(i + batch_size, len(comments))}/{len(comments)}")

        except Exception as e:
            print(f"[分析] 第 {i//batch_size + 1} 批分析失败: {e}")
            for c in batch:
                c.setdefault("sentiment", "分析失败")
                c.setdefault("confidence", 0)
                c.setdefault("keywords", "")

        time.sleep(1)

    return comments


def export_report(comments: list[dict], keyword: str):
    """导出 Excel 报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sentiment_report_{keyword}_{timestamp}.xlsx"

    df = pd.DataFrame(comments)
    df.index = range(1, len(df) + 1)
    df.index.name = "序号"

    total = len(df)
    positive = len(df[df["sentiment"] == "正面"])
    neutral = len(df[df["sentiment"] == "中性"])
    negative = len(df[df["sentiment"] == "负面"])

    summary_data = {
        "指标": ["总评论数", "正面评论", "中性评论", "负面评论", "正面占比", "负面占比"],
        "数值": [
            total,
            positive,
            neutral,
            negative,
            f"{positive/total*100:.1f}%" if total else "0%",
            f"{negative/total*100:.1f}%" if total else "0%",
        ],
    }
    df_summary = pd.DataFrame(summary_data)

    all_keywords = []
    for kw_str in df.get("keywords", []):
        if isinstance(kw_str, str) and kw_str:
            all_keywords.extend(kw_str.split("、"))
    if all_keywords:
        kw_series = pd.Series(all_keywords)
        kw_counts = kw_series.value_counts().head(10)
        df_keywords = pd.DataFrame({"关键词": kw_counts.index, "出现次数": kw_counts.values})
    else:
        df_keywords = pd.DataFrame({"关键词": [], "出现次数": []})

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="评论明细")
        df_summary.to_excel(writer, sheet_name="统计概览", index=False)
        df_keywords.to_excel(writer, sheet_name="统计概览", index=False, startrow=len(df_summary) + 3)

    print(f"[报告] 已导出: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="小红书评论情感分析工具")
    parser.add_argument("--keyword", "-k", required=False, default="启源Q05", help="搜索关键字")
    parser.add_argument("--count", "-c", type=int, default=100, help="目标评论数量")
    args = parser.parse_args()

    print("=" * 50)
    print(f"  小红书评论情感分析")
    print(f"  关键字: {args.keyword} | 目标: {args.count} 条")
    print("=" * 50)

    comments = scrape_comments(args.keyword, args.count)
    if not comments:
        print("[错误] 未抓取到任何评论，请检查网络或登录状态")
        return

    comments = analyze_sentiment(comments)
    export_report(comments, args.keyword)
    print("[完成] 全部流程结束")


if __name__ == "__main__":
    main()
