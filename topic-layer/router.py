#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Topic Layer Router - 主题再索引系统

功能：
1. 读取 topics.yaml 加载主题定义
2. 从 trendradar/output 数据库读取趋势数据
3. 根据关键词匹配生成 timeline.md
4. 实现幂等性（去重）
"""

import os
import sys
import sqlite3
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class TopicRouter:
    def __init__(self, base_dir: str = None, output_dir: str = None):
        """
        初始化路由器
        
        Args:
            base_dir: Topic Layer 基础目录（默认为脚本所在目录）
            output_dir: TrendRadar 输出目录（默认为 ../output/news）
        """
        if base_dir is None:
            # 默认使用脚本所在目录
            base_dir = Path(__file__).parent
        else:
            base_dir = Path(base_dir)
        
        self.base_dir = base_dir
        self.topics_file = base_dir / "topics.yaml"
        self.index_dir = base_dir / "index"
        
        # TrendRadar 输出目录（可配置）
        if output_dir is None:
            self.output_dir = base_dir.parent / "output" / "news"
        else:
            self.output_dir = Path(output_dir)
        
        self.topics = {}
        
    def load_topics(self) -> Dict:
        """加载主题配置"""
        if not self.topics_file.exists():
            raise FileNotFoundError(f"topics.yaml not found at {self.topics_file}")
        
        with open(self.topics_file, 'r', encoding='utf-8') as f:
            self.topics = yaml.safe_load(f)
        
        print(f"✓ 已加载 {len(self.topics)} 个主题")
        return self.topics
    
    def get_all_trends(self) -> List[Dict]:
        """从所有数据库文件读取趋势数据"""
        if not self.output_dir.exists():
            raise FileNotFoundError(
                f"Output directory not found: {self.output_dir}\n"
                "请先运行 TrendRadar 生成数据"
            )
        
        db_files = sorted(self.output_dir.glob("*.db"), reverse=True)
        
        if not db_files:
            raise FileNotFoundError(
                f"No database files found in {self.output_dir}\n"
                "请先运行 TrendRadar 生成数据"
            )
        
        all_trends = []
        print(f"✓ 找到 {len(db_files)} 个数据库文件")
        
        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # 查询新闻数据
                cursor.execute("""
                    SELECT 
                        ni.title,
                        ni.url,
                        ni.first_crawl_time,
                        p.name as source
                    FROM news_items ni
                    JOIN platforms p ON ni.platform_id = p.id
                    ORDER BY ni.first_crawl_time DESC
                """)
                
                rows = cursor.fetchall()
                
                # 提取日期（数据库文件名格式：YYYY-MM-DD.db）
                date = db_file.stem  # 去除 .db 后缀
                
                for row in rows:
                    title, url, crawl_time, source = row
                    all_trends.append({
                        'title': title,
                        'url': url if url else None,  # 保持 None 以便正确处理
                        'date': date,
                        'source': source,
                        # summary 字段保留以兼容 timeline 格式
                        'summary': None
                    })
                
                conn.close()
                print(f"  - {db_file.name}: {len(rows)} 条记录")
                
            except Exception as e:
                print(f"  ✗ 读取 {db_file.name} 失败: {e}")
                continue
        
        print(f"✓ 共读取 {len(all_trends)} 条趋势数据")
        return all_trends
    
    def match_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        关键词匹配（大小写不敏感，词边界检测）
        
        Args:
            text: 要匹配的文本
            keywords: 关键词列表
        
        Returns:
            是否匹配任意一个关键词
        """
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # 使用词边界正则表达式
            # \b 确保匹配完整单词，避免子字符串误匹配
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def route_trends(self, trends: List[Dict]) -> Dict[str, List[Dict]]:
        """
        将趋势数据路由到各个主题
        
        Returns:
            {topic_id: [trend1, trend2, ...]}
        """
        routed = defaultdict(list)
        
        for trend in trends:
            title = trend.get('title', '')
            summary = trend.get('summary', '')
            
            # 在 title 和 summary 中查找关键词
            search_text = f"{title} {summary}"
            
            for topic_id, topic_config in self.topics.items():
                keywords = topic_config.get('keywords', [])
                
                if self.match_keywords(search_text, keywords):
                    routed[topic_id].append(trend)
        
        return routed
    
    def load_existing_urls(self, timeline_file: Path) -> Set[str]:
        """
        加载已存在的 URL 集合（用于去重）
        
        Returns:
            已存在的 URL 集合
        """
        if not timeline_file.exists():
            return set()
        
        urls = set()
        
        with open(timeline_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 提取所有 URL（匹配 **链接**：https://... 格式）
            url_pattern = r'\*\*链接\*\*：(https?://[^\s\n]+)'
            urls = set(re.findall(url_pattern, content))
        
        return urls
    
    def group_by_date(self, trends: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按日期分组趋势数据
        
        Returns:
            {date: [trend1, trend2, ...]}
        """
        grouped = defaultdict(list)
        
        for trend in trends:
            date = trend.get('date', '')
            grouped[date].append(trend)
        
        return grouped
    
    def generate_timeline(self, topic_id: str, trends: List[Dict]):
        """
        生成或更新 timeline.md
        
        Args:
            topic_id: 主题 ID
            trends: 匹配的趋势列表
        """
        topic_config = self.topics[topic_id]
        topic_name = topic_config['name']
        
        # 创建主题目录
        topic_dir = self.index_dir / topic_id
        topic_dir.mkdir(parents=True, exist_ok=True)
        
        timeline_file = topic_dir / "timeline.md"
        
        # 加载已存在的 URL（用于去重）
        existing_urls = self.load_existing_urls(timeline_file)
        
        # 过滤出新的趋势（去重）
        # 只对有 URL 的趋势进行去重，无 URL 的趋势保留
        new_trends = []
        for trend in trends:
            if trend['url'] is None:
                # 无 URL 的趋势总是保留（无法去重）
                new_trends.append(trend)
            elif trend['url'] not in existing_urls:
                # 有 URL 且不在已存在列表中的趋势
                new_trends.append(trend)
        
        if not new_trends:
            print(f"  - {topic_id}: 没有新的趋势需要添加")
            return
        
        # 按日期分组（倒序）
        grouped = self.group_by_date(new_trends)
        sorted_dates = sorted(grouped.keys(), reverse=True)
        
        # 生成新的内容
        new_content = []
        
        for date in sorted_dates:
            new_content.append(f"\n## {date}\n")
            
            for trend in grouped[date]:
                title = trend['title']
                source = trend['source']
                url = trend['url'] if trend['url'] else "（无链接）"
                summary = trend['summary'] if trend['summary'] else "（无摘要）"
                
                new_content.append(f"\n**标题**：{title}  \n")
                new_content.append(f"**来源**：{source}  \n")
                new_content.append(f"**链接**：{url}\n")
                new_content.append(f"\n**摘要**：  \n{summary}\n")
                new_content.append(f"\n**我的判断**：  \n（留空，供人工补充）\n")
                new_content.append("\n---\n")
        
        # 读取现有内容（如果存在）
        if timeline_file.exists():
            with open(timeline_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # 找到第一行标题后的位置（更健壮的解析）
            lines = existing_content.split('\n')
            header_end_line = 0
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    header_end_line = i + 1
                    break
            
            # 重新组合内容
            header_lines = lines[:header_end_line]
            body_lines = lines[header_end_line:]
            
            final_content = (
                '\n'.join(header_lines) + '\n' +
                ''.join(new_content) +
                '\n'.join(body_lines)
            )
        else:
            # 新文件，直接创建
            final_content = f"# {topic_name}\n" + ''.join(new_content)
        
        # 写入文件
        with open(timeline_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"  ✓ {topic_id}: 添加了 {len(new_trends)} 条新趋势")
    
    def run(self):
        """运行主题路由"""
        print("=" * 60)
        print("Topic Layer Router - 主题再索引系统")
        print("=" * 60)
        
        try:
            # 1. 加载主题配置
            print("\n[1/4] 加载主题配置...")
            self.load_topics()
            
            # 2. 读取趋势数据
            print("\n[2/4] 读取趋势数据...")
            trends = self.get_all_trends()
            
            if not trends:
                print("✗ 没有找到任何趋势数据")
                return
            
            # 3. 路由趋势到主题
            print("\n[3/4] 路由趋势到主题...")
            routed = self.route_trends(trends)
            
            for topic_id, matched_trends in routed.items():
                topic_name = self.topics[topic_id]['name']
                print(f"  - {topic_id} ({topic_name}): {len(matched_trends)} 条匹配")
            
            # 4. 生成时间轴
            print("\n[4/4] 生成时间轴...")
            for topic_id, matched_trends in routed.items():
                self.generate_timeline(topic_id, matched_trends)
            
            print("\n" + "=" * 60)
            print("✓ 主题路由完成！")
            print(f"✓ 时间轴文件保存在: {self.index_dir}")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """主函数"""
    router = TopicRouter()
    router.run()


if __name__ == "__main__":
    main()
