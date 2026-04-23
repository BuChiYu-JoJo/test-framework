# test-framework 通用测试框架

**目录结构**
```
test-framework/
├── backend/               # Python FastAPI 后端
│   ├── app/
│   │   ├── api/v1/        # API 路由
│   │   ├── models/        # 数据模型
│   │   ├── schemas/       # Pydantic 模型
│   │   ├── services/      # 核心业务逻辑
│   │   └── core/          # 核心配置、数据库
│   ├── main.py
│   └── requirements.txt
├── frontend/              # Vue3 前端
│   ├── src/
│   │   ├── api/           # API 调用
│   │   ├── stores/        # Pinia 状态管理
│   │   ├── views/         # 页面组件
│   │   └── router/        # 路由
│   ├── dist/              # 构建产物（已编译）
│   ├── package.json
│   └── vite.config.js
└── docs/                  # 文档
    └── L1_excel_user_guide.md
```

---

## Windows 部署指南（前后端分离）

### 环境要求
- Python 3.9+
- Node.js 18+（用于前端开发模式）
- npm 或 yarn

---

### 第一步：拉取代码

```bash
git clone https://github.com/BuChiYu-JoJo/test-framework.git
cd test-framework
```

---

### 第二步：后端部署

```bash
cd test-framework/backend

# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**安装 Playwright 浏览器引擎：**
```bash
playwright install chromium
```

**启动后端服务：**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证后端是否启动成功：
```
浏览器访问 http://localhost:8000/health
应返回：{"status":"ok","version":"1.0.0"}
```

---

### 第三步：前端部署（开发模式）

```bash
cd test-framework/frontend

# 安装依赖
npm install

# 启动开发服务器（会自动代理 /api/* 到后端）
npm run dev
```

访问 `http://localhost:5173` 即可使用。

---

### 第四步：前端部署（生产模式）

不需要 Node.js，直接用后端服务静态文件：

**方式 A：Nginx 部署（推荐）**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/test-framework/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**方式 B：FastAPI 直接托管静态文件**

修改 `backend/app/main.py`，添加静态文件路由：

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="../frontend/dist"), name="static")

@app.get("/")
def read_root():
    return FileResponse("../frontend/dist/index.html")
```

---

### 第五步：初始化数据库

首次启动时，SQLite 数据库会自动创建（`test_framework.db`）。

如果需要重置数据库，删除 `backend/test_framework.db`，重启后端会自动重建。

---

## 模块说明

| 模块 | 端口 | 说明 |
|------|------|------|
| 后端 API | `:8000` | FastAPI 服务 |
| 前端开发 | `:5173` | Vite 热更新开发服务器 |
| 前端生产 | Nginx/静态托管 | 构建产物在 `frontend/dist` |

---

## 常见问题

### Q：Playwright 浏览器下载失败？
```bash
# 设置国内镜像
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors
playwright install chromium
```

### Q：后端启动报 `Port 8000 is in use`？
```bash
# Windows 查找并杀死占用端口的进程
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F
```

### Q：前端 `npm install` 失败？
```bash
# 使用淘宝镜像
npm config set registry https://registry.npmmirrors.org
npm install
```

### Q：如何指定数据库路径？
修改 `backend/app/core/config.py` 中的 `db_url` 配置。

---

## 开发相关

**启动后端（开发模式，自动重载）：**
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**重新构建前端：**
```bash
cd frontend
npm run build
```

**提交代码：**
```bash
git add .
git commit -m "your message"
git push origin main
```
