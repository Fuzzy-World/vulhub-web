<p align="center">
  <h1 align="center">Vulhub-Web</h1>
  <p align="center">
    <strong>基于 Web 的漏洞靶场管理平台</strong>
    <br>
    零配置导入 · 一键启停 · 实时监控
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.115-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/docker-必需-blue.svg" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</p>

---

## 概述

**Vulhub-Web** 是一个轻量级的 Web 平台，用于管理 [Vulhub](https://github.com/vulhub/vulhub) 漏洞靶场。它原生适配 Vulhub 的目录结构，提供自动发现、按需构建、一键启停销毁、全生命周期管理——全部通过浏览器完成，无需手动敲 Docker 命令。

面向安全研究员、渗透测试工程师和安全教学人员。

### 核心功能

| 功能 | 说明 |
|------|------|
| **零配置导入** | 指定 Vulhub 根目录，自动扫描所有 `docker-compose.yml`，智能提取 CVE 编号和分类 |
| **一键启停** | Web UI 上完成构建、启动、停止、销毁，所有操作异步后台执行 |
| **实时日志** | SSE 推送容器标准输出，无需手动 `docker logs` |
| **Web 终端** | xterm.js + WebSocket，真正交互式 `docker exec -it` |
| **资源监控** | Docker 磁盘占用、镜像/容器数量、单容器 CPU/内存 |
| **智能调度** | 定时增量扫描新漏洞、自动清理 Docker 缓存、闲置靶机回收 |
| **30+ 分类** | 自动分类：log4j、shiro、fastjson、struts2、tomcat、weblogic、spring 等 |
| **深色主题** | 响应式 Bootstrap 5 单页应用，GitHub Dark 风格 |

---

## 快速开始

### 前置条件

- Python 3.9+
- Docker 和 Docker Compose（宿主机）
- [Vulhub](https://github.com/vulhub/vulhub) 仓库（独立 clone）

### 推荐目录结构

```
~/work/
├── vulhub/          ← git clone https://github.com/vulhub/vulhub
└── Vulhub-Web/      ← git clone https://github.com/Fuzzy-World/vulhub-web
```

### 本地运行

```bash
# 1. Clone Vulhub（漏洞环境仓库）
git clone https://github.com/vulhub/vulhub.git ~/work/vulhub

# 2. Clone Vulhub-Web（管理平台）
git clone https://github.com/Fuzzy-World/vulhub-web.git ~/work/Vulhub-Web
cd ~/work/Vulhub-Web

# 3. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动服务
python run.py
```

打开 `http://localhost:8088`，首次访问设置管理员密码，然后在「系统设置」中将「Vulhub 根目录」设为 `../vulhub`。

---

## 架构

```
┌─────────────────────────────────────────────┐
│                  浏览器                       │
│   Bootstrap 5 + xterm.js + SSE              │
└──────────────────┬──────────────────────────┘
                   │ HTTP / WebSocket / SSE
┌──────────────────▼──────────────────────────┐
│              FastAPI 服务端                   │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Routers │  │ Services │  │ Scheduler  │  │
│  │ (API)   │──│ (逻辑层)  │  │ (定时任务)  │  │
│  └─────────┘  └──────────┘  └────────────┘  │
│                     │                        │
│              ┌──────▼──────┐                 │
│              │   SQLite    │                 │
│              └─────────────┘                 │
└──────────────────┬──────────────────────────┘
                   │ Docker SDK / subprocess
┌──────────────────▼──────────────────────────┐
│              宿主机 Docker                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │ 靶机 1   │  │ 靶机 2   │  │ 靶机 N ...  │  │
│  └─────────┘  └─────────┘  └─────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 项目结构

```
Vulhub-Web/
├── app/                    # 应用包
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 全局配置
│   ├── database.py         # SQLite 初始化
│   ├── models.py           # ORM 模型（Vuln/Task/Config/Container）
│   ├── routers/            # API 路由层
│   │   ├── auth.py         # 认证接口 /api/auth/*
│   │   ├── vulns.py        # 漏洞库接口 /api/vulns/*
│   │   ├── ranges.py       # 靶场管理接口 /api/ranges/*
│   │   ├── docker.py       # Docker 监控接口 /api/docker/*
│   │   ├── settings.py     # 系统设置接口 /api/settings/*
│   │   └── tasks.py        # 任务记录接口 /api/tasks/*
│   └── services/           # 业务逻辑层
│       ├── auth_service.py      # JWT + bcrypt 认证
│       ├── vuln_service.py      # Vulhub 扫描解析
│       ├── range_service.py     # Docker Compose 生命周期
│       ├── docker_service.py    # Docker SDK 封装
│       └── scheduler_service.py # 定时任务调度
├── static/                 # 前端 SPA
│   ├── index.html          # 单页入口（含登录页、主界面、所有模态框）
│   ├── css/app.css         # 自定义样式（深色科技风）
│   └── js/
│       ├── api.js          # API 封装（Token 管理、27 个接口）
│       ├── app.js          # 主逻辑（页面切换、Toast、确认弹窗）
│       ├── vulns.js        # 漏洞库页面
│       ├── detail.js       # 详情页（README 渲染、日志 SSE）
│       ├── running.js      # 运行中靶机页面
│       ├── settings.js     # 设置页面
│       └── terminal.js     # Web 终端（xterm.js + WebSocket）
├── data/                   # 运行时数据库（自动生成，不入仓库）
├── run.py                  # 应用入口
├── requirements.txt
├── README.md               # 英文文档
├── README.zh-CN.md         # 中文文档（本文件）
├── LICENSE                 # MIT
├── CONTRIBUTING.md         # 贡献指南
├── CHANGELOG.md            # 更新日志
├── .env.example            # 环境变量模板
└── .gitignore
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/auth/status` | 检查是否已初始化管理员密码 |
| `POST` | `/api/auth/login` | 登录认证 |
| `POST` | `/api/auth/init` | 初始化管理员密码 |
| `GET` | `/api/vulns` | 漏洞列表（分页、分类/状态/关键词/年份筛选） |
| `POST` | `/api/vulns/scan` | 触发增量扫描 |
| `GET` | `/api/vulns/categories` | 获取分类列表及数量 |
| `GET` | `/api/vulns/{id}/readme` | 获取 README 渲染 HTML |
| `GET` | `/api/vulns/{id}/readme-assets/{path}` | README 静态资源（图片等） |
| `POST` | `/api/ranges/{id}/build` | 构建 Docker 镜像 |
| `POST` | `/api/ranges/{id}/start` | 启动靶场容器 |
| `POST` | `/api/ranges/{id}/stop` | 停止靶场 |
| `POST` | `/api/ranges/{id}/destroy` | 销毁靶场（可选同步删镜像） |
| `GET` | `/api/ranges/{id}/status` | 获取靶场状态和访问地址 |
| `GET` | `/api/ranges/{id}/logs` | 实时日志流（SSE） |
| `WS` | `/api/ranges/{id}/terminal` | Web 终端（WebSocket） |
| `GET` | `/api/ranges/running` | 所有运行中靶机列表 |
| `POST` | `/api/ranges/batch-destroy` | 批量销毁靶机 |
| `GET` | `/api/docker/info` | Docker 全局信息 |
| `POST` | `/api/docker/cleanup` | 清理 Docker 资源 |
| `GET/POST` | `/api/settings` | 系统配置读写 |
| `GET` | `/api/tasks` | 任务记录列表 |
| `GET` | `/api/tasks/{id}` | 任务详情（含日志） |

---

## 系统设置

所有配置通过 Web UI → 「系统设置」管理：

| 设置项 | 默认值 | 说明 |
|--------|--------|------|
| Vulhub 根目录 | (空) | Vulhub 仓库路径，支持相对路径（如 `../vulhub`） |
| 服务端口 | 8088 | HTTP 监听端口 |
| 闲置超时 | 0（禁用） | 靶机运行 N 小时后自动销毁 |
| 删除镜像 | 是 | 销毁靶场时同步删除 Docker 镜像 |
| 扫描 Cron | `0 */6 * * *` | 增量扫描调度 |
| 清理 Cron | `0 2 * * *` | Docker 缓存清理调度 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.9+, FastAPI, uvicorn |
| **数据库** | SQLite + SQLAlchemy ORM |
| **前端** | Bootstrap 5, jQuery, xterm.js, marked.js |
| **认证** | 自定义 JWT (HMAC-SHA256) + bcrypt |
| **实时通信** | SSE（日志推送）, WebSocket（终端） |
| **调度** | APScheduler (BackgroundScheduler) |
| **Docker 操作** | docker-py SDK + subprocess |

---

## 安全特性

- JWT 认证（72 小时过期），Cookie + Bearer Token 双模式
- bcrypt 密码哈希
- README 资源文件路径遍历防护
- 靶场启动前端口冲突检测
- 管理员独占所有管理接口

---

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT License — 见 [LICENSE](LICENSE)。

## 致谢

- [Vulhub](https://github.com/vulhub/vulhub) — 开源漏洞环境集合
- [FastAPI](https://fastapi.tiangolo.com/) — 现代化 Python Web 框架
- [xterm.js](https://xtermjs.org/) — 终端前端组件
