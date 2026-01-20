# coding=utf-8
"""
历史摘要生成器

读取最近N天的主题数据，生成历史摘要用于AI分析
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .storage import TopicStorage


class HistorySummarizer:
    """历史摘要生成器"""

    def __init__(
        self,
        topic_storage: TopicStorage,
        timezone: str = "Asia/Shanghai"
    ):
        """
        初始化历史摘要生成器

        Args:
            topic_storage: 主题存储器实例
            timezone: 时区
        """
        self.storage = topic_storage
        self.timezone = timezone

    def get_recent_summaries(
        self,
        days: int = 7,
        current_date: Optional[str] = None,
        max_tokens: int = 3000
    ) -> str:
        """
        获取最近N天的主题历史摘要

        Args:
            days: 天数
            current_date: 当前日期 (YYYY-MM-DD)，None则使用今天
            max_tokens: 最大token数（粗略估算，1 token ≈ 1.5字符）

        Returns:
            格式化的历史摘要文本（Markdown格式）
        """
        if current_date is None:
            from trendradar.utils.time import get_configured_time
            now = get_configured_time(self.timezone)
            current_date = now.strftime("%Y-%m-%d")

        # 获取日期列表（排除今天）
        dates = self._get_date_range(current_date, days, exclude_current=True)
        if not dates:
            return ""

        # 收集所有主题的历史数据
        summaries = []
        total_chars = 0
        max_chars = int(max_tokens * 1.5)  # 粗略转换

        # 遍历主题目录
        topics_dir = Path(self.storage.base_dir)
        if not topics_dir.exists():
            return ""

        for topic_dir in topics_dir.iterdir():
            if not topic_dir.is_dir():
                continue

            topic_id = topic_dir.name
            topic_summary = self._summarize_topic_history(topic_id, dates)

            if topic_summary:
                summary_text = f"### {topic_summary['topic_name']}\n\n{topic_summary['content']}\n"
                summary_chars = len(summary_text)

                if total_chars + summary_chars > max_chars:
                    # 超过限制，停止添加
                    summaries.append("\n> ⚠️ 历史数据过多，已截断...\n")
                    break

                summaries.append(summary_text)
                total_chars += summary_chars

        if not summaries:
            return ""

        # 生成最终摘要
        header = f"## 📊 最近{len(dates)}天同主题历史\n\n"
        header += f"> 时间范围: {dates[-1]} 至 {dates[0]}\n\n"

        return header + "\n".join(summaries)

    def _get_date_range(
        self,
        end_date: str,
        days: int,
        exclude_current: bool = True
    ) -> List[str]:
        """
        获取日期范围

        Args:
            end_date: 结束日期 (YYYY-MM-DD)
            days: 天数
            exclude_current: 是否排除当前日期

        Returns:
            日期列表（降序）
        """
        end = datetime.strptime(end_date, "%Y-%m-%d")
        dates = []

        start_offset = 1 if exclude_current else 0

        for i in range(start_offset, days + start_offset):
            date = end - timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))

        return dates

    def _summarize_topic_history(
        self,
        topic_id: str,
        dates: List[str]
    ) -> Optional[Dict]:
        """
        汇总单个主题的历史数据

        Args:
            topic_id: 主题ID
            dates: 日期列表

        Returns:
            {
                "topic_name": str,
                "content": str (Markdown格式的摘要)
            }
        """
        history_items = []

        for date in dates:
            content = self.storage.read_topic_file(topic_id, date)
            if content:
                # 提取关键信息
                stats = self._extract_stats(content)
                human_notes = self._extract_human_notes(content)

                if stats.get("total_items", 0) > 0:
                    history_items.append({
                        "date": date,
                        "stats": stats,
                        "human_notes": human_notes
                    })

        if not history_items:
            return None

        # 提取主题名称
        topic_name = topic_id
        if history_items:
            first_content = self.storage.read_topic_file(topic_id, history_items[0]["date"])
            if first_content and first_content.startswith("#"):
                first_line = first_content.split("\n")[0]
                if " - " in first_line:
                    topic_name = first_line.split(" - ")[0].replace("#", "").strip()

        # 生成摘要内容
        content_lines = []

        for item in history_items:
            date = item["date"]
            stats = item["stats"]
            human_notes = item["human_notes"]

            content_lines.append(f"**{date}**: {stats['total_items']}条 (热榜{stats['hotlist']}, RSS{stats['rss']})")

            if human_notes:
                content_lines.append(f"  > 备注: {human_notes[:100]}{'...' if len(human_notes) > 100 else ''}")

        return {
            "topic_name": topic_name,
            "content": "\n".join(content_lines)
        }

    def _extract_stats(self, content: str) -> Dict:
        """从Markdown内容提取统计信息"""
        stats = {
            "total_items": 0,
            "hotlist": 0,
            "rss": 0
        }

        for line in content.split("\n"):
            if "总条目" in line:
                try:
                    stats["total_items"] = int(line.split(":")[1].split("条")[0].strip().replace("**", ""))
                except:
                    pass
            elif "热榜来源" in line:
                try:
                    stats["hotlist"] = int(line.split(":")[1].split("条")[0].strip().replace("**", ""))
                except:
                    pass
            elif "RSS来源" in line:
                try:
                    stats["rss"] = int(line.split(":")[1].split("条")[0].strip().replace("**", ""))
                except:
                    pass

        return stats

    def _extract_human_notes(self, content: str) -> str:
        """提取人工备注内容"""
        if "## 🖊️ 人工备注" not in content:
            return ""

        parts = content.split("## 🖊️ 人工备注")
        if len(parts) < 2:
            return ""

        notes_section = parts[1].split("## ⭐ 重要度标记")[0]
        notes = notes_section.replace("<!--", "").replace("-->", "").strip()

        # 移除默认提示文本
        if "在此添加你的分析和思考" in notes:
            return ""

        return notes
