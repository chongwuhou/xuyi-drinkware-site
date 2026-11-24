# XUYI website mandatory change policy

> **唯一执行入口：** 具体操作统一按 [XUYI 网站统一执行手册](docs/XUYI_OPERATIONAL_RUNBOOK_ZH.md)。本文件的原则优先级不变；带日期的历史说明仅供追溯。

Before editing this project, read [PROJECT_CHANGE_POLICY.md](PROJECT_CHANGE_POLICY.md).
This applies to localGPT, Codex, other coding agents and human maintainers.
## P0：站长永久指令——所有批量变更只允许在模板 / 正式数据源实施（每次任务开工前必读）
**优先级高于任何历史脚本、旧审计说明、临时实现与建议。适用于今后所有 SEO、GEO、多语言、容量、产品、博客、图片、内链、OG/Schema、样式和后台批量任务。**

1. **每次执行任务，第一步必须阅读本文件和 `PROJECT_CHANGE_POLICY.md`**，明确涉及的共享模板、实际字段所有者（Cloudflare D1/CMS、项目权威数据文件）及正式渲染入口。即使用户只说「继续、批量、修复、上线」，也不能跳过。
2. **凡是批量内容/布局修改，先修改共享模板/组件/正式源数据或 D1/CMS 数据源，再由标准构建生成所有页面。** 不允许把页面已经渲染完后的字符串替换、手工逐页编辑、直接写 `dist/`、线上 HTML 或 R2 缓存当作实施方案。源文件里的「循环改生成 HTML」同样**不自动等于模板化**；应把逻辑前移到模板/正式渲染器或 CMS 字段。
3. **允许用生成页做一次性诊断和隔离测试**，但测试数据必须隔离、可还原、不可发布；测试一结束，必须回到模板或数据库完成正式修复，再从干净源重新全量构建；绝不把测试产物当最终成果。
4. **后台 D1/CMS 用户编辑拥有最终优先权。** 对标题、描述、翻译、文章、图片、内链、容量等必须检测字段是否在后台已更新；用户手动改写不能被静态回退表、旧数据指纹、构建后 HTML 替换覆盖。
5. **批量任务完成证据必须包含**：源模板或数据库/源字段的具体修改位置、真实 CMS 编辑优先测试、D1 当前已发布语种/相关路由回归、两次干净全站构建、无重复注入与新增型号不被旧总数卡住、生产 CI 和线上核验（若获准部署）。若只是改了产物或历史后处理脚本，必须明确标记「尚未真正完成」。
6. **已有直接在 `dist/` 后处理 HTML 的历史脚本属于待迁移旧债，不是今后新增或延续这种做法的许可。** 今后触及相关功能，应优先把其结果迁移进共享模板/正规数据层，并移除冲突的后处理入口；不可用「后处理脚本纳入 build 流程」冒充符合这一条指令。
7. **用户无须再次提醒。** 完成每个任务前必须自检本规则；冲突时以本 P0 规则为准，先拒绝不持久的捷径并选择模板/CMS 方案。



1. Make every correction in the **shared source template, CMS-aware data,
   reusable rendering function, or version-controlled build pipeline**.
   Never count editing dist output or already deployed HTML as a fix.
2. Cloudflare **D1/CMS owner edits are authoritative**. Later edits to SEO
   titles, translations, Blog text, links and product images must not be
   overwritten or rejected by earlier cleanup scripts.
3. Make source transformations **idempotent and tolerant of existing
   owner-selected content**. Do not require old image URLs or previous
   page totals to remain unchanged forever.
4. Rebuild the entire site from source and test a second rebuild; validate
   all D1-configured publish-ready locales, canonical/hreflang, links, inquiry functionality and
   representative live URLs before declaring a production release complete.
5. Keep G-series factory model status intact. Never invent product data,
   certifications, physical factory evidence or exact-SKU photographs.
6. Make the smallest change that fixes the proven issue. Do not modify
   unrelated front-end design, D1 inquiries or R2 original media.

If a legacy script violates these rules, fix that script and add a regression
test reproducing a realistic owner/CMS update before publishing.

7. **永久规则 / Permanent rule:** 用户后续随时可能在后台改图片、SEO、语言、内链和文章，或增加新型号与语言。所有修复必须改正式源模板/数据/CMS 感知构建器，并随每次全站重建自动复现；严禁把改动 `dist/`、手工线上编辑或临时修补当成完成。发布前验证「后台修改优先、重复运行幂等、新增内容不被旧计数卡住」。必须把回归测试接入自动发布门禁。

8. **海外零售容量规格永久规则（2026-10-14 修订）：**工厂准确毫升容量始终保留在参数表。海外营销 SEO、产品卡片采用 `data/retail-oz-size-classes.json` 的海外常用 oz 规格档位（例如 800ml→28 oz class、1000ml→32 oz class、1200ml→40 oz class、2000ml→64 oz class），**不得当作精确 US fl oz 等式**。必须明确标注 size class/approximate，实际容量按源数据 ml 为准。多容量逐一标注，异常 2506、未知 G 型号不猜测。Tritan / BPA Free 用于定制材料询盘，不冒充现有材质或认证；后台 SEO 修改优先保留。唯一构建入口 `scripts/source_catalog_capacity_oz.py` + 审核规格表 + 测试。


## 博客新文章编辑发布规则（2026-10-15，永久执行）

**此条是编辑质量规则，不可用自动注入、整页 HTML 计数或仅通过 CI 伪装已经完成。** 每篇今后新发布或实质改写的 XUYI 博客，**正文中自然分散链接 2–5 个真实、主题相关且资料可信的不同产品型号详情页**；**正文结束处由编辑挑选 2–3 篇直接相关的其他博客文章作为“相关阅读”**。不计入页头、导航、侧栏、页脚和未人工挑选的自动推荐；同型号重复链接只算一次。逐条打开核对 URL、型号、主题和对应语言路径，禁止编造规格和认证。**编辑在 CMS 正式正文中完成并审核后方可发布**；CMS 人工修改优先。此前 16 篇不能凭模板推荐模块或全页链接统计被宣称已完成编辑整改。具体操作规范：`docs/BLOG_EDITORIAL_PUBLISH_CHECKLIST.md`。


## P0 永久补充：B2B 博客图片与正文场景一致（2026-10-29 站长再次明确）

**今后每篇 B 端文章的封面必须一眼对应标题的行业/采购场景/目标读者；不能拿“水杯通用素材”随便配，不能用旧 SKU 图或同一图片跨行业凑数。** 先完整读文章，再实际看图，再逐篇记录行业、画面、用途、真假声明、版权来源、SHA-256 和审核结论。只凭提示词/图片文件名/CI 技术检查视为**未审核**。以站长 2026-10-29 亲选的仓储员工、旅行零售货架、共享办公会议三幅情境图作为选题契合度范例；人物场景不得冒充真实 XUYI 产品型号。

**图片统一 1200×800、3:2、WebP，30–350 KB，清晰无错位与水印。** AI 新文章视觉评审 5 项各≥4、总分≥22/25；不合适即重新选图，绝不自动拿通用图兜底。所有 AI 批量发布先过 `scripts/test_blog_cover_editorial_standard.py` 正式 CI 门禁，再按 D1/CMS 优先完成 R2、所有已发布语种和线上核验。详细不可省略规定见 `docs/BLOG_COVER_VISUAL_STANDARD.md`；审核记录 `data/blog-cover-editorial-approvals.json`。站长通过后台主动换的图始终优先，不允许旧源覆盖。

## 永久执行标准（2026-11-05 定稿：简单、统一、可重复）

核心原则：先读本文件、PROJECT_CHANGE_POLICY.md 和项目圣经；Cloudflare D1/CMS 是运行时唯一事实源。能在正式数据源完成就不另造接口，能复用现有构建入口就不增加新层。所有批量处理必须幂等、条件更新、保留人工修改、可验证、可回滚。

### AI/工具发布与 D1/R2 唯一写入门禁（2026-11-05）

产品、博客、评价、翻译和图片等业务数据必须写入 Cloudflare D1/CMS；图片必须先进入 R2，再由 D1 保存路径、ALT、语言和引用关系。AI 只能生成待审核草稿、翻译初稿和审计结果，不能直接发布或编造事实；工具只能使用已鉴权的正式 D1/CMS、R2 入口，默认 dry-run，条件写入，保留人工值，记录 publish revision。严禁直接改 dist、线上 HTML、Pages 成品或 R2 缓存。完整门禁见 [项目圣经/统一内容发布与翻译审计标准.md](项目圣经/统一内容发布与翻译审计标准.md)。


### 产品 SEO

- 每个型号 × 语言独立维护 title、H1、description、OG 和正文；标题与 H1 必须差异化，按真实产品特征组合 B2B、wholesale、OEM、manufacturer/factory、颜色、真实材质、场景和长尾词，禁止整站复用同一句。
- 容量保留工厂真实 ml；海外表达同时给出经审核的 approximate/size class oz，不写成精确等式。没有来源的材质、认证、尺寸、颜色、MOQ、工厂证据不补造。
- 塑料可作为定制方向；Tritan、BPA-free 等只能写成可询价定制，不得冒充现有 SKU 材质或认证。
- D1/CMS 已有人工值优先；只写缺失、旧模板值或明确允许改写的字段。重复执行不得回退、重复插入或覆盖用户修改。

### 博客与评价

- 多语言 Blog 列表顺序必须以同一次 D1 snapshot 的完整 published slug 顺序为唯一依据。生产默认走 Cloudflare Pages 静态构建：英文列表与 page:/blog/ 的所有已发布语种都从 D1/CMS snapshot 生成，静态列表必须包含 D1 中全部 `status='published'` 的文章，不能只渲染仓库源目录中的旧文章；源目录仅在 D1 快照缺失时作安全回退。卡片只按 D1 顺序重排并原样保留卡片 HTML；动态 `functions/blog/[[path]].js` 仅在显式设置 `XUYI_BLOG_RUNTIME_MODE=dynamic` 时作为备用入口，且必须使用同样的 `COALESCE(published_at,updated_at) DESC,slug ASC` 查询。缺卡、重复卡、额外卡或 slug 不匹配必须停止发布。

- 博客正文在 D1/CMS 编辑并审核；自然放入 2–5 个真实相关产品链接，结尾人工选择 2–3 篇相关阅读，所有 D1 当前已发布语种路径同步检查。图片必须先看正文与画面，记录来源、SHA 和审核结论，不用通用图、旧 SKU 图或虚构工厂/客户证据。
- 评价只接受来源可核验、能精确映射 SKU、未重复的真实内容，并保存 fingerprint、source 和审核状态。AI 只能做草稿、翻译、去重、格式整理与风险筛查；禁止生成虚假体验、补造型号参数或把未经人工/来源审核的内容写入 D1。
- AI 的作用是提效，不是替代事实核验；涉及发布的最终内容须按来源和后台人工修改复核。所有追加或修改采用条件写入，绝不删除、覆盖用户已有数据。

### 固定发布流程

D1/CMS snapshot → 读取当前值和字段所有者 → 条件写入正式数据源 → bump publish revision → 两次干净构建/回归 → 检查 D1 当前已发布语种、canonical/hreflang、sitemap、重复卡片与链接 → 核验代表线上路由。失败停在 CI，不发布临时产物；不要用 dist、线上 HTML 或一次性后处理替代正式修复。

### 阶段二 Blog SEO 永久执行契约（2026-11-17）

- Blog 详情页的 FAQPage、BreadcrumbList、首图 eager/宽高、正文图片几何属性和 sitemap lastmod 均由共享渲染器读取 D1 快照自动生成；新文章只要进入 D1 的 published 数据，不能再新增人工补丁或静态页面特判。
- 多语翻译内容只能通过 D1/CMS 正式字段修改；已核实的术语错误使用可审计、条件写入、可重复执行的 D1 迁移完成，禁止在模板中硬编码翻译替换。后台再次编辑后，以后台值为准。
- scripts/test_phase2_blog_seo.py 是发布门禁：按后台配置语种、D1 已发布文章和当前 sitemap 动态核验，另拦截已知跨语种术语回归。新增语种或文章不依赖固定数量。
- 阶段二仍未把 TDK 长度提示、外部证据和主题去重变成自动篡改；这些属于 D1/CMS 编辑审核项，必须有真实来源和新增信息后再写回，不能靠截断、伪造引用或生成 HTML 代替。



## GEO 与多语 Blog 结构化数据永久执行契约（2026-11-17）

- Blog 的 JSON-LD `keywords` 必须由共享渲染器 `seo_structured_components.py` 从最终 D1/CMS 页面内容派生：标题、描述、H1/H2/H3 和 FAQ 问题。英语缺失时自动补齐；非英语必须使用当前语种最终页面内容，禁止继承英语关键词、固定五语列表或固定文章数量。
- GEO 证据只能来自文章自身已审核的 D1/CMS `evidence`、深度研究或正文引用字段，由共享渲染器按最终页面内容输出；禁止恢复旧的字符截取式 `blog_geo_evidence.py` 启发式区块，也不能对 `dist/`、线上 HTML 或缓存做后处理。没有明确来源的文章不伪造证据区或 citation，新 D1 文章、新语种沿用同一可见内容与 JSON-LD 一致性门禁。
- 量化内容只能使用文章最终可见正文中已经存在、可核验的数字（容量、尺寸、比例、交期、包装数量等），由渲染器提取到可见证据区和 JSON-LD `additionalProperty`；没有真实来源时必须明确提示买家索取/核对，严禁补造 MOQ、耐温、壁厚、交期、认证或工厂实测数据。
- 只有文章最终可见正文包含已审核来源时，才输出对应 `citation` 和可见 GEO 证据区；FAQPage 只能对应页面上真实可见且完整的问答。`scripts/test_phase2_blog_seo.py` 按 D1 当前 published 文章和后台配置语种动态核验，不依赖固定数量。后台再次修改正文、标题、描述或翻译后，以 D1/CMS 值为准，下一次静态构建自动重算。
- 本规则解决的是关键词本地化、证据边界、引用和结构化输出；TDK 过长、主题蚕食和缺少真实正文数据仍必须通过 D1/CMS 人工审核后写回，不能用截断、通用话术或模板伪造“已优化”。


## 近期问题的固定复盘入口

遇到重复 Bug、返工、回滚、缓存错觉、构建失败或多次修改同一问题，必须按 [XUYI 网站统一执行手册](docs/XUYI_OPERATIONAL_RUNBOOK_ZH.md) 第 12 节的根因分类和门禁执行；不能只做局部补丁。

