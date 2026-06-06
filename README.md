# 对话评测系统

美团外卖客服对话评测系统，用于评估 AI 客服在不同用户性格场景下的对话表现。

## 项目结构

```
meituan-hackthon/
├── backend/                    # 后端 (FastAPI)
│   ├── main.py                 # 快速测试后端入口
│   ├── config.py               # 配置文件
│   ├── simulators/             # 用户模拟器
│   ├── dialogue/               # 对话运行器
│   ├── evaluator/              # 评估器
│   ├── models/                 # LLM 客户端
│   ├── routes/                 # API 路由
│   ├── prompts/                # 提示词目录
│   ├── outputs/                # 输出目录
│   └── schemas/                # Pydantic 模型
├── frontend/                   # 前端 (Vue 3)
│   ├── src/
│   │   ├── components/         # 公共组件
│   │   ├── views/              # 页面视图
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── services/           # API 服务
│   │   ├── types/              # TypeScript 类型
│   │   └── router/             # 路由配置
│   └── package.json
├── .env                        # 环境变量配置文件
├── requirements.txt            # Python 依赖
└── README.md
```

## 环境配置

### 后端环境

```bash
# 1. 克隆代码
git clone https://github.com/wangzg03/meituan-hackthon.git
cd meituan-hackthon

# 2. 创建 Python 虚拟环境
python -m venv venv
source venv/bin/activate        # Linux/Mac
# 或 venv\Scripts\activate       # Windows

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 配置环境变量
# 创建 .env 文件
# 配置BASE_URL，API_KEY，MODEL_NAME，TEMPERATURE，MAX_TOKENS，MAX_DIALOGUE_TURNS，EVALUATION_ROUNDS，REQUEST_INTERVAL，MAX_RETRIES
```

### 配置前端环境

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装 Node.js 依赖
npm install

# 3. 确保 vite 配置正确（vite.config.ts）
```

## 运行项目

### 启动后端 API 服务

```bash
# 激活虚拟环境
source venv/bin/activate        # Linux/Mac
# 或 venv\Scripts\activate       # Windows

# 启动 FastAPI 服务
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

API 文档地址: http://localhost:8001/docs

### 启动前端开发服务

```bash
cd frontend
npm run dev
```

前端交互页面地址: http://localhost:5173

### 命令行模式

后端提供了两种运行方式：API 服务模式和命令行直接调用模式。

#### 1. 命令行直接调用（推荐用于快速测试）

```bash
source venv/bin/activate
cd backend

# 评测外卖配送场景（使用 EvaluationPipeline）
python main.py --scenario delivery --use-pipeline

# 评测课程平台场景（使用 EvaluationPipeline）
python main.py --scenario course --use-pipeline

# 评测所有场景
python main.py --scenario all

# 使用 legacy 模式（原始 Evaluator 评估方式）
python main.py --scenario delivery --legacy
```

**参数说明：**
- `--scenario`: 选择评测场景，可选值：`delivery`（外卖配送）、`course`（课程平台）、`all`（两者都跑）
- `--use-pipeline`: 使用新的 EvaluationPipeline 评估方式（默认启用）
- `--legacy`: 使用原有的 Evaluator 评估方式

#### 2. 运行完整系统（前端 + 后端）

```bash
# 启动后端 API 服务
source venv/bin/activate
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8001

# 启动前端（新开终端）
cd frontend
npm run dev
```

## 功能特性

- **首页**: 系统介绍
- **测评页面**: 创建测评任务，实时查看对话过程和评估结果
- **记录页**: 查询历史测评记录，支持按任务名称和场景类型搜索
