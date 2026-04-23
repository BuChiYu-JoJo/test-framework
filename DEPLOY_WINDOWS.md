# test-framework Windows 部署说明

本文档基于当前项目源码和本地 Windows 环境的实际验证结果整理，适用于在 Windows 上部署和运行 `test-framework` 项目。

## 目录结构

```text
test-framework/
├─ backend/                 # FastAPI 后端
│  ├─ app/
│  │  ├─ api/v1/            # API 路由
│  │  ├─ core/              # 配置、数据库
│  │  ├─ models/            # 数据模型
│  │  ├─ schemas/           # Pydantic 模型
│  │  └─ services/          # 业务服务
│  ├─ requirements.txt
│  └─ run.py
├─ frontend/                # Vue 3 + Vite 前端
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.js
├─ engine/                  # 执行引擎
├─ projects/                # 项目数据目录
├─ docs/
├─ requirements.txt         # 根目录 Python 依赖
└─ DEPLOY_WINDOWS.md
```

## 环境要求

- Windows 10/11
- Python 3.10 及以上
- Node.js 18 及以上
- npm 9 及以上
- 可联网安装 Python/npm 依赖

## 已验证可运行的本地环境

以下环境已实际验证可启动：

- Python `3.10.0`
- Node.js `v24.14.0`
- npm `11.9.0`
- Playwright Chromium 已安装并可正常启动

## 部署前说明

项目采用前后端分离模式：

- 后端默认监听：`http://127.0.0.1:8000`
- 前端开发服务默认监听：`http://127.0.0.1:3000`

注意：

- 当前源码中前端开发端口是 `3000`，不是 `5173`
- 后端源码依赖 `python-dotenv`，安装依赖时需要一并安装
- 首次运行需要安装 Playwright 浏览器

## 第一步：获取代码

如果你已经拿到项目目录，可跳过此步骤。

```powershell
git clone <your-repo-url>
cd test-framework
```

## 第二步：准备 Python 环境

建议在 `backend` 目录下创建虚拟环境。

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

如果不使用虚拟环境，也可以直接使用系统 Python，但不推荐。

## 第三步：安装后端依赖

项目后端依赖分散在两个文件中：

- `backend/requirements.txt`
- 根目录 `requirements.txt`

此外，还需要额外安装 `python-dotenv`。

在项目根目录执行：

```powershell
cd E:\develope\codex\program\test-framework
python -m pip install -r backend\requirements.txt -r requirements.txt python-dotenv
```

如果你的系统配置了无效代理，导致 `pip install` 失败，可先临时清空代理环境变量后再安装：

```powershell
$env:HTTP_PROXY=''
$env:HTTPS_PROXY=''
$env:ALL_PROXY=''
$env:http_proxy=''
$env:https_proxy=''
$env:all_proxy=''
$env:NO_PROXY='*'
$env:no_proxy='*'
python -m pip install -r backend\requirements.txt -r requirements.txt python-dotenv
```

## 第四步：安装 Playwright 浏览器

后端的部分能力依赖 Playwright，需要安装 Chromium。

```powershell
playwright install chromium
```

如果 `playwright` 命令不可用，也可以使用：

```powershell
python -m playwright install chromium
```

## 第五步：安装前端依赖

进入前端目录安装 npm 依赖：

```powershell
cd E:\develope\codex\program\test-framework\frontend
npm install
```

如果 npm 下载较慢，可切换镜像：

```powershell
npm config set registry https://registry.npmmirrors.org
npm install
```

## 第六步：启动后端

推荐直接使用 `uvicorn` 启动，而不是使用 `backend/run.py`。

原因：

- `backend/run.py` 中的 `reload=args.reload or True` 会导致始终开启热重载
- 本地调试问题不大，但不适合作为更稳定的启动方式

在 `backend` 目录执行：

```powershell
cd E:\develope\codex\program\test-framework\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动成功后，可访问：

- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Swagger 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

健康检查的期望返回值：

```json
{"status":"ok","version":"1.0.0"}
```

## 第七步：启动前端开发服务

在 `frontend` 目录执行：

```powershell
cd E:\develope\codex\program\test-framework\frontend
npm run dev -- --host 127.0.0.1
```

前端启动成功后，访问：

- 前端首页：[http://127.0.0.1:3000](http://127.0.0.1:3000)

当前前端通过 Vite 代理把 `/api` 请求转发到后端 `http://127.0.0.1:8000`。

对应配置见：

- [frontend/vite.config.js](E:\develope\codex\program\test-framework\frontend\vite.config.js)

## 第八步：验证系统是否正常

建议至少完成以下验证：

### 1. 后端健康检查

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

### 2. 前端首页能正常打开

浏览器访问：

- [http://127.0.0.1:3000](http://127.0.0.1:3000)

页面应能看到以下主要菜单：

- 用例管理
- 项目管理
- Locators
- 执行中心
- 报告中心
- 定时任务
- 系统设置
- AI 工具
- 性能检测
- 接口检测
- SEO 检测

### 3. 前端代理接口访问正常

可直接访问一个 API 验证代理联通：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/api/v1/projects
```

如果返回 `[]` 或项目列表 JSON，说明前后端联通正常。

## 第九步：前端生产构建

如果需要验证前端构建产物，可在 `frontend` 目录执行：

```powershell
cd E:\develope\codex\program\test-framework\frontend
npm run build
```

构建成功后产物位于：

- `frontend/dist`

## 数据库说明

项目默认使用 SQLite，本地首次启动时会自动创建数据库文件。

如需重置数据库，可删除后端目录中的 SQLite 文件后重新启动服务。

删除前请确认数据是否需要保留。

## 运行方式建议

### 本地开发

推荐同时开启两个终端：

终端 1：

```powershell
cd E:\develope\codex\program\test-framework\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

终端 2：

```powershell
cd E:\develope\codex\program\test-framework\frontend
npm run dev -- --host 127.0.0.1
```

### 简单测试环境

可以先保持上述运行方式，确认业务流程可用后，再考虑增加：

- 进程守护
- 反向代理
- 生产环境配置分离

## 生产部署建议

当前项目更适合先用于开发和测试环境。若要部署到正式环境，建议补充以下能力：

- 使用 `nginx` 或其他反向代理统一对外暴露服务
- 通过 `systemd`、`supervisor`、`pm2` 或容器方式管理进程
- 区分开发、测试、生产环境变量
- 清理和外置敏感配置
- 评估是否继续使用 SQLite，或切换为 MySQL/PostgreSQL

## 常见问题

### 1. `pip install` 失败，提示代理连接错误

通常是系统代理或环境变量代理配置无效。

可先清空代理环境变量后重试：

```powershell
$env:HTTP_PROXY=''
$env:HTTPS_PROXY=''
$env:ALL_PROXY=''
$env:http_proxy=''
$env:https_proxy=''
$env:all_proxy=''
$env:NO_PROXY='*'
$env:no_proxy='*'
```

然后重新执行安装命令。

### 2. 后端启动时报缺少模块

通常是 Python 依赖没有装全。请确认已执行：

```powershell
python -m pip install -r backend\requirements.txt -r requirements.txt python-dotenv
```

### 3. `playwright install chromium` 失败

可尝试使用镜像：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST='https://npmmirror.com/mirrors/playwright'
playwright install chromium
```

### 4. 8000 或 3000 端口被占用

可查看占用端口的进程：

```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :3000
```

结束指定进程：

```powershell
taskkill /PID <PID> /F
```

### 5. 前端能打开，但接口报错

请优先检查：

- 后端 `http://127.0.0.1:8000/health` 是否正常
- 前端代理配置是否仍指向 `127.0.0.1:8000`
- 后端是否有启动报错

## 本次实际验证结果

在当前 Windows 环境中，以下结果已经验证通过：

- 后端依赖安装成功
- 前端依赖安装成功
- Playwright Chromium 可用
- 后端健康检查正常
- 前端首页可访问
- 前端代理后端接口正常
- `npm run build` 构建成功

因此，当前项目可以在 Windows 本地成功部署并运行。
