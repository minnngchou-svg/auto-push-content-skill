# Auto Push Content Skill

这是一个给 Codex 用的 skill 仓库。

它不是“让你手动敲一堆命令”的项目，而是一个安装器。  
正常情况下，你只需要把 skill 装进 Codex，然后用一句话让 Codex 把 watcher 项目铺出来就够了。

## 先看结论

对大多数人来说，真正需要自己做的只有 4 件事：

1. 安装这个 skill
2. 重启 Codex
3. 让 Codex 在当前工作区安装 watcher
4. 打开 `config.json`，填自己的邮箱信息

除此之外的大部分命令，都是：

- 备用方案
- 排错方案
- 或者给维护者看的

## 这套东西最后能做什么

装完以后，你会得到一套 watcher 项目，它可以：

- 监控 `linux.do`
- 监控 `NodeSeek`
- 监控 `V2EX`
- 自动发邮件
- 支持回复邮件执行指令
- 自动保存文章到本地知识库

## 最推荐的安装方式

这是默认路径，也是最适合朋友复刻的路径。

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

这一步会把 skill 安装到 Codex 的技能目录。

### 第 3 步：重启 Codex

这一步必须做。

### 第 4 步：在 Codex 里说一句话

进入你想放项目的工作区，然后直接说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务
```

如果你暂时不想创建计划任务，也可以说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，但先不要创建计划任务
```

### 第 5 步：只手动改 `config.json`

正常情况下，真正需要你手动处理的核心就是这一件事：

- 打开生成出来的 `config.json`
- 填好邮箱和授权码

如果你想抓取更个性化的内容，也是直接在 IDE 里改生成出来的 watcher 项目：

- 改 `config.json`
- 必要时改 `linux_do_watcher.py`

## 哪些是自动完成的

默认情况下，这套 skill 会帮你自动完成：

- 把 watcher 模板铺到当前工作区
- 在缺少时生成 `config.json`
- 生成启动脚本
- 生成计划任务安装脚本
- 生成健康检查脚本
- 可选创建计划任务
- 启动脚本自动清理坏掉的代理变量
- 计划任务默认以隐藏窗口运行

所以你说得对，很多命令并不需要普通用户手动做。

## 哪些必须手动改

这些内容不应该自动猜，必须你自己确认：

- 发件邮箱
- 收件邮箱
- SMTP 授权码
- IMAP 相关配置
- `allowed_senders`
- 你是否开启邮箱推送
- 你是否开启 `WxPusher`

另外非常推荐这样配：

- 一个邮箱负责 SMTP 发信和 IMAP 读回复
- 另一个邮箱负责接收 watcher 推送

因为如果发件邮箱和收件邮箱是同一个账号，某些邮箱服务会把“自己发给自己”的邮件折叠，导致看起来像没收到。

## 哪些只在需要时才手动做

下面这些不是默认流程必做项，只有在你需要的时候才用：

### 1. 手动测试命令

如果你想自己验一下 watcher 状态，可以用：

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

如果你想单独验证回复处理链路，可以用：

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

### 2. 手动创建计划任务

只有当你在上一步没有让 Codex 自动创建任务时，才需要自己运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1
```

### 3. 手动安装 skill

如果你已经 `git clone` 了这个仓库，也可以不用 GitHub 安装命令，直接手动复制：

- 把仓库里的 `ai-opportunity-watcher/`
- 复制到 `%USERPROFILE%\.codex\skills\ai-opportunity-watcher`

复制完以后，重启 Codex 即可。

## clone 以后，`skill-creator` 该怎么理解

这里很容易混淆，所以单独说清楚。

### 普通用户

普通用户如果只是想“安装并使用这个 skill”，不需要 `$skill-creator`。

普通用户只需要：

- `skill-installer`
- 或者手动复制 skill 目录

### 维护者

如果你已经 clone 了仓库，而且你想：

- 修改 skill 文案
- 修改 skill 脚本
- 修改模板内容
- 继续扩展这个 skill

那这时候 `$skill-creator` 很有价值。

也就是说：

- `skill-installer` / 手动复制：解决“怎么安装”
- `$skill-creator`：解决“怎么维护和升级 skill”

## 给朋友的最短说明

如果你只想转发最短版本，发这段就够了：

1. 安装 Python 和 Codex。
2. 在 PowerShell 运行：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

3. 重启 Codex。
4. 在 Codex 里说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务
```

5. 打开生成出来的 `config.json`，填邮箱账号和授权码。
6. 如果想抓更个性化的内容，直接在 IDE 里改 `config.json` 或 `linux_do_watcher.py`。

## 仓库结构说明

- `ai-opportunity-watcher/`：真正发布出去的 Codex skill

里面主要包含：

- `SKILL.md`
- `scripts/`
- `assets/project-template/`
- `references/`
- `agents/`

## 这个仓库不应该保存什么

不要把这些内容推上来：

- `config.json`
- `state.json`
- `saved_articles/`
- `sent_batches/`
- 日志文件
- 你自己的邮箱授权码
