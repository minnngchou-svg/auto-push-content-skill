# AI Opportunity Watcher 使用说明

这个目录里的项目，才是真正会跑起来的 watcher。

它会定时抓取多个站点的内容，筛选出和 AI 福利、试用、额度、邀请码相关的话题，然后发到邮箱。你还可以直接回复邮件，用序号保存文章、给内容打偏好、写备注。

如果你是第一次接触这套项目，建议严格按下面顺序操作。

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
- 一个可用的邮箱账号
- 这个邮箱对应的 SMTP 权限
- 如果要处理“回复邮件”，还需要 IMAP 权限

先确认 Python 正常：

```powershell
python --version
```

## 3. 项目里最重要的文件有哪些

你最常接触的是这些文件：

- `linux_do_watcher.py`
- `config.example.json`
- `config.json`
- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`
- `install_tasks.ps1`
- `doctor.ps1`

运行后还会出现这些文件：

- `state.json`
- `watcher_runs.jsonl`
- `last_sent_batch.json`
- `reply_state.json`
- `reply_actions.jsonl`
- `saved_articles/`
- `sent_batches/`

## 4. 第一次怎么配置

### 第 4.1 步：先生成 `config.json`

如果项目里还没有 `config.json`，就把：

- `config.example.json`

复制成：

- `config.json`

### 第 4.2 步：填写邮箱配置

最常见是用 QQ 邮箱发信。

如果你想抓取个性化内容，也是直接在 IDE 里改这套项目本身，不需要重装。

最常改的是：

- `config.json`
- `linux_do_watcher.py`

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

### 第 4.3 步：理解推送渠道

默认模板里同时保留了：

- `email`
- `wxpusher`

如果你只想先用邮箱：

- 把 `email.enabled` 设为 `true`
- 把 `wxpusher.enabled` 设为 `false`

## 5. 默认监控哪些来源

默认来源已经配好了，不用你手动加：

- `linux.do`
- `NodeSeek`
- `V2EX`

默认逻辑是：

- 先从多来源抓取
- 过滤 AI 福利相关内容
- 做跨站去重
- 再按站点分段发邮件

## 6. 先手动测试，再上定时任务

### 第 6.1 步：做干运行测试

先运行：

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

如果成功，你会看到：

- 抓取了多少条
- 命中了多少条
- 这一轮预计会发什么
- 对应的邮件批次号

### 第 6.2 步：测试回复处理

再运行：

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

如果还没有新回复，出现：

```text
No new reply emails to process.
```

这是正常的。

### 第 6.3 步：如果想首轮就把当前结果发出去

可以运行：

```powershell
python .\linux_do_watcher.py --config .\config.json --first-run-send
```

## 7. 怎么安装定时任务

确认手动测试没问题后，再运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1
```

默认会创建两个任务：

- `LinuxDoWatcher3H`
- `LinuxDoReplyProcessor10M`

默认调度是：

- watcher：从 `14:10` 开始，每 3 小时跑一次
- reply processor：从 `00:00` 开始，每 10 分钟跑一次

默认电源策略是：

- 电池模式不启动
- 如果运行中切到电池模式，会停止

所以最稳的使用方式是：

- 放在长期插电的电脑上跑

## 8. 邮件收到后怎么操作

收到推送邮件后，不需要打开本地脚本，也不需要再手工找链接。

你可以直接回复那封邮件，在正文最前面输入指令。

### 最常用的回复指令

- `1`
- `1 3 5`
- `2+`
- `3-`
- `4 note: 这个活动像真福利`

它们的意思分别是：

- `1`：保存第 1 条
- `1 3 5`：保存第 1、3、5 条
- `2+`：以后更偏向推类似内容
- `3-`：以后少推类似内容
- `4 note: ...`：给第 4 条加备注

### 回复时要注意什么

为了让系统识别更稳：

- 尽量直接回复原邮件
- 把命令放在正文最开头
- 不要把命令埋在一大段聊天内容后面

## 9. 保存后的文章会去哪里

保存后的文章会进：

- `saved_articles/`

系统会自动：

- 按内容类型分类
- 更新索引
- 让最近的内容排在最上面

常见分类包括：

- `offers`
- `news`
- `guides`
- `tools`
- `other`

## 10. 过滤规则怎么理解

当前模板已经内置了一套默认规则。

它的思路不是“只要出现 AI 就推”，而是更像：

- 一组词要像“福利词”
- 另一组词要像“AI 产品词”
- 同时命中才更容易进推送

你后面如果想自己调：

- 改 `filter.required_keyword_groups`
- 改 `filter.exclude_keywords`
- 改 `filter.max_notify_items`

如果你想抓取更个性化的内容，直接在 IDE 里修改即可。

最常见的改法是：

- 在 `config.json` 里增删来源
- 在 `config.json` 里改关键词组
- 在 `config.json` 里改排除词
- 在 `linux_do_watcher.py` 里改更细的匹配逻辑

## 11. 常见排错

### 情况 1：脚本报网络连接被拒绝

很常见的原因是系统里挂了坏掉的代理变量，比如：

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `ALL_PROXY`
- `GIT_HTTP_PROXY`
- `GIT_HTTPS_PROXY`

好消息是，这套模板的两个启动脚本已经会自动清理这些常见代理变量：

- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`

所以计划任务路径通常不会再因为死代理而失败。

### 情况 2：计划任务没跑

优先检查：

- 电脑是不是在电池模式
- 计划任务是不是已经创建
- `watcher_task.log` 有没有新记录

可以运行：

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

## 12. 如何看运行状态

最常用的几个状态文件是：

- `state.json`
- `watcher_runs.jsonl`
- `reply_actions.jsonl`
- `watcher_task.log`
- `reply_task.log`

最常见的状态有：

- `no_match`
- `no_new`
- `sent`
- `bootstrapped`
- `error`

## 13. 如果你想把这套项目分享给别人

不要直接把你自己的运行目录整包发出去。

尤其不要共享这些：

- `config.json`
- `state.json`
- `saved_articles/`
- `sent_batches/`
- 日志文件

适合分享的是：

- `config.example.json`
- 脚本模板
- 安装说明

## 14. 推荐的第一次完整操作顺序

如果你想最稳地从零跑起来，就按这个顺序来：

1. 确认 Python 正常。
2. 复制 `config.example.json` 为 `config.json`。
3. 填邮箱账号、SMTP 授权码、接收邮箱。
4. 运行 `--dry-run`。
5. 运行 `--process-replies-only`。
6. 运行 `install_tasks.ps1`。
7. 等第一封正式推送邮件。
8. 直接回复邮件测试 `1` 或 `1 3 5`。
9. 如果想抓取个性化内容，直接在 IDE 里继续改 `config.json` 和 `linux_do_watcher.py`。
