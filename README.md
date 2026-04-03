# Auto Push Content Skill

这是一个给 Codex 用的 skill 仓库。

这个仓库本身不是“直接运行监控”的项目，而是一个可以安装到 Codex 里的 skill。  
安装好这个 skill 之后，你只要在 Codex 里说一句话，它就会帮你把真正运行的 watcher 项目铺到当前工作区。

这套 watcher 最终可以做到：

- 监控 `linux.do`
- 监控 `NodeSeek`
- 监控 `V2EX`
- 自动发邮件
- 支持回复邮件执行指令
- 自动保存文章到本地知识库

## 先搞清楚这两个概念

你现在看到的是：

- `skill 仓库`

这个 skill 安装到 Codex 之后，Codex 再帮你生成：

- `watcher 项目`

可以简单理解成：

- 当前这个 GitHub 仓库 = 安装器
- 生成出来的 watcher 项目 = 真正干活的程序

## 最推荐的用法

如果你只是想把这套东西装起来，用下面这条路线就够了：

1. 安装 skill
2. 重启 Codex
3. 在 Codex 里调用 skill
4. 让 skill 帮你生成 watcher 项目
5. 填 `config.json`
6. 先手动测试
7. 再创建计划任务

## 自动安装和手动安装怎么选

这里有两条路：

- `自动安装`：适合绝大多数人，直接从 GitHub 把 skill 装进 Codex
- `手动安装`：适合你已经 `git clone` 了仓库，或者你想自己管理 skill 文件

## 方案一：自动安装，推荐

这是最适合普通用户和朋友复刻的方案。

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

如果能看到版本号，比如 `Python 3.12.x`、`Python 3.13.x`、`Python 3.14.x`，就可以继续。

### 第 2 步：安装 skill

在 PowerShell 里运行：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

这条命令会：

- 从 GitHub 下载这个 skill
- 安装到你本机的 Codex skill 目录

### 第 3 步：重启 Codex

这一步不能省。

很多人不是没装成功，而是装完 skill 以后没有重启 Codex，所以在技能列表里看不到。

### 第 4 步：在 Codex 里调用 skill

进入你想放项目的工作区，然后直接说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务
```

如果你现在只想先铺项目，不想立刻创建计划任务，也可以说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，但先不要创建计划任务
```

### 第 5 步：生成完成后会看到什么

正常情况下，工作区里会出现：

- `linux_do_watcher.py`
- `config.example.json`
- `config.json`
- `run_linux_do_watcher.ps1`
- `run_linux_do_reply_processor.ps1`
- `install_tasks.ps1`
- `doctor.ps1`
- `README.md`

看到这些文件，就说明 watcher 已经铺好了。

## 方案二：手动安装，适合已经 clone 仓库的人

如果你已经把仓库 clone 到本地，也可以不用走 GitHub 安装命令，直接手动安装 skill。

### 第 1 步：clone 仓库

```powershell
git clone https://github.com/minnngchou-svg/auto-push-content-skill.git
```

### 第 2 步：把 skill 目录复制到 Codex 技能目录

把仓库里的：

- `ai-opportunity-watcher/`

复制到：

- `%USERPROFILE%\.codex\skills\ai-opportunity-watcher`

也就是复制完成后，目标结构应该像这样：

```text
%USERPROFILE%\.codex\skills\ai-opportunity-watcher\SKILL.md
%USERPROFILE%\.codex\skills\ai-opportunity-watcher\scripts\bootstrap_watcher.py
%USERPROFILE%\.codex\skills\ai-opportunity-watcher\assets\project-template\...
```

### 第 3 步：重启 Codex

还是一样，必须重启 Codex。

### 第 4 步：调用 skill

重启后，在 Codex 里说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务
```

## clone 以后，`skill-creator` 到底该怎么用

你刚才提醒得很对，但这里有一个关键区别要写清楚。

### 普通用户安装 skill

普通用户如果只是想“把 skill 装起来然后用”，不需要 `skill-creator`。

对普通用户来说：

- `skill-installer` 是安装器
- 手动复制 `ai-opportunity-watcher/` 到 `~/.codex/skills/` 也是安装

### 维护者或二开用户修改 skill

如果你已经 clone 了仓库，而且你想：

- 修改 skill 文案
- 修改 skill 里的脚本
- 修改 skill 模板
- 继续扩展这个 skill

那这时候就可以让 Codex 配合：

- `$skill-creator`

来维护这个 skill 本身。

也就是说：

- `skill-installer` / 手动复制：解决“怎么安装 skill”
- `$skill-creator`：解决“怎么维护 skill”

### 一句最实用的理解

不要把 `$skill-creator` 当成普通用户的安装器。  
它更适合你这种仓库维护者，在 clone 仓库之后继续打磨和更新 skill。

## 手动 / 自动，一眼看懂

### 自动完成的事

如果你用这套 skill，下面这些通常都可以自动完成：

- 把 watcher 模板铺到当前工作区
- 没有 `config.json` 时，从 `config.example.json` 自动生成
- 生成 watcher 运行脚本
- 生成计划任务安装脚本
- 生成健康检查脚本
- 可选创建计划任务
- 启动脚本自动清掉常见坏代理变量

### 必须手动改的事

这些内容涉及你的隐私、账号或个人选择，必须手动确认：

- 你的邮箱账号
- SMTP 授权码
- IMAP 相关配置
- 收件邮箱
- `allowed_senders`
- 你到底想不想开邮箱推送
- 你到底想不想开 `WxPusher`

这类内容不应该让仓库写死，也不应该让脚本猜。

### 可以让 IDE / Codex 直接帮你改的事

这类属于本地规则和逻辑优化，最适合直接在 IDE 里改：

- 增删监控来源
- 调关键词
- 调排除词
- 调推送条数
- 调计划任务时间
- 调更细的匹配逻辑
- 调邮件模板
- 调文章保存格式

也就是说，如果你想抓取更个性化的内容，直接用 IDE 打开生成出来的 watcher 项目去改即可。

最常改的是：

- `config.json`
- `linux_do_watcher.py`
- `install_tasks.ps1`

## 配置时最重要的实战提醒

### 最好准备两个邮箱地址

非常推荐这样配：

- 一个邮箱负责发信和接收回复
- 另一个邮箱负责实际接收提醒邮件

原因是：

- 如果发件邮箱和收件邮箱是同一个账号，某些邮箱服务会把“自己发给自己”的邮件折叠、归档，甚至看起来像没收到

我们之前已经踩过这个坑，所以这里单独强调。

## 朋友装好之后，下一步看哪里

如果 skill 已经安装好了，朋友下一步应该看 watcher 项目里的：

- `README.md`

也就是 skill 生成到工作区之后的那份 README。  
那份文档负责解释：

- `config.json` 怎么填
- 邮件怎么测
- 回复指令怎么用
- 计划任务怎么装
- 出问题怎么排查

## 最短转发版本

如果你只想把最短教程发给朋友，发这几句就够了：

1. 安装 Python 和 Codex。
2. 在 PowerShell 运行安装命令：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" --repo minnngchou-svg/auto-push-content-skill --path ai-opportunity-watcher
```

3. 重启 Codex。
4. 在 Codex 里说：

```text
用 $ai-opportunity-watcher 在当前工作区安装 watcher，并创建计划任务
```

5. 打开生成出来的 `config.json`，填邮箱账号和授权码。
6. 先跑一次 `--dry-run`。
7. 如果想抓个性化内容，直接在 IDE 里改 `config.json` 或 `linux_do_watcher.py`。

## 仓库结构说明

- `ai-opportunity-watcher/`：真正发布出去的 Codex skill

这个目录里又包含：

- `SKILL.md`
- `scripts/`
- `assets/project-template/`
- `references/`
- `agents/`

## 这个仓库不应该保存什么

这个仓库主要是发布 skill 的，不是保存你的个人运行状态的。

不要把这些内容推上来：

- `config.json`
- `state.json`
- `saved_articles/`
- `sent_batches/`
- 日志文件
- 你自己的邮箱授权码
