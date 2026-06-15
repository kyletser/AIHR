# OfferCatcher — AI 求职匹配智能体

> 腾讯 AIHR 训练营项目 | 面向学生的智能求职匹配系统

## 项目简介

OfferCatcher 是一个 AI 驱动的求职匹配平台，帮助学生快速评估自己与目标岗位的匹配度，并获得有针对性的简历优化建议。

**核心能力：**
- 📄 上传简历 PDF/DOCX，自动提取文本
- 🧬 JD 基因解码 — 提取岗位关键技能和软素质要求
- 🎯 **可靠匹配引擎** — LLM提取 → 代码验证 → 确定性评分 → LLM文案，杜绝幻觉
- 📊 6 维雷达评分 + 差距分析 + 简历优化建议
- 🗂 多用户支持 + 历史分析记录持久化
- 💬 求职智能体 — 目标规划、追问、对话、投递反馈

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Vue 3 前端 (Vite)                      │
│  Login / Dashboard / MatchAnalysis / History             │
├─────────────────────────────────────────────────────────┤
│                    REST API (FastAPI)                    │
│  /api/login  /api/analyze-v2  /api/match-history ...    │
├─────────────────────────────────────────────────────────┤
│                  可靠匹配引擎 (V2)                        │
│  ① LLM 提取    ② 代码验证    ③ 代码评分    ④ LLM 文案    │
│  (extractor)    (verifier)     (scorer)     (narrator)   │
├─────────────────────────────────────────────────────────┤
│                   SQLite 数据库                           │
│  users / resumes / jds / match_records / versions        │
└─────────────────────────────────────────────────────────┘
```

### 6 维评分引擎

| 维度 | 权重 | 评分逻辑 |
|------|------|---------|
| **硬技能** | 35% | 70+ 技能同义词匹配 + 可迁移技能检测 |
| **项目经历** | 25% | 项目与 JD 技能/领域重叠度 |
| **学历** | 15% | 学位等级与岗位要求对比 |
| **软素质** | 15% | 11 类软素质信号关键词匹配 |
| **行业认知** | 5% | 13 个职业领域关键词匹配 |
| **成长潜力** | 5% | 竞赛获奖 + 技能广度 + 证书 |

### 投递策略

| 总分 | 策略 | 说明 |
|------|------|------|
| ≥ 82 | 优先投递 | 匹配度强，重点打磨简历表达 |
| ≥ 68 | 优化后投递 | 补强 1-2 个证据点后投递 |
| ≥ 55 | 谨慎投递 | 适合冲刺，建议先补短板 |
| < 55 | 暂缓投递 | 差距较大，先换更贴合岗位 |

## 项目结构

```
AIHR/
├── backend/
│   ├── main.py              # FastAPI 入口（JWT认证、API路由、SPA服务）
│   ├── config.py             # LLM Provider 配置（DeepSeek/Zhipu/SiliconFlow）
│   ├── database.py           # SQLAlchemy + SQLite
│   ├── .env                  # 环境变量（不提交）
│   ├── requirements.txt
│   ├── models/
│   │   ├── db_models.py      # ORM 模型（User/Resume/JD/MatchRecord/ResumeVersion）
│   │   └── schemas.py        # Pydantic 模型
│   └── services/
│       ├── llm_client.py     # LLM API 客户端（httpx 直连）
│       ├── extractor.py      # ① 结构化提取
│       ├── verifier.py       # ② 反向验证
│       ├── scorer.py         # ③ 确定性评分（核心 506 行）
│       ├── narrator.py       # ④ 文案生成
│       └── career_agent.py   # 求职智能体
├── frontend-vue/
│   └── src/
│       ├── views/            # DashboardView, LoginView, RegisterView, MatchAnalysisView
│       ├── stores/auth.js    # Pinia 认证状态
│       └── router/index.js   # Vue Router
└── README.md
```

## 快速开始

### 本地开发

```bash
# 后端
cd backend
cp .env.example .env          # 编辑填入 LLM API Key
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8080

# 前端
cd frontend-vue
npm install
npm run dev                    # 访问 http://localhost:3000
```

### 生产部署

```bash
cd frontend-vue && npm run build
cp -r dist/* ../backend/static/
cd ../backend
nohup venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8088 &
```

## LLM Provider 配置

在 `backend/.env` 中设置，支持三种 Provider：

```env
LLM_PROVIDER=deepseek          # deepseek / zhipu / siliconflow
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_MODEL=deepseek-chat
```

## 技术亮点

1. **幻觉控制**：LLM 提取结果经代码反向验证，每个技能/项目必须在原文中找到证据，否则剔除
2. **确定性评分**：纯代码计算 6 维分数，同一输入永远同一输出
3. **全行业覆盖**：13 个职业领域 + 70+ 技能同义词，从程序员到会计师均可匹配
4. **投递策略**：不只是给分，还输出风险雷达、学习冲刺计划和简历聚焦建议

## 管理账号

默认管理员：`admin` / `admin`

## License

MIT
