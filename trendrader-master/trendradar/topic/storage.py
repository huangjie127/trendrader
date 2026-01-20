# coding=utf-8
"""
主题存储模块

负责将主题分类结果存储为 Markdown 文件
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class TopicStorage:
    """主题存储器"""

    def __init__(self, base_dir: str = "output/topics", timezone: str = "Asia/Shanghai"):
        """
        初始化主题存储器

        Args:
            base_dir: 主题存储根目录
            timezone: 时区
        """
        self.base_dir = Path(base_dir)
        self.timezone = timezone
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_topic_classification(
        self,
        date: str,
        topic_id: str,
        topic_name: str,
        items: List[Dict],
        append: bool = True
    ) -> str:
        """
        保存主题分类结果到 Markdown 文件

        Args:
            date: 日期 (YYYY-MM-DD)
            topic_id: 主题ID
            topic_name: 主题名称
            items: 分类条目列表
            append: 是否追加模式（同一天多次运行）

        Returns:
            保存的文件路径
        """
        topic_dir = self.base_dir / topic_id
        topic_dir.mkdir(parents=True, exist_ok=True)

        file_path = topic_dir / f"{date}.md"

        # 检查是否已存在
        if file_path.exists() and append:
            # 追加模式：读取现有内容，合并去重
            return self._append_to_existing(file_path, items)
        else:
            # 新建文件
            content = self._generate_markdown(date, topic_name, items)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return str(file_path)

    def _generate_markdown(
        self,
        date: str,
        topic_name: str,
        items: List[Dict]
    ) -> str:
        """
        生成 Markdown 内容

        格式:
        # [主题名称] - YYYY-MM-DD

        ## 📊 统计摘要
        - 总条目: N 条
        - 热榜来源: M 条
        - RSS来源: K 条

        ## 📰 内容列表

        ### 热榜新闻
        1. **标题** - [来源] 出现N次 [链接]
           - 排名: #1, #3, #5
           - 时间: 09:00 ~ 12:00

        ### RSS订阅
        1. **标题** - [来源] [链接]
           - 发布时间: 2026-01-20 10:00
           - 摘要: ...

        ## 🖊️ 人工备注
        <!-- 在此添加你的分析和思考 -->

        ## ⭐ 重要度标记
        <!-- 1-5星，数字越大越重要 -->
        重要度: ☐ 1星 ☐ 2星 ☐ 3星 ☐ 4星 ☐ 5星
        """
        lines = []

        # 标题
        lines.append(f"# {topic_name} - {date}\n")

        # 统计摘要
        hotlist_count = sum(1 for item in items if item.get("source_type") == "hotlist")
        rss_count = sum(1 for item in items if item.get("source_type") == "rss")

        lines.append("## 📊 统计摘要\n")
        lines.append(f"- **总条目**: {len(items)} 条")
        lines.append(f"- **热榜来源**: {hotlist_count} 条")
        lines.append(f"- **RSS来源**: {rss_count} 条\n")

        # 内容列表
        lines.append("## 📰 内容列表\n")

        # 热榜新闻
        hotlist_items = [item for item in items if item.get("source_type") == "hotlist"]
        if hotlist_items:
            lines.append("### 热榜新闻\n")
            for i, item in enumerate(hotlist_items, 1):
                title = item["title"]
                source = item.get("source_id", "未知")
                url = item.get("url", "")
                count = item.get("count", 1)
                ranks = item.get("ranks", [])
                first_time = item.get("first_time", "")
                last_time = item.get("last_time", "")

                # 标题和基本信息
                if url:
                    lines.append(f"{i}. **[{title}]({url})**")
                else:
                    lines.append(f"{i}. **{title}**")

                lines.append(f"   - 来源: {source} | 出现 {count} 次")

                # 排名信息
                if ranks:
                    rank_str = ", ".join([f"#{r}" for r in ranks[:5]])  # 最多显示5个
                    if len(ranks) > 5:
                        rank_str += "..."
                    lines.append(f"   - 排名: {rank_str}")

                # 时间信息
                if first_time:
                    time_display = first_time if first_time == last_time else f"{first_time} ~ {last_time}"
                    lines.append(f"   - 时间: {time_display}")

                lines.append("")  # 空行

        # RSS 订阅
        rss_items_list = [item for item in items if item.get("source_type") == "rss"]
        if rss_items_list:
            lines.append("### RSS订阅\n")
            for i, item in enumerate(rss_items_list, 1):
                title = item["title"]
                source = item.get("source_id", "未知")
                url = item.get("url", "")
                published_at = item.get("published_at", "")
                summary = item.get("summary", "")
                author = item.get("author", "")

                # 标题和基本信息
                if url:
                    lines.append(f"{i}. **[{title}]({url})**")
                else:
                    lines.append(f"{i}. **{title}**")

                lines.append(f"   - 来源: {source}")

                if published_at:
                    lines.append(f"   - 发布时间: {published_at}")

                if author:
                    lines.append(f"   - 作者: {author}")

                if summary:
                    # 限制摘要长度
                    summary_short = summary[:200] + "..." if len(summary) > 200 else summary
                    lines.append(f"   - 摘要: {summary_short}")

                lines.append("")  # 空行

        # 人工备注区
        lines.append("\n---\n")
        lines.append("## 🖊️ 人工备注\n")
        lines.append("<!-- 在此添加你的分析和思考 -->\n\n")

        # 重要度标记
        lines.append("## ⭐ 重要度标记\n")
        lines.append("<!-- 1-5星，数字越大越重要 -->\n")
        lines.append("重要度: ☐ 1星 ☐ 2星 ☐ 3星 ☐ 4星 ☐ 5星\n")

        return "\n".join(lines)

    def _append_to_existing(self, file_path: Path, new_items: List[Dict]) -> str:
        """
        追加到已存在的文件（简单实现：重新生成，去重）

        Args:
            file_path: 文件路径
            new_items: 新条目

        Returns:
            文件路径
        """
        # 简化处理：直接覆盖（MVP版本）
        # 生产环境应该读取现有内容，合并去重，保留人工标注
        with open(file_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # 提取人工备注区域（简单实现）
        human_notes = ""
        importance = ""

        if "## 🖊️ 人工备注" in existing_content:
            parts = existing_content.split("## 🖊️ 人工备注")
            if len(parts) > 1:
                notes_section = parts[1].split("## ⭐ 重要度标记")
                if notes_section:
                    human_notes = notes_section[0].strip()
                if len(notes_section) > 1:
                    importance = notes_section[1].strip()

        # 重新生成（保留人工标注）
        date = file_path.stem
        topic_name = file_path.parent.name

        # 读取标题从现有文件
        if "# " in existing_content:
            first_line = existing_content.split("\n")[0]
            if " - " in first_line:
                topic_name = first_line.split(" - ")[0].replace("#", "").strip()

        content = self._generate_markdown(date, topic_name, new_items)

        # 替换人工备注区域
        if human_notes:
            content = content.replace(
                "<!-- 在此添加你的分析和思考 -->",
                human_notes
            )
        if importance:
            content = content.replace(
                "重要度: ☐ 1星 ☐ 2星 ☐ 3星 ☐ 4星 ☐ 5星",
                importance
            )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def read_topic_file(self, topic_id: str, date: str) -> Optional[str]:
        """
        读取主题文件内容

        Args:
            topic_id: 主题ID
            date: 日期

        Returns:
            文件内容，不存在返回 None
        """
        file_path = self.base_dir / topic_id / f"{date}.md"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_topic_dates(self, topic_id: str) -> List[str]:
        """
        列出主题的所有日期

        Args:
            topic_id: 主题ID

        Returns:
            日期列表（降序）
        """
        topic_dir = self.base_dir / topic_id
        if not topic_dir.exists():
            return []

        dates = []
        for file_path in topic_dir.glob("*.md"):
            date_str = file_path.stem
            dates.append(date_str)

        return sorted(dates, reverse=True)
