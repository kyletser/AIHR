# OfferCatcher（Offer 捕手）—— 学生求职匹配智能体 设计方案

## 一、问题诊断

当前学生求职存在**三大断层**：

| 断层类型 | 具体表现 | 根因 |
|---------|---------|------|
| **信息断层** | 海量岗位中筛选匹配岗位耗时巨大，学生难以判断"我到底适合什么" | JD描述与学生自我认知之间存在语义鸿沟 |
| **表达断层** | 简历无法将真实能力转化为JD语言，常常"卖相不佳" | 学生不会用STAR法则量化成果，不会针对不同岗位定制简历 |
| **反馈断层** | 投递后石沉大海，不知道是简历问题还是能力问题 | 缺少"简历诊断→投递→反馈→优化"的迭代闭环 |

**核心论断**：学生不缺能力，缺的是"能力翻译"和"精准匹配"。

---

## 二、方案设计：五维设计

> 说明：原"五维创新"改为"五维设计"，措辞更严谨；以下内容均为可落地的设计，非营销表述。

### 设计1：JD基因解码器（Job DNA Decoder）★核心模块

**设计目标**：将非结构化的JD文本转化为结构化、可计算的数据，支撑后续所有匹配逻辑。

**四层递进式解析模型**（均有明确数据来源，避免LLM幻觉）：

| 层级 | 维度 | 数据来源 | LLM 作用 | 示例输出 |
|------|------|---------|----------|---------|
| **Layer 1** | 硬技能基因 Hard-skill DNA | JD原文明确列出的技能要求 | 提取 + 三级分类 | `Must: Python, MySQL / Plus: Docker, K8s / Nice-to-have: TiDB` |
| **Layer 2** | 软素质基因 Soft-skill DNA | JD原文中"沟通能力""抗压能力"等软素质描述 | 提取 + 重要度评级 | `沟通协作: 高 / 抗压能力: 中 / 领导力: 低（未提及）` |
| **Layer 3** | 团队文化基因 Culture DNA | JD用词风格（"快速迭代"→敏捷；"代码质量"→工程文化） | 从显式文本推断，输出附置信度 | `文化倾向: 敏捷开发(高置信度) / 扁平管理(中置信度)` **标注：此层为AI推断，仅供参考** |
| **Layer 4** | 匹配度诊断 Diagnosis | 将L1+L2与学生画像对比 | 差距分析 + 改进建议 | `缺失技能: Docker(可在2周内补全) / 简历表述建议: 项目经历缺少并发处理描述` |

**幻觉风险控制**：
- L1/L2：严格限定从JD原文提取，输出含 `source_text`（原文引用），可追溯
- L3：输出必须附带 `confidence` 字段（`high/medium/low`），前端对 `low` 置信度项做灰显+提示
- L4：基于L1/L2与学生画像的客观对比，不允许LLM编造学生没有的经历

**输出Schema**（供下游模块调用）：
```json
{
  "job_id": "jd_xxx",
  "hard_skills": {
    "must": [{"skill": "Python", "source_text": "熟练掌握Python"}],
    "plus": [{"skill": "Docker", "source_text": "有容器化经验优先"}],
    "nice": [{"skill": "TiDB"}]
  },
  "soft_skills": [
    {"skill": "沟通协作", "level": "high", "source_text": "良好的团队协作能力"}
  ],
  "culture_hints": [
    {"hint": "敏捷开发", "confidence": "high", "source_text": "快速迭代"}
  ],
  "parsed_at": "2026-05-29T14:00:00Z"
}
```

---

### 设计2：候选人能力画像（Candidate Profile）

**设计目标**：将非结构化简历转化为可计算的结构化画像，与JD基因解码输出对齐。

**简历解析流程**：
```
PDF/Word简历 → 文本提取（pdfplumber/python-docx）→ LLM结构化提取 → 标准化JSON画像
```

**画像Schema**：
```json
{
  "candidate_id": "cand_xxx",
  "basic": {
    "name": "（脱敏处理，仅存 initials）",
    "education": [{"school": "XX大学", "major": "计算机科学", "degree": "本科", "year": "2024"}],
    "graduation_year": 2024
  },
  "skills": {
    "hard_skills": [{"skill": "Python", "level": "proficient", "source": "项目经历"}],
    "soft_skills": [{"skill": "团队协作", "evidence": "社团负责人"}]
  },
  "projects": [
    {
      "name": "XX项目",
      "role": "后端开发",
      "duration": "2023.06-2023.12",
      "description_raw": "（原文）",
      "description_enhanced": "（LLM优化后的STAR表述）",
      "skills_used": ["Python", "MySQL"]
    }
  ],
  "parsed_at": "2026-05-29T14:00:00Z"
}
```

**隐私设计**：`name` 字段仅存储姓名首字母+姓氏拼音首字母，原始姓名不落库；简历原文文件在解析完成后可选删除（用户可配置保留期）。

---

### 设计3：能力匹配引擎（Matching Engine）

**设计目标**：将候选人画像与JD基因进行多维度匹配，输出可解释的结果，而非单一分数。

**匹配维度**（6维，与竞品只给单一匹配分数区分）：

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 硬技能匹配度 | 35% | Must技能命中率 + Plus技能加权 |
| 项目经验相关度 | 25% | 项目技能与JD技能的交集大小 + LLM语义相关度 |
| 教育背景匹配度 | 15% | 专业匹配 + 学历要求符合 |
| 软素质匹配度 | 15% | 简历中是否体现JD要求的软素质 |
| 行业/方向认知 | 5% | 项目/实习方向是否与JD一致 |
| 成长潜力 | 5% | 技能广度 + 学习轨迹（在校期间技能演进） |

**输出示例**：
```json
{
  "overall_score": 72,
  "dimensions": {
    "hard_skills": {"score": 80, "detail": "Must技能命中4/5，缺失Docker"},
    "projects": {"score": 75, "detail": "2个项目涉及后端开发，与JD匹配"},
    "education": {"score": 100, "detail": "计算机本科，符合学历要求"},
    "soft_skills": {"score": 60, "detail": "简历未体现'沟通能力'，建议在项目描述中补充"},
    "industry": {"score": 50, "detail": "无直接相关实习经历"},
    "growth": {"score": 70, "detail": "技能逐年丰富，有自学能力体现"}
  },
  "gap_analysis": [
    {"gap": "缺失Docker技能", "suggestion": "可在简历'技能'栏添加'了解Docker基础'，并在项目中补充容器化部署经历"},
    {"gap": "软素质未体现", "suggestion": "在社团/项目经历中加入团队协作的具体案例"}
  ]
}
```

---

### 设计4：简历优化引擎（Resume Optimization Engine）

**设计目标**：基于匹配结果，生成针对性优化建议，支持多版本管理。

**核心功能**：
1. **STAR重构**：将项目描述从"做了XX"重构为"背景-任务-行动-结果"结构化表述，量化成果
2. **针对性关键词注入**：根据JD的Must/Plus技能，在简历合适位置自然融入关键词（不生硬堆砌）
3. **多版本管理**：同一份简历可生成多个目标岗位版本，分别追踪优化历史
4. **修改溯源**：每一处修改标注原因（"对应JD要求：Docker容器化经验"）

**不使用LLM直接生成整份简历**（避免造假风险），而是：
- 对原有表述做STAR优化（保留事实真实性）
- 给出"建议补充方向"（由学生自行填写真实内容）
- 标注 `[AI建议]` 与 `[需本人确认]` 的边界

---

### 设计5：面试准备 + 反馈闭环（Interview Prep & Feedback Loop）

**面试准备模块**：
- 基于JD基因+L4诊断，生成该岗位的高频面试问题（技术+行为）
- 对每个预估薄弱点，提供"回答思路框架"（非标准答案，避免背题）
- 生成"自我推销话术"：基于匹配结果中最强的2-3个维度，设计差异化叙事

**反馈闭环设计**：
```
投递标记（学生手动标记投递状态）
    ↓
面试邀请 / 拒信 / 无回复（学生反馈结果）
    ↓
系统分析：该类岗位的匹配分阈值是多少？
    ↓
建议：该类岗位建议匹配分≥75再投递，当前平均通过分70
    ↓
学生根据建议调整简历 or 调整目标岗位范围
```

**数据看板指标**：
- 投递总数 / 面试转化率 / offer转化率
- 各维度平均得分趋势（是否在优化后提升）
- "高通过率岗位"的共性技能特征（用于反向指导技能学习方向）

---

## 三、AI工具选型与成本估算

| 组件 | 选型 | 理由 | 成本估算（仅供参考） |
|------|------|------|---------------------|
| **JD基因解码** | DeepSeek-V3 | 长文本理解强，支持结构化JSON输出；性价比高 | ~0.001元/次（JD约1000 tokens输入） |
| **简历解析** | DeepSeek-V3 + pdfplumber | 结构化提取稳定；pdfplumber处理中文PDF准确率可接受 | ~0.005元/次（简历约3000 tokens输入） |
| **匹配评分** | DeepSeek-V3 | 简历画像JSON + JD基因JSON直接输入LLM，输出6维评分+差距分析，无需Embedding模型 | ~0.004元/次（输入约2000 tokens） |
| **简历优化建议** | DeepSeek-V3 | 长文本生成可控，支持JSON格式输出修改建议 | ~0.008元/次（输出较长） |
| **前端框架** | React + TailwindCSS + Recharts | 雷达图/热力图可视化；Recharts比ECharts体积更小 | 免费（开源） |
| **数据库** | PostgreSQL | 存储结构化数据；无需向量检索，纯关系型即可满足 | 约30元/月（轻量云数据库） |

**单用户完整流程成本估算**（解析简历1次 + 解码JD3次 + 匹配3次 + 优化建议1次）：
≈ 0.001×3 + 0.005 + 0.004×3 + 0.008 ≈ **0.04元/用户**

---

## 四、系统架构设计

### 技术架构图

```
┌─────────────────────────────────────────────────────┐
│                     前端（React）                     │
│  简历上传页 → JD输入页 → 匹配结果页 → 优化建议页      │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────┐
│                 后端（FastAPI）                       │
│  /api/parse-resume  /api/decode-jd  /api/match      │
│  /api/optimize-resume  /api/track-application       │
└──────────┬───────────────────────────┬──────────────┘
           │                           │
┌──────────▼──────────┐   ┌───────────▼──────────────┐
│  LLM服务层           │   │  数据库层                 │
│  DeepSeek API调用    │   │  PostgreSQL              │
│  重试 / 限流 / 审计  │   │  用户表 / 简历表 / JD表   │
└─────────────────────┘   │  匹配记录表 / 投递跟踪表    │
                           └───────────────────────────┘
```

### 数据库设计

```sql
-- 用户表（最小必要信息，隐私优先）
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    subscription_tier VARCHAR(20) DEFAULT 'free'
);

-- 简历表（解析后的结构化数据，原始文件可选）
CREATE TABLE resumes (
    resume_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    profile_json JSONB,        -- 候选人画像Schema
    file_url VARCHAR(500),     -- 原始文件存储路径（可NULL，解析后删除）
    parsed_at TIMESTAMP,
    deleted_at TIMESTAMP       -- 软删除，满足数据遗忘权要求
);

-- JD表（用户粘贴/导入的岗位描述）
CREATE TABLE job_descriptions (
    jd_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    title VARCHAR(200),
    company VARCHAR(200),
    raw_text TEXT,
    dna_json JSONB,            -- JD基因解码Schema
    created_at TIMESTAMP DEFAULT NOW()
);

-- 匹配记录表
CREATE TABLE match_records (
    match_id UUID PRIMARY KEY,
    resume_id UUID REFERENCES resumes(resume_id),
    jd_id UUID REFERENCES job_descriptions(jd_id),
    match_result_json JSONB,    -- 匹配结果Schema
    created_at TIMESTAMP DEFAULT NOW()
);

-- 投递跟踪表（反馈闭环）
CREATE TABLE applications (
    app_id UUID PRIMARY KEY,
    match_id UUID REFERENCES match_records(match_id),
    status VARCHAR(20) CHECK (status IN ('pending','interview','offer','rejected')),
    feedback_text TEXT,        -- 用户填写的面试反馈/拒信原因
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 五、API接口设计

### 5.1 简历解析
```
POST /api/parse-resume
Body: multipart/form-data { file: .pdf/.docx, user_id }
Response: { resume_id, profile_json, parse_status }
Error: 400（文件格式不支持）/ 422（解析失败）
```

### 5.2 JD基因解码
```
POST /api/decode-jd
Body: { jd_text: string, user_id }
Response: { jd_id, dna_json, decode_status }
```

### 5.3 能力匹配
```
POST /api/match
Body: { resume_id, jd_id }
Response: { match_id, overall_score, dimensions, gap_analysis }
```

### 5.4 简历优化建议
```
POST /api/optimize-resume
Body: { resume_id, jd_id, match_result_json }
Response: { suggestions: [{ section, original, suggested, reason }] }
```

### 5.5 投递跟踪
```
POST /api/track-application
Body: { match_id, status, feedback_text }
Response: { app_id, tracked }
```

### 认证方案
MVP阶段：使用简单的 `user_id` 标识（demo无需登录）；
正式版：JWT + 邮箱验证，密码bcrypt加密存储。

---

## 六、工作流总览

```
学生上传简历
    ↓ LLM提取
候选人画像（结构化JSON，落库）
    ↓
学生输入/粘贴目标岗位JD
    ↓ JD基因解码（四层JSON，落库）
    ↓
能力匹配（6维评分 + 差距分析，可视化雷达图）
    ↓
┌───────────┼───────────────┐
↓           ↓                ↓
简历优化    面试准备        投递跟踪
建议生成    问题+思路框架    状态标记+数据看板
（多版本）  （定制化）      （持续迭代）
```

---

## 七、与竞品差异化分析

| 维度 | 传统方案（BOSS直聘/牛客/智联） | OfferCatcher |
|------|-------------------------------|-------------|
| 匹配方式 | 关键词/Tag匹配，或仅提供单一匹配百分比 | JD基因结构化解析 + 6维可解释匹配 |
| 简历优化 | 模板填充 或 仅做格式检查 | 基于目标JD的针对性优化建议 + 修改溯源 |
| 面试准备 | 通用题库，与岗位无关 | 基于JD基因定制的面试问题预测 |
| 反馈机制 | 投递后无反馈，或仅有"已读/未读" | 投递结果跟踪 + 个人转化率数据看板 |
| 可解释性 | 低（"匹配度85%"但不知道为什么） | 高（每个维度有具体分析文字） |

> 注：差异化对比基于各平台公开功能描述，实际功能以官方最新版本为准。

---

## 八、隐私与合规设计

| 风险点 | 应对措施 |
|--------|---------|
| 简历含姓名/手机号/身份证号等敏感信息 | 解析后立即脱敏；`users`表不存储明文手机号（hash存储）；原始文件可选不落库 |
| 用户要求删除数据（遗忘权） | `resumes.deleted_at` 软删除字段；定时任务物理删除超过30天的已删除记录 |
| LLM API传输数据安全 | DeepSeek等国内LLM服务，数据不出境；不与第三方海外API传输用户简历原文 |
| 学生用户年龄可能<18岁 | 注册时年龄确认；不主动收集未成年人额外信息 |

---

## 九、预期迭代计划

| 阶段 | 目标 | 关键交付 |
|------|------|---------|
| **Phase 1（当前）** | 核心匹配链路跑通 | 简历解析 + JD解码 + 6维匹配 + 基础优化建议 |
| **Phase 2** | 可解释性增强 | 修改溯源 + 多版本管理 + 雷达图可视化 |
| **Phase 3** | 反馈闭环 | 投递跟踪 + 数据看板 + 策略建议 |
| **Phase 4** | 规模化 | 多用户并发 + 岗位库（对接公开招聘API）+ 推荐算法 |

---

## 十、方案定位

**OfferCatcher 不是"又一个AI改简历工具"**，而是提出了**"JD结构化解码 → 可解释多维度匹配 → 针对性简历迭代 → 投递反馈闭环"**的完整求职匹配方法论。

核心差异化：**可解释性**（学生知道"为什么"匹配/不匹配）和**闭环**（系统从投递结果中持续学习，反向指导学生优化方向）。
