# Test Framework - 通用自动化测试框架

## 概述

一款支持多层次的自动化测试框架，旨在降低测试用例编写门槛，同时满足复杂测试场景需求。

## 特性

- **多格式支持**: YAML / Excel / JSON 用例格式
- **配置驱动**: 元素定位与业务逻辑分离
- **分层用例**: 从"完全不懂代码"到"专业Python开发"都能使用
- **多项目管理**: 同一框架支持多个项目，通过配置隔离
- **报告丰富**: HTML / JSON / Markdown 报告格式
- **关键字驱动**: 预置30+常用关键字，开箱即用

## 目录结构

```
/test-framework
├── engine/                    # 核心引擎
│   ├── engine.py              # 执行器
│   ├── locator_resolver.py    # 定位符解析
│   ├── keyword_executor.py    # 关键字执行
│   ├── reporter.py            # 报告生成
│   └── parser/                # 用例解析器
│       ├── yaml_parser.py
│       └── excel_parser.py
│
├── projects/                  # 项目配置
│   └── dataify/              # 示例项目
│       ├── env/              # 环境配置
│       ├── locators.json     # 元素定位
│       └── cases/            # 测试用例
│
├── reports/                   # 报告输出
├── scripts/                   # 工具脚本
├── docs/                      # 文档
└── run.py                     # 入口脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install playwright pytest pyyaml openpyxl
playwright install chromium
```

### 2. 运行示例用例

```bash
# 运行单个用例
python run.py --project dataify --case tc001_login

# 运行所有用例
python run.py --project dataify --all

# 指定环境
python run.py --project dataify --case tc001_login --env test
```

## 用例格式

### YAML格式 (推荐)

```yaml
id: TC001
name: 登录成功
module: login
priority: P0
tags: [冒烟, 核心流程]

steps:
  - no: 1
    action: click
    target: login.tab_password

  - no: 2
    action: type
    target: login.username
    value: ${USERNAME}

  - no: 3
    action: type
    target: login.password
    value: ${PASSWORD}

  - no: 4
    action: click
    target: login.submit

expected:
  - url_contains: /dashboard/

data:
  USERNAME: "15251686234"
  PASSWORD: "Zxs6412915@+"
```

### 简写格式

```yaml
steps:
  - click: login.tab_password
  - type: login.username|${USERNAME}
  - type: login.password|${PASSWORD}
  - click: login.submit
```

## Locators配置

```json
{
  "pages": {
    "login": {
      "elements": {
        "tab_password": {
          "selector": "button:has-text('密码登录')",
          "type": "css",
          "priority": 1,
          "description": "密码登录Tab"
        },
        "username": {
          "selector": "[name='account']",
          "type": "css",
          "priority": 1,
          "description": "用户名输入框"
        }
      }
    }
  }
}
```

## 支持的关键字

| 关键字 | 说明 |
|--------|------|
| navigate(url) | 导航到页面 |
| click(target) | 点击元素 |
| type(target, text) | 输入文本 |
| select(target, option) | 下拉选择 |
| check(target) | 勾选 |
| wait(seconds) | 等待秒数 |
| wait_for(target, state) | 等待元素状态 |
| assert_text(target, contains) | 断言文本包含 |
| assert_visible(target) | 断言元素可见 |
| assert_count(target, op, num) | 断言数量 |
| screenshot(name) | 截图 |
| api_request(method, url, body) | API请求 |

## 开发指南

### 添加新项目

1. 创建项目目录: `projects/myproject/`
2. 添加环境配置: `env/test.json`
3. 添加Locators: `locators.json`
4. 添加测试用例: `cases/yaml/`

### 添加新关键字

编辑 `engine/keyword_executor.py`，添加新方法:

```python
def my_custom_action(self, selector, value, page=None):
    """自定义关键字"""
    p = page or self.current_page
    # 实现逻辑
    return result
```

然后在 `KEYWORDS` 字典中注册:

```python
KEYWORDS = {
    'my_action': 'my_custom_action',
    ...
}
```

## 许可证

MIT License
