# AI Opportunity Watcher 使用说明

这个目录里的项目，才是真正会跑起来的 watcher。

先说结论：

正常使用时，你并不需要手动执行很多命令。
大多数情况下，你只需要：

1. 打开 `config.json`
2. 填好邮箱配置
3. 让 Codex 为当前工作区创建 2 个自动化

所以这份文档会分成两类内容：

- `默认流程`：普通用户真正要做的
- `备用命令`：只有在你想手测、排错或高阶定制时才用

## 1. 这套项目能做什么

默认支持：

- 监控 `linux.do`
- 监控 `NodeSeek`
- 监控 `V2EX`
- 邮件推送
- 邮件回复指令
- 文章分类归档
- 本地知识库索引

## 2. 先准备什么

开始前你至少需要这些：

- Windows
- Python
- 最好准备两个邮箱地址
- 一个邮箱具备 SMTP 发信能力
- 如果要处理“回复邮件”，这个邮箱还需要 IMAP 能力

先确认 Python 正常：

```powershell
python --version
```

## 3. 默认流程，普通用户按这个来

### 第 1 步：确认项目已经生成

如果这是 skill 自动铺出来的项目，目录里通常会有：

- `linux_do_watcher.py`
- `config.example.json`
- `config.json`
- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`
- `install_tasks.ps1`
- `doctor.ps1`

### 第 2 步：只改 `config.json`

真正必须你自己改的，核心就是这个文件：

- `config.json`

最常见是用 QQ 邮箱发信。
你至少要改这些字段：

- `push.email.enabled`
- `push.email.username`
- `push.email.password`
- `push.email.from_addr`
- `push.email.to_addrs`
- `push.email.imap_host`
- `push.email.reply_processing.allowed_senders`

一个常见的 QQ 邮箱示例是：

```json
"email": {
  "enabled": true,
  "smtp_host": "smtp.qq.com",
  "smtp_port": 465,
  "use_ssl": true,
  "starttls": false,
  "username": "你的QQ邮箱@qq.com",
  "password": "你的SMTP授权码",
  "from_addr": "你的QQ邮箱@qq.com",
  "to_addrs": ["接收邮箱@example.com"],
  "save_to_sent": true,
  "imap_host": "imap.qq.com",
  "imap_port": 993,
  "imap_sent_mailbox": "Sent Messages",
  "reply_processing": {
    "enabled": true,
    "mailbox": "INBOX",
    "allowed_senders": ["接收邮箱@example.com"],
    "subject_keyword": "[linux.do]",
    "max_messages": 50
  },
  "timeout_sec": 20
}
```

注意：

- `password` 不是邮箱登录密码
- `password` 是邮箱的 SMTP 授权码

### 第 3 步：推荐用两个邮箱

非常推荐这样配：

- 一个邮箱负责 SMTP 发信和 IMAP 读回复
- 另一个邮箱负责接收 watcher 推送

原因是：

- 如果发件邮箱和收件邮箱是同一个账号，某些邮箱服务会把“自己发给自己”的邮件折叠或分类，导致你以为没有收到

### 第 4 步：创建 Codex 自动化

这是当前默认方案。

直接在 Codex 里说：

```text
请为当前工作区创建 2 个 Codex 自动化：一个在 09:00、12:00、15:00、18:00、21:00 运行 powershell -ExecutionPolicy Bypass -File .\run_linux_do_watcher.ps1，另一个在 09:00 到 23:00 之间每小时运行 powershell -ExecutionPolicy Bypass -File .\run_linux_do_reply_processor.ps1
```

默认调度是：

- watcher：每天 `09:00 / 12:00 / 15:00 / 18:00 / 21:00`
- reply processor：每天 `09:00-23:00` 每小时一次

这里有个重要说明：

- Codex 自动化现在不支持“每 10 分钟”
- 所以回复处理默认统一成“每天 09:00-23:00 每 1 小时”
- watcher 仍然保留“白天每 3 小时一轮”的节奏，所以最后一轮是 `21:00`

## 4. 哪些是自动完成的

这套项目默认会自动处理：

- 多来源抓取
- 默认规则过滤
- 跨站去重
- 邮件批次管理
- 回复指令识别
- 保存文章索引
- 启动脚本自动清理坏掉的代理变量

## 5. 哪些必须手动改

这些必须你自己决定：

- 发件邮箱
- 收件邮箱
- SMTP 授权码
- IMAP 配置
- `allowed_senders`
- 是否开启邮箱推送
- 是否开启 `WxPusher`

## 6. 哪些可以直接在 IDE 里改

如果你想抓取更个性化的内容，不需要重装项目。

直接在 IDE 里改这些文件即可：

- `config.json`
- `linux_do_watcher.py`
- `install_tasks.ps1`

最常见的修改包括：

- 增删监控来源
- 改关键词组
- 改排除词
- 改推送条数
- 改匹配逻辑
- 改备用 Windows 调度时间

## 7. 备用命令，只在需要时手动跑

### 干运行测试

如果你想自己验证本轮会抓到什么，用：

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

### 只测试回复处理

如果你想单独验证回复邮件链路，用：

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

### 首轮直接发送当前结果

如果你希望第一次就把当前命中发出去，用：

```powershell
python .\linux_do_watcher.py --config .\config.json --first-run-send
```

### 健康检查

```powershell
powershell -ExecutionPolicy Bypass -File .\doctor.ps1
```

## 8. Windows 备用方案

默认不需要 Windows 计划任务。

如果你明确不想用 Codex 自动化，或者以后你想把回复处理提速到更高频，再考虑运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1
```

这个备用脚本现在会创建：

- `LinuxDoWatcher3H`
- `LinuxDoReplyProcessor1H`

也就是说，就算走 Windows 备用方案，默认也已经和当前的 Codex 自动化口径对齐成：

- watcher：每天 `09:00 / 12:00 / 15:00 / 18:00 / 21:00`
- reply processor：每天 `09:00-23:00` 每小时一次

## 9. 邮件收到后怎么操作

收到推送邮件后，可以直接回复那封邮件，在正文最前面输入指令。

### 最常用的回复指令

- `1`
- `1 3 5`
- `2+`
- `3-`
- `4 note: 这个活动像真福利`

它们的意思分别是：

- `1`：保存第 1 条
- `1 3 5`：保存第 1、3、5 条
- `2+`：以后更偏向推这类内容
- `3-`：以后少推这类内容
- `4 note: ...`：给第 4 条加备注

### 回复时要注意什么

为了让系统识别更稳：

- 尽量直接回复原邮件
- 把命令放在正文最开头
- 不要把命令埋在一大段聊天内容后面

## 10. 保存后的文章会去哪里

保存后的文章会进入：

- `saved_articles/`

系统会自动：

- 按内容类型分类
- 更新索引
- 让最近的内容排在最上面

## 11. 常见排错

### 情况 1：脚本报网络连接被拒绝

很常见的原因是系统里挂了坏掉的代理变量，比如：

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `ALL_PROXY`
- `GIT_HTTP_PROXY`
- `GIT_HTTPS_PROXY`

模板里的两个启动脚本已经会自动清理这些常见代理变量：

- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`

### 情况 2：Codex 自动化没跑

优先检查：

- Codex 自动化是不是已经创建
- 当前工作区是不是对的
- `watcher_runs.jsonl` 有没有新增记录

也可以运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\doctor.ps1
```

### 情况 3：邮件发不出去

优先检查：

- SMTP 主机和端口对不对
- 授权码是不是填成了登录密码
- `to_addrs` 有没有填接收邮箱

### 情况 4：回复邮件不生效

优先检查：

- `reply_processing.enabled` 是否开启
- `allowed_senders` 是否包含你的邮箱
- 你是不是回复了原推送邮件

### 情况 5：发送成功但收件箱里看不到

优先检查是不是把发件邮箱和收件邮箱配置成了同一个账号。

更稳的做法是：

- 发件邮箱：负责 SMTP 发信和 IMAP 收回复
- 收件邮箱：负责实际接收提醒

## 12. 如何看运行状态

最常用的几个状态文件是：

- `state.json`
- `watcher_runs.jsonl`
- `reply_actions.jsonl`
- `watcher_task.log`（主要给 Windows 备用方案排错用）
- `reply_task.log`（主要给 Windows 备用方案排错用）

最常见的状态有：

- `no_match`
- `no_new`
- `sent`
- `bootstrapped`
- `error`
