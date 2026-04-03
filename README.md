# Auto Push Content Skill

这是一个给 Codex 用的 skill 仓库。

它的作用不是“直接运行监控脚本”，而是让你或你的朋友可以一条命令安装一个 skill，然后再用一句话把整套 AI 白嫖监控项目铺到自己的工作区里。

这套 skill 铺出来的项目可以：

- 监控 `linux.do`
- 监控 `NodeSeek`
- 监控 `V2EX`
- 自动发邮件
- 支持回复邮件执行指令
- 自动保存文章到本地知识库

## 先搞清楚这两个概念

这个仓库里放的是：

- `skill`

skill 安装完成后，skill 再帮你生成真正运行的项目，也就是 watcher。

你可以把它理解成：

- 这个仓库 = 安装器
- 生成出来的 watcher 项目 = 真正干活的程序

## 谁适合用这个仓库

适合下面这两类人：

- 已经在用 Codex，想一键把 AI 机会监控装起来的人
- 想把这套监控快速复刻给朋友的人

如果你的朋友根本不用 Codex，那这个仓库就不是最直接的入口。那种情况更适合直接发“生成出来的 watcher 项目模板”。

## 这套东西最后能做到什么

装完以后，你朋友会得到一套本地项目，它会：

- 每 3 小时检查一次多个站点
- 找出和 AI 免费额度、试用、兑换码、邀请码、福利相关的内容
- 发到邮箱
- 邮件里直接回复 `1`、`1 3 5`、`2+`、`3-`、`4 note: ...`
- 自动保存对应文章并按分类归档

## 保姆级安装教程

下面按“完全从零开始”来写。

### 第 1 步：准备环境

你的朋友需要先准备：

- Windows
- 已安装 Codex
- 已安装 Python
- 最好准备两个邮箱地址

先确认 Python 能用：

```powershell
python --version
```

如果能看到版本号，比如 `Python 3.12.x`、`Python 3.13.x`、`Python 3.14.x`，就可以继续。

### 第 2 步：安装这个 skill

在 PowerShell 里运行：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

这条命令做的事是：

- 从 GitHub 下载这个 skill
- 安装到你本机的 Codex skill 目录里

安装完成后，重启 Codex。

### 第 3 步：在 Codex 里调用 skill

重启 Codex 后，在你想放项目的工作区里直接说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务
```

如果你不想立刻创建计划任务，也可以说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，但先不要创建计划任务
```

### 第 4 步：skill 会帮你生成哪些文件

生成完成后，工作区里通常会有这些文件：

- `linux_do_watcher.py`
- `config.example.json`
- `config.json`
- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`
- `install_tasks.ps1`
- `doctor.ps1`
- `README.md`

如果你看到这些文件，说明 watcher 已经铺好了。

### 第 5 步：填写配置

最重要的是 `config.json`。

第一次使用，最少要把邮箱相关配置填好。

如果你想抓取更个性化的内容，也是从这一步开始改。

最直接的做法就是：

- 用 IDE 打开生成出来的 watcher 项目
- 直接修改 `config.json`
- 如果你想改更深的逻辑，再修改 `linux_do_watcher.py`

常用的是 QQ 邮箱发信，最关键的几个字段是：

- `push.email.enabled`
- `push.email.smtp_host`
- `push.email.smtp_port`
- `push.email.username`
- `push.email.password`
- `push.email.from_addr`
- `push.email.to_addrs`
- `push.email.imap_host`
- `push.email.reply_processing.allowed_senders`

如果你用 QQ 邮箱，常见写法是：

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

这里最容易填错的是：

- `password` 不是邮箱登录密码
- `password` 是 QQ 邮箱的 SMTP 授权码

还有一个很重要的实战建议：

- 最好用两个邮箱地址
- 一个邮箱负责发信和收回复
- 另一个邮箱负责接收推送

原因是：

- 如果发件邮箱和收件邮箱是同一个账号，某些邮箱服务会把“自己发给自己”的邮件折叠、归档，甚至看起来像没收到
- 我们之前就遇到过这个问题

### 第 6 步：先手动测试，不要一上来就等计划任务

先做干运行测试：

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

如果这一步正常，你会在终端里看到：

- 抓到了哪些内容
- 哪些内容会被推送
- 邮件批次号

再测试回复处理链路：

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

如果没有新回复，看到 `No new reply emails to process.` 是正常的。

### 第 7 步：创建计划任务

如果你在调用 skill 时没有自动创建计划任务，就手动运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1
```

默认会创建两个计划任务：

- `LinuxDoWatcher3H`
- `LinuxDoReplyProcessor10M`

默认调度是：

- watcher：从 `14:10` 开始，每 3 小时运行一次
- reply processor：从 `00:00` 开始，每 10 分钟运行一次

当前模板默认策略是：

- 电池模式不启动
- 如果运行过程中切到电池模式，会停止

也就是说，这套默认更适合放在插电的电脑上长期跑。

如果你后面想让推送更符合自己的口味，不需要重新安装 skill。

直接在 IDE 里改生成出来项目里的配置和规则就可以：

- 改 `config.json` 里的来源
- 改 `config.json` 里的过滤词
- 改 `config.json` 里的排除词
- 必要时改 `linux_do_watcher.py`

## 朋友收到邮件后怎么用

这套系统不只是“发邮件提醒”，还支持直接用邮件回复做操作。

收到推送邮件后，可以直接回复原邮件，在正文最上面输入命令。

支持这些常用指令：

- `1`
- `1 3 5`
- `2+`
- `3-`
- `4 note: 这个活动像真福利`

含义分别是：

- `1`：保存第 1 条
- `1 3 5`：批量保存第 1、3、5 条
- `2+`：以后优先推类似内容
- `3-`：以后少推类似内容
- `4 note: ...`：给第 4 条加备注

## 生成出来的项目会保存哪些数据

项目运行后，常见文件有：

- `state.json`
- `watcher_runs.jsonl`
- `last_sent_batch.json`
- `reply_state.json`
- `reply_actions.jsonl`
- `saved_articles/`
- `sent_batches/`

这些文件是运行时状态，不应该直接共享给别人。

## 常见问题

### 1. 装完 skill 以后，Codex 里找不到

先重启 Codex。

这个步骤很重要。很多人不是没装上，而是装上以后没有重启。

### 2. 计划任务创建了，但没有按时发邮件

先检查电脑是不是在电池模式。

当前模板默认就是：

- `No Start On Batteries`
- `Stop On Battery Mode`

如果你希望抓取更个性化的内容，不是重建计划任务，而是直接在 IDE 里修改项目配置和规则。

### 3. 明明网络正常，但脚本报连接被拒绝

这台机器可能挂了坏掉的代理变量，比如：

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `ALL_PROXY`
- `GIT_HTTP_PROXY`
- `GIT_HTTPS_PROXY`

当前模板里的启动脚本已经会自动清掉这些常见代理变量，所以计划任务路径一般不会再踩这个坑。

### 4. 邮件能发，但回复邮件不生效

优先检查：

- `reply_processing.enabled` 是否为 `true`
- `allowed_senders` 是否包含你的回复邮箱
- 你是不是“回复原邮件”，而不是新写一封邮件

### 5. 明明发送成功了，但收件箱里看不到

优先检查是不是把发件邮箱和收件邮箱配置成了同一个账号。

更推荐的做法是：

- 发件邮箱：负责 SMTP 发信和 IMAP 读取回复
- 收件邮箱：负责实际接收提醒邮件

### 6. 想只分享 skill，不想泄露自己的配置

公开仓库里不要提交这些运行时文件：

- `config.json`
- `state.json`
- `saved_articles/`
- `sent_batches/`
- 各种日志文件

这个仓库现在已经默认忽略这些本地运行文件。

## 仓库结构说明

- `ai-opportunity-watcher/`：真正发布出去的 Codex skill

这个目录里又包含：

- `SKILL.md`
- `scripts/`
- `assets/project-template/`
- `references/`
- `agents/`

## 一句话给朋友的版本

如果你只想把最短教程发给朋友，发这几句就够了：

1. 先装 Python 和 Codex。
2. 在 PowerShell 里运行安装命令。
3. 重启 Codex。
4. 在 Codex 里说：`用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务`
5. 打开生成的 `config.json`，填好邮箱账号和授权码。
6. 先跑一次 `--dry-run` 测试。
7. 如果想抓取个性化内容，直接在 IDE 里改 `config.json` 或 `linux_do_watcher.py`。

## 仓库说明

这个仓库主要是用来发布 skill 的，不是用来保存你的个人运行状态的。

所以：

- skill 应该推到 GitHub
- 你的邮箱配置、日志、知识库、状态文件应该只保留在本地
