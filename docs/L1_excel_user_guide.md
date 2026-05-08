# L1 Excel 用例格式 — 用户手册

## 概述

L1 格式是为了让**完全不懂代码的人**也能编写自动化用例。通过填写 Excel 表格，零门槛上手。

---

## 快速开始

1. 下载模板：[`cases/excel/用例模板_v1.0.xlsx`](cases/excel/用例模板_v1.0.xlsx)
2. 打开 Excel，按格式填写用例
3. 保存后通过 Web 管理平台上传

---

## Excel 格式说明

### 列定义

| 列名 | 说明 | 示例 |
|------|------|------|
| **用例ID** | 用例唯一标识，相同ID的多行=同一个用例 | `TC001` |
| **用例名称** | 用例描述，仅第1行填写 | `登录成功` |
| **模块** | 所属模块/页面，仅第1行填写 | `login`、`task_list` |
| **优先级** | P0(冒烟)/P1(核心)/P2(普通)/P3(低)，仅第1行填写 | `P0` |
| **操作类型** | 关键字，见下方对照表 | `导航`、`点击`、`输入` |
| **目标元素** | locator key（在 locators.json 中定义） | `login.username`、`task.submit` |
| **输入值** | 操作的具体值，变量或固定内容 | `15251686234`、`${USERNAME}` |
| **预期结果** | 用例执行后期望的验证点 | `URL包含 /dashboard/` |
| **备注** | 可留空；填写 `[setup]` 表示前置步骤，`[teardown]` 表示后置步骤 | `[setup]` |

### 多行 = 一个用例

同一个 `用例ID` 的多行按**从上到下**顺序执行，组成完整用例。

```
TC001 | 登录-正确账号密码 | login | P0 | 导航     | /login/           |              | URL包含 /login/     |
TC001 |                  |       |    | 点击     | login.tab_password |              |                    |
TC001 |                  |       |    | 输入     | login.username     | 15251686234  |                    |
TC001 |                  |       |    | 输入     | login.password     | Zxs6412915@+ |                    |
TC001 |                  |       |    | 勾选     | login.agree_terms  |              |                    |
TC001 |                  |       |    | 点击     | login.submit       |              | URL包含 /dashboard/ |
```

上方 6 行 = 1 个完整登录用例。

### 步骤类型（通过备注标记）

| 备注 | 含义 | 执行时机 |
|------|------|---------|
| （空） | 普通步骤 | 正常执行 |
| `[setup]` | 前置步骤 | 用例最开始执行（适合清除cookie、登录等初始化） |
| `[teardown]` | 后置步骤 | 用例最后执行（适合登出、清理数据） |

**示例：带前置/后置的用例**

```
TC002 | 创建任务   | task | P1 | 清除cookie |              |             |                   | [setup]
TC002 |            |      |    | 导航       | /tasks/create |             |                   |
TC002 |            |      |    | 输入       | task.name     | 测试任务     |                   |
TC002 |            |      |    | 点击       | task.submit   |             | 元素可见 .success |
TC002 |            |      |    | 登出       |              |             |                   | [teardown]
```

执行顺序：`清除cookie` → `导航` → `输入` → `点击` → `登出`

---

## 操作类型对照表

### 页面操作

| 中文 | 英文关键字 | 参数 |
|------|-----------|------|
| 导航 | `navigate` | target: URL 或相对路径 |
| 点击 | `click` | target: locator key |
| 双击 | `dblclick` | target: locator key |
| 右键 | `rightclick` | target: locator key |
| 输入 | `type` | target: locator key, value: 文本内容 |
| 清空 | `clear` | target: locator key |
| 选择 | `select` | target: locator key, value: 选项值 |
| 勾选 | `check` | target: locator key |
| 取消勾选 | `uncheck` | target: locator key |
| 悬停 | `hover` | target: locator key |
| 上传 | `upload` | target: locator key, value: 文件路径 |

### 等待

| 中文 | 英文关键字 | 参数 |
|------|-----------|------|
| 等待 | `wait` | value: 秒数 |
| 等待元素 | `wait_for` | target: locator key, value: `visible` / `hidden` |
| 等待URL | `wait_for_url` | value: URL模式（支持 contains） |

### 断言

| 中文 | 英文关键字 | 参数 |
|------|-----------|------|
| 断言文本 | `assert_text` | target: locator key, value: 期望包含的文本 |
| 断言可见 | `assert_visible` | target: locator key |
| 断言隐藏 | `assert_hidden` | target: locator key |
| 断言URL | `assert_url` | value: URL包含的字符串 |
| 断言数量 | `assert_count` | target: locator key, value: 比较表达式如 `>0`、`==3` |

### 浏览器

| 中文 | 英文关键字 | 参数 |
|------|-----------|------|
| 刷新 | `refresh` | — |
| 后退 | `back` | — |
| 前进 | `forward` | — |
| 截图 | `screenshot` | value: 图片命名 |
| 滚动 | `scroll` | value: `up` / `down` / `像素值` |
| 执行JS | `execute_js` | value: JS代码 |

### API

| 中文 | 英文关键字 | 参数 |
|------|-----------|------|
| API请求 | `api_request` | value: `METHOD@URL@Data` 如 `POST@/api/task@{"name":"test"}` |

### 特殊（仅限 setup/teardown）

| 中文 | 英文关键字 | 说明 |
|------|-----------|------|
| 清除cookie | `clear_browser_cookies` | 清除浏览器 Cookie，[setup] 专用 |
| 登出 | `logout` | 执行登出操作，[teardown] 专用 |

---

## 预期结果格式

| 格式 | 含义 | 示例 |
|------|------|------|
| `URL包含 xxx` | 验证当前 URL 包含指定字符串 | `URL包含 /dashboard/` |
| `元素可见 xxx` | 验证指定元素可见 | `元素可见 .success-msg` |
| `元素不可见 xxx` | 验证指定元素不存在或隐藏 | `元素不可见 .loading` |
| `文本包含 xxx` | 验证元素文本包含指定内容 | `文本包含 提交成功` |
| `状态 = xxx` | 验证 API 响应状态 | `状态 = 200` |

预期结果**不是必填**——如果不填，则只验证步骤执行，不做额外断言。

---

## 变量引用

输入值中可以使用变量，格式为 `${VAR_NAME}`：

```
${USERNAME}   → 从测试数据中获取
${PASSWORD}
${task_id}    → 从前序步骤结果中获取
${timestamp}  → 自动替换为当前时间戳
```

具体变量内容需要在 Web 管理平台的「测试数据」中配置。

---

## 完整示例

### 示例：登录 + 创建任务

```
用例ID  | 用例名称       | 模块  | 优先级 | 操作类型  | 目标元素           | 输入值                  | 预期结果                 | 备注
--------|---------------|-------|--------|----------|-------------------|------------------------|-------------------------|-----
TC001   | 登录-正确账号   | login | P0    | 导航      | /dashboard/login/ |                        | URL包含 /login          |
TC001   |               |       |        | 点击      | login.tab_password |                        |                          |
TC001   |               |       |        | 输入      | login.username     | 15251686234            |                          |
TC001   |               |       |        | 输入      | login.password     | Zxs6412915@+           |                          |
TC001   |               |       |        | 勾选      | login.agree_terms  |                        |                          |
TC001   |               |       |        | 点击      | login.submit       |                        | URL包含 /dashboard/     |

TC002   | 创建爬虫任务   | task  | P1    | 清除cookie |                    |                        |                          | [setup]
TC002   |               |       |        | 导航       | /tasks/create/     |                        |                          |
TC002   |               |       |        | 输入       | task.name          | youtube_${timestamp}   |                          |
TC002   |               |       |        | 输入       | task.url           | https://youtube.com/.. |                          |
TC002   |               |       |        | 点击       | task.submit        |                        | 元素可见 .success       |
TC002   |               |       |        | 登出       |                    |                        |                          | [teardown]
```

---

## 常见问题

**Q: 目标元素怎么填？**
→ 在 Web 管理平台的「Locators 管理」页面查看当前项目已配置的 locator key，如 `login.username`。

**Q: 操作类型填错了会怎样？**
→ 执行时会报错「未知操作类型」，请参考上表填写。

**Q: 可以不填预期结果吗？**
→ 可以，不填则仅执行步骤，不做断言验证。

**Q: 一个 Excel 可以放多个用例吗？**
→ 可以，每个用例ID单独一组行即可。

**Q: 备注里的 `[setup]` 必须大写吗？**
→ 不区分大小写，`[SETUP]`、`[setup]`、`[前置]` 都支持。
