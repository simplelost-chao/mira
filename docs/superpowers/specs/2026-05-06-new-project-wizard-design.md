# New Project Wizard — Design Spec

**Date:** 2026-05-06  
**Status:** Approved  
**Feature:** 在 Mira 主页通过 AI 引导新建项目

---

## Overview

在 Mira 项目列表末尾添加虚线占位卡片，点击后跳转至 `/new` 专用页面，通过 4 步向导完成项目创建。AI 生成项目名称、命名寓意、Logo SVG，用户确认后 Mira 自动完成磁盘操作。

---

## Entry Point

主页项目列表（grid）末尾增加一张虚线占位卡片：

- 样式：虚线边框、半透明、中央 `+` 图标
- 点击：`window.location.href = '/new'`
- 位置：始终排在所有项目卡片之后，不参与筛选排序

---

## Pages & Routes

| Route | Handler | 说明 |
|---|---|---|
| `GET /new` | `new_project_page.py` | 渲染向导页 HTML |
| `POST /api/projects/brainstorm` | `main.py` | 调用 AI，返回 3 个方案 |
| `POST /api/projects/create` | `main.py` | 创建目录、文件、git init |

---

## 4-Step Wizard

### Step 1 — 描述想法

- 单行文本输入（`<textarea>` 限高，1-2 行视觉）
- placeholder：`"例：一个帮我追踪每天跑步数据的工具"`
- 模型选择器：动态读取 `vibe.yaml` 中已配置的 key，只展示可用模型
  - 检测字段：`deepseek_api_key`、`openrouter_api_key`、`doubao_api_key`、`gemini_api_key`、`anthropic_api_key`
- 按钮：「✦ 开始生成」→ 调用 `POST /api/projects/brainstorm`，显示 loading 状态

### Step 2 — AI 生成方案

AI 返回 3 个候选，每个卡片展示：

```
┌─────────────────────────────────────────┐
│  [Logo SVG 64×64]   名称  /读音/         │
│                     命名寓意（1-2句）     │
│                     ──────────────────── │
│                     Logo图形解读（1-2句） │
└─────────────────────────────────────────┘
```

- 无技术栈标签
- 点击卡片选中（高亮边框）
- 选中后「下一步」按钮激活

### Step 3 — 确认配置

可编辑字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| 项目名称 | ✓ | 预填 AI 推荐名，可修改 |
| 一句话描述 | ✓ | 预填 AI 生成，可修改 |
| 端口 | 选填 | 服务端口，留空则 vibe.yaml 不写 |
| 域名 | 选填 | 如 `xxx.zhuchao.life` |

### Step 4 — 创建

实时日志输出（流式 or 轮询），逐行显示：

```
✓ 创建目录 /Users/chao/Documents/Projects/stride
✓ 写入 vibe.yaml
✓ 生成 logo.svg
✓ 生成 favicon.svg（从 logo 派生）
✓ git init & 初始提交
✦ 完成！正在跳转...
```

完成后 2 秒自动跳转主页，新卡片出现。

---

## API Design

### POST /api/projects/brainstorm

**Request:**
```json
{
  "description": "追踪每天跑步数据并生成周报",
  "model": "deepseek"
}
```

**Response:**
```json
{
  "candidates": [
    {
      "name": "Stride",
      "phonetic": "/straɪd/",
      "name_meaning": "Stride 是跑步中「一大步」的意思，也有「稳步前进」的含义——不只记录数据，更象征每周积累的进步感。",
      "logo_svg": "<svg width=\"64\" height=\"64\">...</svg>",
      "logo_meaning": "圆形代表周期与循环（周报），内部对勾轨迹象征每次跑步的完成与打卡，绿→蓝渐变呼应从起点到终点的运动感。"
    }
  ]
}
```

**AI Prompt 结构（系统侧）：**

```
你是一个项目命名专家。用户描述了一个项目想法，请生成3个候选方案。
每个方案包含：
- name: 项目英文名（1个单词，简洁有力）
- phonetic: 国际音标
- name_meaning: 命名寓意（中文，1-2句，说清楚为什么取这个名字）
- logo_svg: 64×64 SVG，风格：深色背景友好，线条简洁，可用渐变色，不要文字
- logo_meaning: logo图形解读（中文，1-2句，说清楚每个元素代表什么）

返回合法 JSON 数组，不要其他内容。
```

### POST /api/projects/create

**Request:**
```json
{
  "name": "Stride",
  "description": "追踪跑步数据，每周生成训练报告",
  "logo_svg": "<svg>...</svg>",
  "port": 8090,
  "domain": ""
}
```

**Response:** `{"project_id": "stride", "path": "/Users/chao/Documents/Projects/stride"}`

**磁盘操作顺序：**
1. `mkdir /Users/chao/Documents/Projects/{project_id}`
2. 写 `vibe.yaml`（name、description、port、domain 按需写入）
3. 写 `logo.svg`（AI 返回原始 SVG）
4. 写 `favicon.svg`（将 logo SVG viewBox 缩为 32×32，去除细节装饰）
5. `git init && git add . && git commit -m "init: {name}"`

---

## File Templates

### vibe.yaml
```yaml
name: Stride
description: 追踪跑步数据，每周生成训练报告
# port: 8090        # 仅在用户填写时写入
# domain: xxx.life  # 仅在用户填写时写入
```

---

## UI Components

### 步骤指示器
- 4 个圆点 + 连接线，当前步骤绿色实心，已完成步骤绿色描边+对勾，未到步骤灰色
- 固定在页面顶部 topbar 下方

### 加载状态（Step 1 → Step 2）
- 按钮变为「生成中...」+ spinner
- 禁止重复提交

### 错误处理
- AI 调用失败：显示错误信息 + 「重试」按钮
- 目录已存在：Step 3 校验项目名，实时提示冲突

---

## Implementation Files

| 文件 | 操作 | 说明 |
|---|---|---|
| `vibe/new_project_page.py` | 新建 | 渲染向导页 HTML + JS |
| `vibe/main.py` | 修改 | 注册 3 个新路由 |
| `vibe/ai_brainstorm.py` | 新建 | AI 调用逻辑，支持多模型 |
| `static/index.html` | 修改 | 添加占位卡片 |

---

## Out of Scope

- 不生成项目代码骨架（只建目录和配置文件）
- 不自动推送 git remote
- 不支持模板选择（后续可扩展）
