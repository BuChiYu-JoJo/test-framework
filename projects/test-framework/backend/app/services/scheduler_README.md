# Scheduler Service

基于 APScheduler 的定时任务管理服务，支持 cron 表达式调度。

## 功能

- 支持完整的 6 分量 cron 表达式（秒/分/时/日/月/周）
- 任务持久化到 SQLite 数据库，应用重启后自动恢复
- 支持手动立即触发任务
- 与执行引擎无缝集成

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/scheduler/jobs | 创建定时任务 |
| GET | /api/v1/scheduler/jobs | 列表 |
| GET | /api/v1/scheduler/jobs/{id} | 详情 |
| PUT | /api/v1/scheduler/jobs/{id} | 更新 |
| DELETE | /api/v1/scheduler/jobs/{id} | 删除 |
| POST | /api/v1/scheduler/jobs/{id}/run | 手动触发 |

## Cron 预设

- 每天凌晨：`0 0 * * *`
- 每小时：`0 0 * * * *`
- 每天 9:00：`0 0 9 * *`
- 每周一 9:00：`0 0 9 * * 1`
- 每月 1 号：`0 0 1 1 *`
