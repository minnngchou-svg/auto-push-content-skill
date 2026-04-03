# AI 白嫖情报自动巡检

这套脚本会定时抓取多个站点的最新内容，筛出和 AI 福利、免费额度、邀请码、试用相关的话题，并推送到邮箱或微信。

当前接入的来源：

- `linux.do`
- `NodeSeek`
- `V2EX`

默认行为：

- 按 `linux.do -> NodeSeek -> V2EX` 的优先级聚合
- 同一条机会跨站重复时自动合并去重
- 邮件正文按站点分段展示
- 你可以直接回复邮件里的序号，系统会自动保存对应文章

## 主要文件

- `linux_do_watcher.py`：主脚本
- `config.json`：当前配置
- `config.example.json`：示例配置
- `state.json`：运行状态
- `watcher_runs.jsonl`：每次巡检日志
- `last_sent_batch.json`：最近一次邮件里的编号列表
- `sent_batches/`：历史已发送批次
- `saved_articles/`：按编号保存后的文章归档
- `reply_actions.jsonl`：邮箱回复处理日志
- `feedback_profiles.json`：喜欢/不喜欢反馈画像
- `run_linux_do_watcher.ps1`：Windows 计划任务启动脚本
- `run_linux_do_reply_processor.ps1`：邮箱回复轮询脚本

## 常用命令

预览当前命中，不发信：

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run
```

正常执行一轮：

```powershell
python .\linux_do_watcher.py --config .\config.json
```

首次就把当前结果也发出去：

```powershell
python .\linux_do_watcher.py --config .\config.json --first-run-send
```

预览“首轮发送”，但不改状态：

```powershell
python .\linux_do_watcher.py --config .\config.json --dry-run --reset-state --first-run-send
```

只处理邮箱回复，不抓新帖：

```powershell
python .\linux_do_watcher.py --config .\config.json --process-replies-only
```

按最近一批邮件里的编号保存文章：

```powershell
python .\linux_do_watcher.py --config .\config.json --save-numbers "1 3 5"
```

## 多来源规则

配置改成了 `sources[]` 结构。每个来源都可以独立设置：

- `id`
- `label`
- `enabled`
- `kind`
- `base_url`
- `fetch_mode`
- `entrypoints`
- `priority`

当前默认实现：

- `linux.do`：`latest.json` 优先，失败时回退到 RSS 镜像
- `NodeSeek`：走 `https://rss.nodeseek.com/`
- `V2EX`：走官方节点 API，默认抓 `openai`、`claude`、`cursor`、`copilot`

## 去重和推送

脚本有两层去重：

- 站内去重：按 `source_id + topic_id`
- 跨站去重：按标题归一化和产品关键词生成的 `canonical_key`

推送时会：

- 先按规则过滤
- 再做跨站合并
- 只保留一条主记录
- 在正文里补 `Also seen on:`，显示它也出现在哪些站

## 邮件回复保存

发出的邮件主题里会带批次号，例如：

- `[linux.do][batch 20260403-201002] 4 new matched topic(s)`

你可以直接回复这封邮件，在正文最上面输入：

- `1`
- `1 3 5`
- `2,4`
- `2+`
- `3-`
- `4 note: 这个活动看起来靠谱`

系统会自动：

- 识别这封回复属于哪个批次
- 找到对应编号的话题
- 执行保存、偏好反馈或备注操作
- 保存到 `saved_articles/`
- 自动按内容类型分类到 `offers/`、`news/`、`guides/`、`tools/`、`other/`
- 自动刷新每个分类的 `index.md`
- 让最近时间的文章排在最上面
- 刷新 `active_offers.md` 和 `by_product.md`

目前支持的回复指令：

- `1 3 5`：保存对应文章
- `2+`：以后优先推送类似内容
- `3-`：以后少推类似内容
- `4 note: ...`：给对应条目写备注，若未保存会自动先保存

保存后的文章会自动补这些结构化字段：

- `benefit_type`
- `product`
- `deadline`
- `target_audience`
- `requires_invite`
- `entry_links`
- `note`
- `preference_score`

## 如何确认任务有没有跑

看这几个文件：

- `state.json`
- `watcher_runs.jsonl`
- `reply_task.log`
- `reply_actions.jsonl`

常见状态：

- `no_match`：本轮没命中
- `no_new`：有命中，但和历史重复
- `sent`：有新内容并已推送
- `bootstrapped`：首次运行只记状态，不发历史邮件
- `error`：本轮失败

如果某个来源单独失败，比如 `NodeSeek` 临时不可用：

- 会记录到 `last_source_errors`
- 但只要其他来源还能抓到，整轮任务仍然会继续
