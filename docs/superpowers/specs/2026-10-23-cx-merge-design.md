# cx-study-mate × 油猴脚本能力融合设计

日期：2026-10-23
状态：已确认，进入实现
目标版本：v2.10.0

## 背景

现有 `main.py` 基于 Playwright 无头浏览器，已具备：真实时长播放、心跳、防暂停、字体反混淆、
章节/测验巡检、断点续跑。与 OCS、CxKitty、满分助手等成熟油猴脚本相比，主要缺口：

1. 音频、PDF/文档任务点未处理，部分小节会被直接跳过；
2. 答题链路只有自定义接口 + 已宕机的公共题库，缺少多源并发与归一化；
3. 稳定性与浏览器环境兼容仍有零散问题。

本设计**保留无头 Playwright 内核**，只移植油猴脚本的业务逻辑，不引入油猴注入、不伪造心跳。

## 架构

```
main.py
├─ 任务调度层  run_study / process_current_tab_tasks
├─ 任务点层    视频 / 音频 / PDF·文档 / 测验
├─ 答题层      多源题库并发 → AI 兜底 → 填涂 → 草稿或可选提交
└─ 稳定性层    统一 context、UA/自动化标记兼容、重试、去重、源健康度
```

## 模块一：任务点覆盖

- 在 `process_current_tab_tasks` 中新增音频与文档 frame 识别：
  - 音频：`/ananas/modules/audio/index.html`
  - 文档：`/ananas/modules/pdf/index.html`，兼容 `doc` / `document`
- 音频：静音播放 `audio_html5_api`，轮询 `ended` / `isUnFinishJob()`，带唤醒与超时。
- 文档：滚动 `#panView` 内嵌窗口及页面到底部，触发阅读进度。
- 统一 `is_job_finished(cards_frame, idx)` 判断已完成任务点，避免重复处理。

## 模块二：答题链路

统一适配器接口：`query(question, q_type, config) -> answer | None`。

| 源 | 地址 | 凭证 |
|---|---|---|
| 自定义 | `tiku_config.api_url` | `token` |
| 题库海 | `api.tikuhai.com/search` | `thtoken`（可选） |
| 一之 | `cx.icodef.com/wyn-nb?v=4` | `yztoken`（可选） |
| free4 | `api.muketool.com/cx/v2/query` | 无 |
| 言溪 | `tk.enncy.cn/query` | `enncy_token`（可选） |

- 并发查询，单源 6s 超时，首个有效答案即用。
- 源健康度：连续 3 次失败本轮跳过。
- 答案归一化：字母、字母组合、选项原文、`正确/错误`、`#` 分隔填空。
- AI 兜底沿用 `query_ai_for_question`。
- 可选自动提交：`auto_submit`（默认 false）、`min_accuracy`（默认 0.8）；
  未达阈值或未开启时仍只调用 `noSubmit()` 暂存草稿。

## 模块三：稳定性与兼容

- 统一 `create_context()`：真实 Chrome UA、`navigator.webdriver` 兼容、语言/时区一致。
- 播放速率默认 1.0x，允许配置但上限 2.0x；不使用 16x。
- 音频/文档/测验任务级异常隔离与重试。
- 保持真实播放、心跳、防暂停、断点续跑、嵌套 frame 去重。

## 配置新增

```json
{
  "auto_submit": false,
  "min_accuracy": 0.8,
  "playback_rate": 1.0,
  "tiku_config": {
    "api_url": "",
    "token": "",
    "thtoken": "",
    "yztoken": "",
    "enncy_token": ""
  }
}
```

## 测试

- 单元测试：`_valid_answer`、`match_option_index`、`clean_question_text`、配置深合并。
- `py_compile` 与 `--help` 冒烟。
- 实机：单小节 `--start` 验证音频/文档/测验，避免影响正在运行的挂机进程。

## 非目标

- 不实现协议发包、不伪造心跳、不移植 16x 倍速。
- 不承诺规避平台检测，仅降低异常特征。
