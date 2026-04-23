# test-framework Linux 部署说明

本文档基于当前项目源码结构整理，适用于在 Linux 服务器上部署和运行 `test-framework` 项目。

适用场景：

- Ubuntu 20.04 / 22.04
- Debian 11 / 12
- 其他兼容 `apt` 的 Linux 发行版

如果你使用的是 CentOS / Rocky / AlmaLinux，系统包安装命令需要自行替换为对应版本。

## 项目结构

```text
test-framework/
├─ backend/                 # FastAPI 后端
├─ frontend/                # Vue 3 + Vite 前端
├─ engine/                  # 执行引擎
├─ projects/                # 项目数据
├─ docs/
├─ requirements.txt         # 根目录 Python 依赖
├─ DEPLOY_WINDOWS.md
└─ DEPLOY_LINUX.md
```

## 环境要求

- Python 3.10 及以上
- Node.js 18 及以上
- npm 9 及以上
- 能联网安装 pip / npm / Playwright 依赖

## 部署方式说明

当前项目更适合采用“前后端分离 + nginx 反向代理”的方式部署：

- 后端运行在 `127.0.0.1:8000`
- 前端构建为静态文件，交给 `nginx` 提供服务
- `nginx` 统一代理 `/api` 到后端

不建议在 Linux 正式环境中长期使用 `npm run dev`。

## 第一步：安装系统依赖

以 Ubuntu / Debian 为例：

```bash
sudo apt update
sudo apt install -y \
  git \
  curl \
  wget \
  unzip \
  build-essential \
  python3 \
  python3-venv \
  python3-pip \
  nginx
```

## 第二步：安装 Node.js

如果系统默认 Node 版本太低，建议安装 Node.js 18+ 或 20+。

示例：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

验证版本：

```bash
python3 --version
node -v
npm -v
```

## 第三步：获取代码

```bash
git clone <your-repo-url>
cd test-framework
```

## 第四步：创建 Python 虚拟环境

建议在项目根目录或 `backend` 目录中创建虚拟环境。

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

## 第五步：安装后端依赖

项目 Python 依赖分为两部分：

- `backend/requirements.txt`
- 根目录 `requirements.txt`

另外，源码实际还依赖 `python-dotenv`。

在项目根目录执行：

```bash
cd /path/to/test-framework
python3 -m pip install -r backend/requirements.txt -r requirements.txt python-dotenv
```

如果你所在环境需要代理，请确保 `HTTP_PROXY` / `HTTPS_PROXY` 配置有效；如果代理失效，建议先清理环境变量后再安装。

## 第六步：安装 Playwright 浏览器和系统依赖

这是 Linux 部署里最容易踩坑的部分。

先安装 Chromium：

```bash
python3 -m playwright install chromium
```

再安装 Playwright 所需系统依赖：

```bash
python3 -m playwright install-deps chromium
```

如果 `install-deps` 不可用，可手动执行：

```bash
sudo apt update
sudo apt install -y \
  libnss3 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libcups2 \
  libdrm2 \
  libxkbcommon0 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libasound2 \
  libpango-1.0-0 \
  libcairo2 \
  libatspi2.0-0 \
  libx11-xcb1 \
  libxcursor1 \
  libxi6 \
  libxext6 \
  libglib2.0-0
```

## 第七步：安装前端依赖

```bash
cd /path/to/test-framework/frontend
npm install
```

## 第八步：构建前端

当前源码前端已经可以正常构建：

```bash
cd /path/to/test-framework/frontend
npm run build
```

构建产物目录：

- `frontend/dist`

## 第九步：启动后端

推荐直接使用 `uvicorn` 启动。

```bash
cd /path/to/test-framework/backend
source venv/bin/activate
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证健康检查：

```bash
curl http://127.0.0.1:8000/health
```

期望返回：

```json
{"status":"ok","version":"1.0.0"}
```

Swagger 地址：

- `http://127.0.0.1:8000/docs`

## 第十步：使用 nginx 托管前端并代理后端

创建 nginx 配置文件：

```bash
sudo vim /etc/nginx/sites-available/test-framework
```

参考配置：

```nginx
server {
    listen 80;
    server_name _;

    root /path/to/test-framework/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/test-framework /etc/nginx/sites-enabled/test-framework
sudo nginx -t
sudo systemctl reload nginx
```

之后访问：

- `http://<server-ip>/`

## 第十一步：配置 systemd 管理后端

建议把后端托管给 `systemd`。

创建服务文件：

```bash
sudo vim /etc/systemd/system/test-framework-backend.service
```

参考内容：

```ini
[Unit]
Description=test-framework backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/test-framework/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/path/to/test-framework/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable test-framework-backend
sudo systemctl start test-framework-backend
sudo systemctl status test-framework-backend
```

查看日志：

```bash
journalctl -u test-framework-backend -f
```

## 数据库说明

项目当前默认使用 SQLite。

本地或测试环境通常可以直接使用；如果是正式生产环境，建议评估是否切换到 MySQL 或 PostgreSQL，原因包括：

- 多任务并发时稳定性更好
- 更适合长期运行
- 便于备份和运维

## 配置与安全建议

部署到服务器前，建议重点检查：

- `.env` 中是否包含敏感信息
- webhook、API key 是否应改为环境变量注入
- CORS 是否仍为 `*`
- 是否需要限制管理后台访问来源

当前源码里后端允许所有来源跨域，这适合开发阶段，不建议直接用于公网生产环境。

## 验证清单

部署完成后，建议至少验证以下内容：

### 1. 后端服务正常

```bash
curl http://127.0.0.1:8000/health
```

### 2. 前端首页正常

浏览器访问：

- `http://<server-ip>/`

### 3. 前后端联通正常

```bash
curl http://127.0.0.1/api/v1/projects
```

或者直接访问：

- `http://<server-ip>/api/v1/projects`

返回 `[]` 或 JSON 数据即可。

### 4. Playwright 运行能力正常

可在虚拟环境中做一个最小验证：

```bash
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
PY
```

## 常见问题

### 1. 后端启动失败，提示缺少模块

请确认已安装：

```bash
python3 -m pip install -r backend/requirements.txt -r requirements.txt python-dotenv
```

### 2. Playwright 启动浏览器失败

大概率是 Linux 系统依赖不完整，请优先执行：

```bash
python3 -m playwright install chromium
python3 -m playwright install-deps chromium
```

### 3. nginx 返回 502

通常说明后端没起来，或者 nginx 代理地址不对。

优先检查：

```bash
curl http://127.0.0.1:8000/health
sudo systemctl status test-framework-backend
```

### 4. 前端页面打开正常，但接口 404 或超时

请检查：

- nginx 是否正确代理 `/api/`
- 后端是否绑定到 `127.0.0.1:8000`
- 前端是否已经执行过 `npm run build`

### 5. 服务端口冲突

检查端口：

```bash
ss -lntp | grep 8000
ss -lntp | grep 80
```

## 部署建议总结

如果只是开发/测试环境：

- 后端用 `uvicorn`
- 前端直接 `npm run dev`

如果是服务器长期运行：

- 后端用 `systemd`
- 前端用 `npm run build + nginx`
- 结合日志、备份、数据库升级做进一步治理

## 当前源码部署注意点

基于当前项目源码，部署时需要特别注意以下几点：

- 前端开发端口实际是 `3000`
- 后端源码实际依赖 `python-dotenv`
- 更推荐直接使用 `uvicorn` 启动，而不是 `backend/run.py`
- 生产环境建议不要直接使用 Vite 开发服务器对外提供服务
