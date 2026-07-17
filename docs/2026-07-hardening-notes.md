# 2026-07 大轮打磨记录与注意事项

本轮工作分两大块:**前端 dev 页/珊瑚橙皮肤打磨** 与 **后端安全/并发/资源审查修复**。
本文记录改了什么、为什么这么改、以及维护时的坑和注意事项。对应两个 commit:
`feat: 珊瑚橙皮肤全站统一…`(前端) 与 `fix: 后端安全/并发/资源审查修复…`(后端)。

> 面向未来的维护者和 AI:动到相关区域前先读对应小节的"⚠️ 注意事项",很多坑是反直觉的。

---

## 一、前端 · 珊瑚橙(claude-light)主题

### 1.1 全站字体跟皮肤走
- 珊瑚橙的字体**不是**逐个组件设的,而是在 `vibe/topbar.py` 的 `[data-theme="claude-light"]` 块里**覆盖全局 `--mono` 为 Inter**。`body { font-family: var(--mono) }` 是全站入口,所有 `var(--mono)` 一步全变。
- 原则:**字体跟皮肤走** —— 每个皮肤的 `--mono` 决定全站字体。珊瑚橙=Inter(人文无衬线),其他皮肤=各自等宽。

⚠️ 注意事项:
- `--mono` 这个变量名在珊瑚橙下名不副实(值是比例字体 Inter),这是有意的,别"修正"。
- **唯一例外**:xterm 终端本体字体写死在 `static/dev.js` 的 `new Terminal({ fontFamily: "ui-monospace,…" })`,不走 `--mono` —— 因为终端要渲染 TUI,字符必须严格等宽。改主题不影响它,但它的**颜色**跟主题走(见 1.2)。
- Inter 字体文件已自托管在 `static/fonts/`(`inter-latin.woff2`),`fonts.css` 里有 @font-face。

### 1.2 xterm ANSI 调色板接入(此前是断链 bug)
- 各主题在 `topbar.py` 定义了 `--ansi-0..15`,但历史上 `_xtermTheme()` **只传了 background/foreground/cursor,从没传 ANSI 调色板** → 所有主题的终端一直用 xterm 内置默认色。珊瑚橙浅底最先暴露:claude 的白字(ANSI 白/亮白)贴着米白背景看不清。
- 修复:`_xtermTheme()` 现在读 `--ansi-0..15` 喂给 xterm。

⚠️ 注意事项:
- `--ansi-N` 的值可能是嵌套引用如 `var(--red)`。`getComputedStyle().getPropertyValue('--ansi-1')` 读自定义属性拿到的是**未解析字面量** `"var(--red)"`,不能直接喂 xterm。代码用一个**探针 `<span>`** 把 `var(--ansi-N)` 落到真实 `color` 上再读回解析后的 `rgb()`。改这段务必保留探针逻辑。
- **truecolor 绕过调色板**:claude Code 的 TUI 大量用 truecolor / 高位 256 色画白字,这些写死 RGB、不走 ANSI 16 色调色板。改 `--ansi-*` 对它们无效。兜底是 `minimumContrastRatio`(见下)。
- **`minimumContrastRatio`**:`_xtermMinContrast()` 按 `--bg` 亮度判断,**仅浅底主题返回 7**(WCAG AAA),深底返回 1(不干预)。它让 xterm 对全色域(含 truecolor)自动把低对比前景压到可读。换肤时 `_refreshXtermTheme()` 会更新它并 `refresh()` 强制 canvas 重绘(canvas 渲染器需手动重绘才刷对比度缓存)。
- 珊瑚橙的 16 色用的是 Atom One Light 调色板;white(7)/brightWhite(15) 被刻意压深(#1a1a1a/#383a42),别改回浅色。

### 1.3 珊瑚橙的白色叠加补丁 + CSS 特异性坑
- 早期大量 `rgba(255,255,255,x)` 叠加(hover/边框/底槽/徽章)在深色主题下可见,但在珊瑚橙米白背景上不可见。已在 `static/dev.css` 的 claude-light 区(约 777–815)逐个补深色版覆盖。
- 新增 `--track-bg` 语义变量(珊瑚橙=`rgba(0,0,0,.06)`,深色走 fallback),统一 token 底槽色 —— 因为有一处底槽是 `dev.js` 里**内联 style**(内联特异性最高、CSS 盖不住),只能走变量。

⚠️ 注意事项:
- **CSS 特异性陷阱**:`.mobile-key-btn` 等的白底/字体是 `.dev-page.stream-mode .x`(特异性 0,3,0)设的。珊瑚橙覆盖若只写 `[data-theme="claude-light"] .x`(0,2,0)会**被压过失效**,必须带同前缀抬到 0,4,0:`[data-theme="claude-light"] .dev-page.stream-mode .x`。加珊瑚橙覆盖时先确认基础规则的特异性。
- 若之后还发现珊瑚橙下某处"白叠白看不见",大概率又是漏了一个 `rgba(255,255,255,x)` 没加 claude-light 覆盖。

---

## 二、前端 · dev 终端(xterm + PTY)

### 2.1 内容区底部横向滚动条自激振荡
- 现象:内容区底部一直闪、冒出滚动条。根因:一个 ResizeObserver 盯 `#xterm-container`(它 `overflow-x:auto`),而 `_ptyFitResize` 的 fit 每次多算 1-2 列瞬时溢出 → 横滚条出现 → 改变 contentRect 高 → 再触发 fit → 补正去溢出 → 滚条消失 → 高又变 → …自激环。
- 修复:ResizeObserver 改盯 **flex 父 `#xterm-wrap`**(绝对定位子的内部滚动条压不到父;父高只随 flex 重排变),断开反馈环。并把 `#xterm-container` 的 `overflow-x` 从 auto 改 **hidden**(瞬时溢出会被补正,不该露横滚条)。

### 2.2 切换项目的闪烁 / loading 体验
- 切换走 `_connectPtyWs`:单例 `_ptyTerm` `reset()` 清屏 → 重连新 PTY → 等 tmux 重推当前屏。这段过程会多次 fit/resize,肉眼是"闪 + 各种滚动条"。
- 修复:
  - **淡入过渡**:切换时给终端加 `.term-switching`(opacity:0),藏住 reset+多次 fit 的抖动,稳定后淡入。
  - **收敛式 fit**:`_fitThenReveal()` 用 rAF 反复 fit + 溢出补正,直到 cols×rows 连续两帧不变(布局稳)才淡入 —— 比死等固定时长快,且淡入后无 fit 跳动("固定闪两下"就是固定延时 fit 落在淡入后造成的)。
  - **首帧即显**:淡入不死等,首帧内容 write 到达就 reveal(见 onmessage),tmux 多快就多快显示。
  - **竞态守卫**:`_termSwitchSeq` 每次连接自增,淡入回调只认最新序号,防快速连切时旧回调误淡入。

⚠️ 注意事项:
- 这条路**没有本地显示缓存**,切回内容仍靠 tmux 重推(`_paneSnapshots` 只用于切换器预览小图,不用于恢复画面)。真·即时切换需每 target 一个独立 xterm 实例(多实例),是架构改动,当前未做。

### 2.3 末行被输入栏/快捷键栏遮挡
- 根因:`#xterm-container` 的 `padding-top:4px` 会"骗高" FitAddon,让它**纵向多算行**,canvas 底部溢出被不透明输入栏盖住。横向多算列早有 drop-cols 补正,**纵向一直没有**。(最初删掉的 `margin-bottom:14px` 是用一整行余量掩盖它,删了就暴露。)
- 修复:`_ptyFitResize` 和 `_fitThenReveal` 都补上**纵向溢出补正**(测 `scrollHeight - clientHeight`,溢出就动态减行),与横向对称。不溢出不减 → 用满高度、无死留白。

### 2.4 会话历史入口 & 移动端项目名
- 会话历史入口移到 topbar 右上角 icon(`#topbar-hist-btn`),桌面和移动端统一;桌面选中终端时 `openDetail` 显示它(返回/切换仍是移动端专属)。删掉了原来 `dev_page.py` 里页面内的文字"历史"按钮。
- 移动端 logo 旁显示当前项目名:走 `#topbar-project-name`(自带 max-width+ellipsis)。

⚠️ 注意事项:
- 移动端**不要**再把项目名塞进 `.topbar-page-title` —— `body.detail-locked`(移动详情态)会把 page-title `display:none` 藏起来省 topbar 空间,塞进去就看不见(这正是之前的 bug)。

### 2.5 性能
- 拖拽排序 `_computeDrop`、tab 切换器透视 `_updateTabPerspective` 改**读写分离**(先读完所有 rect 再统一写),消除逐项 读→写→读 的 layout thrashing。
- `_ptyFitResize` 的 80ms 溢出补正 timer 用 `_fitCorrectTimer` 存句柄,进入先 clear,连续 resize 不堆叠。

### 2.6 清理:移动端"智能回车"
- `_smartEnter`(移动端 ↵)原想检测灰色幽灵补全、有则自动 Tab 采纳,但依赖已退役的快照变量 `_sbLastData`(全仓无赋值),**一直失效、只发裸回车**。已简化为普通回车。要采纳灰色建议用快捷键栏的 Tab。

---

## 三、后端 · 安全

### 3.1 子账号授权撤销后仍能操作旧 pane【已修】
- 授权撤销后进程不杀(仍在 sub session 里跑)。只读/历史端点做了 `account_can_access_project` 校验,但**三个写端点漏了**:WS `/ws/terminal/{target}/pty`、`/api/terminals/{target}/send`、`/api/terminals/{target}/respawn`。子账号可拿到旧项目的可写终端/发指令/杀进程。
- 修复:三处都补 `_sub_target_project(...) + account_can_access_project(...)` 双校验,与只读端点一致。

⚠️ 注意事项:
- **新增任何子账号可达的写终端/PTY 端点,必须同时做这两个校验**。只校验 `_sub_target_project`(只验 target 属于自己 session)不够,还要验项目授权。
- 治本应在撤销授权时 kill 掉对应 window(当前未做,靠端点校验兜)。

### 3.2 剩余安全项(未改,设计权衡/需单独评估)
- WS token 走 query string,会进 cloudflared/反代日志(admin token = 永久密码哈希)。根治需改一次性 ticket,动静较大。
- `save_project_config` 的 raw_yaml 无 schema 校验(admin-only,写恶意 restart_cmd 后触发重启=RCE,属已鉴权后提权)。
- `_run_shell` 黑名单可绕过(admin-only 聊天工具,别当安全边界)。
- `/tmp/mira-uploads`:已加后台定期清理(每小时清超 24h 的文件,`_cleanup_uploads_loop`),缓解了"只增不清"堆留;但**目录/文件仍是默认权限(世界可读)**,若要更严需在写入时 chmod 0600/目录 0700。
- 分享 token 无过期(链接外泄则持续可读)。

---

## 四、后端 · 并发与一致性

### 4.1 SQLite busy_timeout【已修】
- `history_db._conn` 加 `PRAGMA busy_timeout=5000`、`cache_db` 的 connect 加 `timeout=5`。此前没设 → 多线程并发写(FastAPI 线程池 + watchfiles + rescan + backfill 等多个写线程)直接 `database is locked` 而非等待。

### 4.2 vibe.yaml 原子写 —— 重要规范【已修 19 处】
- **所有对 vibe.yaml 的"读-改-写"必须走 `_mutate_vibe_yaml(mutate_fn)`**(它在 `_vibe_yaml_lock` 内 read→改→write)。此前 main.py 有 19 处散开的 `_read_vibe_yaml + 改 + _write_vibe_yaml`,并发下互相覆盖(accounts/keys lost update)。已全部收口。

⚠️ 注意事项(未来写 vibe.yaml 必读):
- **新增任何改 vibe.yaml 的路径,一律用 `_mutate_vibe_yaml`**,不要自己 `_read_vibe_yaml` + `_write_vibe_yaml`。
- 读前的校验(`_is_admin`、参数解析)留在锁外;只把 read-modify-write 包进 mutate。
- **穿插的非 vibe.yaml 副作用**(写别的文件、subprocess、刷新缓存、`fetch_all_balances`、`new_session` 等)要留在 `_mutate_vibe_yaml` **调用之后**、且确认不依赖锁内状态、顺序无关。参考 `save_settings` / `feishu_callback` / `add_remote_host_endpoint` 的写法。

---

## 五、后端 · 资源与护栏

- **PTY 连接数上限护栏**:`_PTY_MAX_CONN=24`,`_pty_active_conns` 计数 `+1/-1` 由本地 PTY 分支的**同一 try/finally 严格配对**。挡住重连风暴无界创建 tmux 会话+子进程。远程代理连接不占本地资源、不计入。
- chat 本地模型 `urlopen` timeout `120→30s`,减少慢请求占线程池。
- 终端写侧 `os.write`(数据)失败 → break 收口;resize `ioctl` 失败 → 忽略(数据通道的 os.write 负责退出),与读侧 `_read_master` 对称。
- `_feishu_states` 登录时清理过期项(未完成授权的 state 原来只增不减)。

⚠️ 注意事项 / 已知限制:
- **护栏上限是宽松的**:check 与 +1 之间有一次 await(建 viewer),并发窗口内上限可能被短暂突破几个 —— 目的是防"无界",不是精确限流,够用。
- **PTY 读仍用 asyncio 默认线程池跑阻塞 `os.read`**,每条活跃连接常驻占 1 个 worker(池 ≈12)。`chat` 的 `to_thread` 也用同一个默认池 —— 十几条终端 + 几个聊天会共振占满,拖累其他 `to_thread` 路由。**根治(master fd 改 `loop.add_reader` 非阻塞)本轮按决定暂缓**(动核心终端链路、难自动测,护栏已挡最坏情况)。日常并发不高时够用;若将来并发上来,这是首要优化点。

---

## 六、后端 · 正确性

- `init_db` 历史去重后**一并清 `messages_fts` 孤儿行**(`DELETE FROM messages_fts WHERE message_id NOT IN (SELECT id FROM messages)`)—— 否则搜索命中已删除消息的幽灵结果。`messages_fts` 是手动同步的普通 FTS5 表,删 messages 必须同步删 fts。
- 项目卡片"7天/30天会话数"改按 **distinct session_id** 计。原来对 `daily_stats` 行数 `+1`,而 daily_stats PK 是 `(session_id, date)`,跨天会话被重复计、数字偏高。

---

## 七、剩余未做项(可选,按需再点)

- **性能**:`codex_stats` 三重扫盘+无缓存(会话文件多时统计页慢);`_check_service_statuses` 串行探活(项目多且端口普遍不通时 status 延迟)。
- **边缘竞态**:`_isMobile` 加载时算一次,桌面↔移动跨临界(拖窗/iPad 旋转过 900px)不更新;`newWindow`/`selectSubProject` 快速连点两个项目抢 `_currentTarget`(无 `_termSwitchSeq` 级守卫)。都需刻意并发操作才触发。
- **Low 安全项**:见 3.2。

---

## 八、验证 / 测试

- 后端改动全程 `pytest tests/`(195 passed)兜底,覆盖 accounts/config/subaccounts/history_db/security 等。
- 但**安全修复(子账号越权)和 PTY 护栏、以及前端终端行为难以自动测**,需实机验证:
  1. 正常开终端仍工作(护栏 24 上限不误拦)。
  2. 子账号撤销授权后确实连不上旧 pane。
  3. 珊瑚橙下终端白字可辨、各处 hover/按钮可见;切换项目无闪无横滚条;末行不被输入栏盖。
- 回退:前端/后端是两个独立 commit,可用 `git revert <hash>` 单独回退一侧。

---

## 附:已知过时文档

- `README.md` 仍写 "full PTY terminal via ttyd + tmux",但 **ttyd 早已退役**,现为 xterm.js + PTY 直连(WebSocket `/ws/terminal/{target}/pty`)。待更新。
