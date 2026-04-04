# Auto Push Content Skill

这是一个给 Codex 用的 skill 仓库。

它的目标不是让朋友手动敲一堆命令，而是让朋友用一句话就在自己的工作区搭起一套“AI 白嫖 / 机会监控”系统。

这套 skill 最终会帮你铺出一个 watcher 项目，它支持：

- 抓取 `linux.do`
- 抓取 `NodeSeek`
- 抓取 `V2EX`
- 邮件推送
- 邮件回复指令
- 保存文章到本地知识库
- 结构化整理 `saved_articles/`

## 先看结论

对大多数人来说，真正需要自己做的只有 4 步：

1. 安装这个 skill
2. 重启 Codex
3. 对 Codex 说一句话，让它在当前工作区安装 watcher 并创建 Codex 自动化
4. 打开 `config.json`，填自己的邮箱配置

除此之外的大部分命令，都是：

- 备用方案
- 排错方案
- 或者给维护者看的

## 默认路径

这是最推荐的安装方式，也是最适合朋友复刻的路径。

### 第 1 步：准备环境

先准备：

- Windows
- Codex
- Python
- 最好准备两个邮箱地址

先确认 Python 正常：

```powershell
python --version
```

### 第 2 步：安装 skill

在 PowerShell 里运行：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

### 第 3 步：重启 Codex

这一步需要做。

### 第 4 步：让 Codex 安装 watcher 并创建自动化

进入你想放项目的工作区，然后直接说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建 2 个 Codex 自动化：watcher 每天在 09:00、12:00、15:00、18:00、21:00 运行；reply processor 每天 09:00 到 23:00 每小时运行一次
```

如果你暂时只想先把项目铺出来，也可以说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，但先不要创建自动化
```

### 第 5 步：只手动改 `config.json`

正常情况下，你真正必须手动处理的核心就是这一件事：

- 打开生成出来的 `config.json`
- 填好邮箱、授权码、IMAP 和收件地址

如果你想抓取更个性化的内容，也是在 IDE 里直接改生成出来的 watcher 项目：

- 改 `config.json`
- 必要时改 `linux_do_watcher.py`

## 自动完成的事情

默认情况下，这套 skill 会帮你自动完成：

- 把 watcher 模板铺到当前工作区
- 在缺失时生成 `config.json`
- 生成启动脚本
- 生成健康检查脚本
- 提示并创建 Codex 自动化
- 默认调度为：
- watcher：每天 `09:00 / 12:00 / 15:00 / 18:00 / 21:00`
- reply processor：每天 `09:00-23:00` 每小时一次
- 启动脚本自动清理坏掉的代理变量

这里有一个你需要提前知道的小点：

- Codex 自动化目前不支持“每 10 分钟”这种频率
- 所以回复处理默认改成“每天 09:00-23:00 每 1 小时一次”
- watcher 仍然保留“白天每 3 小时一轮”的节奏，所以最后一轮是 `21:00`
- 如果你以后一定要更快，比如 10 分钟一次，可以再手动启用 Windows 备用脚本

## 哪些必须手动改

这些内容不应该自动猜，必须你自己确认：

- 发件邮箱
- 收件邮箱
- SMTP 授权码
- IMAP 配置
- `allowed_senders`
- 是否开启邮箱推送
- 是否开启 `WxPusher`

另外非常推荐这样配：

- 一个邮箱负责 SMTP 发信和 IMAP 读回复
- 另一个邮箱负责接收 watcher 推送

因为如果发件邮箱和收件邮箱是同一个账号，某些邮箱服务会把“自己发给自己”的邮件折叠，导致看起来像没收到。

## 哪些可以直接在 IDE 里改

如果你想抓取更个性化的内容，不需要重装项目。

直接在 IDE 里改这些文件即可：

- `config.json`
- `linux_do_watcher.py`
- `install_tasks.ps1`

最常见的修改包括：

- 增删抓取来源
- 调关键词
- 调排除词
- 调推送条数
- 调匹配逻辑
- 改备用 Windows 调度时间

## 手动命令

下面这些不是默认流程必做项，只有在你需要的时候才用。

### 手动干运行

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

### 只处理回复邮件

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

### 首次就发送当前命中

```powershell
python .\linux_do_watcher.py --config .\config.json --first-run-send
```

### 健康检查

```powershell
powershell -ExecutionPolicy Bypass -File .\doctor.ps1
```

### Windows 备用方案

默认不需要 Windows 计划任务。

只有在你明确不想用 Codex 自动化，或者你一定要更高频回复处理时，才考虑这个备用脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1
```

这个脚本现在属于“备用方案”，不是默认安装路径。

## clone 之后怎么处理

如果你已经 `git clone` 了这个仓库，有两种用法。

### 普通使用者

普通使用者如果只是想“安装并使用这个 skill”，不需要 `$skill-creator`。

普通使用者只需要：

- 用 `skill-installer` 从 GitHub 安装
- 或者手动把 `ai-opportunity-watcher/` 复制到 `%USERPROFILE%\.codex\skills\ai-opportunity-watcher`

复制完成后重启 Codex 即可。

### 维护者

如果你已经 clone 了仓库，而且你想：

- 改 skill 文档
- 改 skill 脚本
- 改模板文件
- 继续扩展这个 skill

这时候再用 `$skill-creator`。

也就是说：

- `skill-installer` / 手动复制：解决“怎么安装”
- `$skill-creator`：解决“怎么维护和升级 skill”

## 最短说明

如果你只想转发最短版本，发这段就够了：

1. 安装 Python 和 Codex。
2. 在 PowerShell 运行：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

3. 重启 Codex。
4. 在 Codex 里说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建 2 个 Codex 自动化：watcher 每天在 09:00、12:00、15:00、18:00、21:00 运行；reply processor 每天 09:00 到 23:00 每小时运行一次
```

5. 打开生成出来的 `config.json`，填邮箱账号、SMTP 授权码、IMAP 配置和收件邮箱。
6. 如果想抓取个性化内容，直接在 IDE 里改 `config.json` 或 `linux_do_watcher.py`。

## 仓库结构

- `ai-opportunity-watcher/`：真正发布出去的 Codex skill

里面主要包含：

- `SKILL.md`
- `scripts/`
- `assets/project-template/`
- `references/`
- `agents/`

## 不要提交什么

不要把这些内容推到仓库里：

- `config.json`
- `state.json`
- `saved_articles/`
- `sent_batches/`
- 日志文件
- 你自己的邮箱授权码
