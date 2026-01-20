# coding=utf-8
"""
主题分类器

复用 TrendRadar 的关键词匹配系统实现主题分类
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from trendradar.core.frequency import matches_word_groups, _word_matches


class TopicClassifier:
    """主题分类器"""

    def __init__(self, topics_config_file: str):
        """
        初始化主题分类器

        Args:
            topics_config_file: topics.yaml 配置文件路径
        """
        self.topics_config_file = topics_config_file
        self.topics = self._load_topics()

    def _load_topics(self) -> List[Dict]:
        """
        加载主题配置

        Returns:
            主题列表，格式:
            [{
                "id": "ai-tech",
                "name": "AI与科技",
                "keywords": ["AI", "人工智能", "ChatGPT"],
                "description": "人工智能和科技领域",
                "priority": 1
            }]
        """
        config_path = Path(self.topics_config_file)
        if not config_path.exists():
            print(f"主题配置文件不存在: {self.topics_config_file}")
            return []

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            topics = data.get("topics", [])
            if not topics:
                print("主题配置为空")
                return []

            # 验证并标准化
            validated_topics = []
            for topic in topics:
                if not isinstance(topic, dict):
                    continue

                topic_id = topic.get("id", "")
                name = topic.get("name", "")
                keywords = topic.get("keywords", [])

                if not topic_id or not name or not keywords:
                    print(f"主题配置不完整，跳过: {topic}")
                    continue

                validated_topics.append({
                    "id": topic_id,
                    "name": name,
                    "keywords": keywords,
                    "description": topic.get("description", ""),
                    "priority": topic.get("priority", 999),
                })

            print(f"成功加载 {len(validated_topics)} 个主题配置")
            return validated_topics

        except Exception as e:
            print(f"加载主题配置失败: {e}")
            return []

    def classify(
        self,
        news_items: Dict[str, Dict],
        rss_items: Optional[Dict[str, Dict]] = None
    ) -> Dict[str, List[Dict]]:
        """
        将新闻分类到主题

        Args:
            news_items: 热榜新闻数据 {source_id: {title: title_data}}
            rss_items: RSS 数据 {feed_id: {title: item_data}}

        Returns:
            主题分类结果 {topic_id: [{title, source, url, ...}]}
        """
        if not self.topics:
            return {}

        results = {}

        # 处理热榜新闻
        if news_items:
            for source_id, titles in news_items.items():
                for title, title_data in titles.items():
                    matched_topics = self._match_topics(title)
                    for topic_id in matched_topics:
                        if topic_id not in results:
                            results[topic_id] = []

                        results[topic_id].append({
                            "title": title,
                            "source_type": "hotlist",
                            "source_id": source_id,
                            "url": title_data.get("url", ""),
                            "mobile_url": title_data.get("mobileUrl", ""),
                            "ranks": title_data.get("ranks", []),
                            "count": title_data.get("count", 1),
                            "first_time": title_data.get("first_time", ""),
                            "last_time": title_data.get("last_time", ""),
                        })

        # 处理 RSS 数据
        if rss_items:
            for feed_id, items in rss_items.items():
                for title, item_data in items.items():
                    matched_topics = self._match_topics(title)
                    for topic_id in matched_topics:
                        if topic_id not in results:
                            results[topic_id] = []

                        results[topic_id].append({
                            "title": title,
                            "source_type": "rss",
                            "source_id": feed_id,
                            "url": item_data.get("url", ""),
                            "published_at": item_data.get("published_at", ""),
                            "summary": item_data.get("summary", ""),
                            "author": item_data.get("author", ""),
                        })

        return results

    def _match_topics(self, title: str) -> List[str]:
        """
        匹配标题到主题

        Args:
            title: 新闻标题

        Returns:
            匹配的主题ID列表
        """
        matched = []

        for topic in self.topics:
            keywords = topic["keywords"]

            # 使用 _word_matches 检查是否匹配
            for keyword in keywords:
                if _word_matches(title, keyword):
                    matched.append(topic["id"])
                    break  # 一个主题只匹配一次

        return matched

    def get_topic_info(self, topic_id: str) -> Optional[Dict]:
        """获取主题信息"""
        for topic in self.topics:
            if topic["id"] == topic_id:
                return topic
        return None
