# Topic Layer - 长期主题追踪系统

## 📖 系统介绍

Topic Layer 是一个建立在 TrendRadar 输出之上的**长期主题追踪系统**，用于帮助用户主动、系统性地获取对自己有用的信息，而不是被情绪化算法推送牵着走。

### 核心特点

✅ **不修改 TrendRadar 源代码**  
✅ **不依赖 AI 的长期记忆**  
✅ **所有长期结构由文件系统保证**  
✅ **人类保留最终控制权（通过 YAML 定义主题）**

### 工作原理

系统不负责爬取信息本身，而是对 TrendRadar 已经生成的趋势数据进行**主题再索引（topic re-indexing）**，并以**时间轴（timeline）**的形式长期存储和更新。

```
TrendRadar 输出数据 → Topic Layer 主题再索引 → 时间轴存储
```

---

## 📁 目录结构

```
topic-layer/
├── topics.yaml              # 人工定义的主题与关键词
├── router.py                # 核心脚本：主题再索引
├── index/                   # 主题时间轴存储目录
│   ├── ai_finance/
│   │   └── timeline.md
│   ├── climate_tech/
│   │   └── timeline.md
│   └── .gitkeep
└── README.md                # 本文档
```

---

## 🚀 快速开始

### 1. 配置主题

编辑 `topics.yaml` 文件，定义你关心的主题：

```yaml
ai_finance:
  name: AI 对金融体系与劳动力市场的影响
  description: >
    长期追踪人工智能在银行、交易、风控、会计、
    金融就业结构中的影响。
  keywords:
    - AI
    - artificial intelligence
    - finance
    - banking
    - trading
    - labor
    - employment

climate_tech:
  name: 气候科技与碳中和
  description: >
    追踪碳捕捉、新能源、气候政策、ESG 投资等领域的技术突破与政策变化。
  keywords:
    - climate
    - carbon
    - renewable energy
    - ESG
    - net zero
```

**配置说明：**

- `主题 ID`（如 `ai_finance`）：作为文件夹名，只能包含字母、数字、下划线
- `name`：主题的人类可读名称
- `description`：主题的详细描述（可选）
- `keywords`：关键词列表，用于匹配趋势（大小写不敏感）

### 2. 运行路由器

确保 TrendRadar 已经运行并生成了数据（`output/news/*.db` 文件存在）。

```bash
# 进入 topic-layer 目录
cd topic-layer

# 运行路由器
python router.py
```

**运行效果：**

```
============================================================
Topic Layer Router - 主题再索引系统
============================================================

[1/4] 加载主题配置...
✓ 已加载 2 个主题

[2/4] 读取趋势数据...
✓ 找到 7 个数据库文件
  - 2025-12-27.db: 245 条记录
  - 2025-12-26.db: 238 条记录
  ...
✓ 共读取 1650 条趋势数据

[3/4] 路由趋势到主题...
  - ai_finance (AI 对金融体系与劳动力市场的影响): 23 条匹配
  - climate_tech (气候科技与碳中和): 8 条匹配

[4/4] 生成时间轴...
  ✓ ai_finance: 添加了 23 条新趋势
  ✓ climate_tech: 添加了 8 条新趋势

============================================================
✓ 主题路由完成！
✓ 时间轴文件保存在: /path/to/topic-layer/index
============================================================
```

### 3. 查看结果

打开 `index/<topic_id>/timeline.md` 查看主题时间轴：

```markdown
# AI 对金融体系与劳动力市场的影响

## 2026-01-19

**标题**：AI reduces junior analyst roles in banks  
**来源**：HackerNews  
**链接**：https://example.com/...

**摘要**：  
According to recent reports, major banks are reducing junior analyst positions due to AI automation in financial modeling and risk assessment.

**我的判断**：  
（留空，供人工补充）

---

## 2026-01-18

**标题**：Another related trend  
**来源**：Reddit  
**链接**：https://...

**摘要**：  
...

**我的判断**：  
（留空）

---
```

---

## ⚙️ 配置说明

### 添加新主题

1. 编辑 `topics.yaml`
2. 添加新的主题定义（参考已有主题格式）
3. 运行 `python router.py`

**示例：**

```yaml
quantum_computing:
  name: 量子计算突破
  description: 追踪量子计算领域的技术突破和商业应用
  keywords:
    - quantum computing
    - quantum
    - qubit
    - 量子计算
    - 量子比特
```

### 关键词匹配规则

- **大小写不敏感**：`AI` 和 `ai` 效果相同
- **词边界检测**：只匹配完整单词，避免子字符串误匹配
  - `AI` 会匹配 "AI technology"
  - `AI` 不会匹配 "training"（不包含独立的 "AI" 单词）

### 幂等性保证

- 路由器使用 URL 进行去重
- 重复运行不会重复添加相同内容
- 可以安全地定时运行（如每天一次）

---

## 🔄 集成建议

### 定时运行（GitHub Actions）

创建 `.github/workflows/topic-router.yml`：

```yaml
name: Topic Router

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点运行
  workflow_dispatch:  # 手动触发

jobs:
  route:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install pyyaml
      
      - name: Run Topic Router
        run: |
          cd topic-layer
          python router.py
      
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add topic-layer/index/
          git diff --staged --quiet || git commit -m "Update topic timelines"
          git push
```

### 本地定时运行（Cron）

**Linux/Mac：**

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点运行）
0 2 * * * cd /path/to/trendrader/topic-layer && python router.py
```

**Windows（任务计划程序）：**

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天凌晨 2 点
4. 操作：启动程序
   - 程序：`python`
   - 参数：`router.py`
   - 起始于：`C:\path\to\trendrader\topic-layer`

### Docker 集成

在 TrendRadar 的 Docker 容器中运行：

```bash
# 进入容器
docker exec -it trendradar /bin/bash

# 运行路由器
cd /app/topic-layer
python router.py
```

或在 `docker-compose.yml` 中添加定时任务：

```yaml
services:
  trendradar:
    # ... 现有配置
    command: >
      sh -c "
        python -m trendradar &&
        cd topic-layer &&
        python router.py
      "
```

---

## 📊 使用场景

### 个人知识管理

- **投资者**：追踪特定公司、行业、政策变化
- **研究者**：长期跟踪某个学术领域的进展
- **自媒体人**：收集素材，发现选题

### 团队协作

- **企业公关**：监控品牌舆情和行业动态
- **产品团队**：跟踪竞品和用户反馈
- **政策分析**：追踪政策变化和社会影响

### 学习与成长

- **技能学习**：追踪某个技术栈的最新发展
- **职业规划**：关注行业趋势和就业变化
- **兴趣爱好**：长期收集感兴趣的话题

---

## 🔧 技术细节

### 数据流程

```
1. TrendRadar 抓取新闻 → 存储到 output/news/*.db
2. Topic Router 读取数据库 → 提取 title, url, date, source
3. 关键词匹配 → 路由到对应主题
4. 去重检查 → 过滤已存在的 URL
5. 按日期分组 → 生成 Markdown 格式
6. 追加到 timeline.md → 最新的在上面
```

### 性能优化

- **增量更新**：只处理新的趋势，已存在的不重复添加
- **批量处理**：一次运行处理所有主题
- **轻量级**：只依赖 `pyyaml`，无需安装大型库

### 错误处理

- 数据库文件不存在 → 友好提示
- topics.yaml 格式错误 → 详细报错
- 网络中断/文件损坏 → 跳过并继续处理其他文件

---

## 🎯 设计原则

1. **不侵入原有系统**
   - 只读取 TrendRadar 输出，不修改其代码
   - 独立运行，互不干扰

2. **人类保留控制权**
   - 主题定义由人类编写（YAML）
   - AI 不参与长期记忆管理
   - 判断区留空，供人工补充

3. **文件系统保证持久性**
   - 所有数据存储在文件系统
   - Git 友好，易于版本控制
   - 无需数据库，简单可靠

4. **可扩展性**
   - 易于添加新主题
   - 可集成到各种自动化流程
   - 预留扩展接口（正则匹配、LLM 辅助等）

---

## 🚧 未来增强（可选）

这些功能不在本次实现范围内，但预留了扩展空间：

### 高级匹配

```yaml
ai_finance:
  keywords:
    - AI
    - /\b(machine|deep)\s+learning\b/  # 正则表达式支持
```

### LLM 辅助判断

```python
# 使用 LLM 评估相关性（而不是简单关键词匹配）
relevance_score = llm.judge_relevance(trend, topic)
if relevance_score > 0.7:
    add_to_timeline(trend)
```

### 导出功能

```bash
# 导出为 PDF 报告
python router.py --export pdf --topic ai_finance

# 导出为 HTML 网页
python router.py --export html --output ./reports
```

### 多语言支持

```yaml
ai_finance:
  name: 
    zh: AI 对金融体系的影响
    en: AI's Impact on Financial Systems
  keywords:
    zh: [人工智能, 金融]
    en: [AI, finance]
```

---

## 🙋 常见问题

### Q: 为什么没有找到 trends.json？

A: TrendRadar v4.0.0 之后使用 SQLite 数据库存储数据，不再生成 JSON 文件。Topic Layer 已适配新的存储格式，直接读取 `output/news/*.db` 文件。

### Q: 如何处理历史数据？

A: 首次运行时，路由器会处理所有已有的数据库文件。后续运行只会添加新的趋势（通过 URL 去重）。

### Q: 可以修改已生成的 timeline.md 吗？

A: 可以。timeline.md 是普通的 Markdown 文件，你可以：
- 手动编辑内容
- 删除不相关的条目
- 在"我的判断"区添加批注
- 重新组织结构

### Q: 关键词匹配不准确怎么办？

A: 当前版本使用简单的关键词匹配。未来可以：
- 使用正则表达式（更精确）
- 集成 LLM 辅助判断（更智能）
- 添加排除词（negative keywords）

### Q: 如何备份时间轴数据？

A: timeline.md 是纯文本文件，建议：
- 使用 Git 版本控制
- 定期备份整个 `index/` 目录
- 同步到云存储（Dropbox、OneDrive 等）

---

## 📄 许可证

本系统遵循 TrendRadar 的 GPL-3.0 许可证。

---

## 🙏 致谢

感谢 [TrendRadar](https://github.com/sansan0/TrendRadar) 项目提供的数据基础。

---

**Happy Tracking! 📈**
