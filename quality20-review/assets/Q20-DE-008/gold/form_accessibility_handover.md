# 星芒社区居家养老服务预约表单 — 设计与开发交接说明

> **文档版本**：v1.0  
> **编制日期**：2024-05-15  
> **适用标准**：W3C WCAG 2.2（2023-10-05 Recommendation）+ WAI Forms Tutorial  
> **编制依据**：`S01_WCAG22_20231005_原文摘录.docx`、`primary_forms.txt`

---

## ⚠️ 合规范围声明

**本文档仅针对"星芒社区居家养老服务预约与信息采集表单"（`community_form_workflow.json` 中描述的4步骤流程）的无障碍改造与验收。**

- 本文档不构成、不代表、不暗示星芒社区网站或任何子产品"全站通过WCAG认证"。
- 合规目标仅限于本表单在改造后达到 WCAG 2.2 AA级（含部分AAA级增强），不扩展到其他页面或组件。
- 任何其他页面、功能模块的无障碍状态需在各自改造文档中独立评估。

---

## 1. 设计原则：面向60岁以上老年用户

| 原则 | 说明 |
|------|------|
| **减少认知负荷** | 避免复杂密码记忆、消除冗余输入、提供明确进度指示 |
| **增大容错空间** | 即时校验、可撤销操作、宽松超时策略 |
| **适配运动退化** | 放大可点击区域、消除拖拽操作、提供替代操作路径 |
| **支持辅助技术** | 正确的语义标签、高对比度焦点指示、屏幕阅读器兼容 |
| **多元认证兜底** | 考虑无智能手机、无法接收短信等极端场景 |

---

## 2. 逐项缺陷分析与改造方案

### 2.1 步骤1：身份验证 — 可无障碍认证

**适用准则**：WCAG 2.2 SC 3.3.8 Accessible Authentication (Minimum) — **AA级**

> 原文要求："A cognitive function test (such as remembering a password or solving a puzzle) is not required for any step in an authentication process unless that step provides at least one of the following: Alternative / Mechanism / Object Recognition / Personal Content."

#### 当前缺陷

1. **8位复杂密码要求**：要求包含大小写字母、数字和特殊字符，对认知退化的老年人构成不可逾越的认知功能测试。
2. **无替代登录方式**：`alternative_login: "无"`，完全依赖记忆密码。
3. **5分钟超时且无预警**：`idle_timeout_seconds: 300`，超时后"清空所有已输入数据并跳转至登录页"，对操作速度慢的老年人极为不利。
4. **未声明支持密码管理器**：违反 Mechanism 条款中"support for password entry by password managers to reduce memory need"。

#### 改造方案

**方案A（推荐）：提供不依赖认知记忆的替代认证方式**

| 认证方式 | 实现要点 | 适用场景 |
|----------|----------|----------|
| 手机短信验证码 | 6位数字，有效期5分钟；发送后在页面显示倒计时 | 有手机的用户 |
| 生物识别（指纹/面容） | 通过 WebAuthn API 实现 | 支持生物识别的设备 |
| 社区实体卡刷卡 | 通过 NFC 读卡器或二维码扫描 | 无手机/不会操作的老人 |
| 线下协助预约通道 | 提供社区电话热线和上门协助预约入口 | 所有场景的兜底方案 |

**方案B（最低限度）：若必须保留密码登录**

- 允许使用密码管理器：确保密码输入框不禁用浏览器的自动填充功能。
- 取消密码复杂度强制要求，或降至最低限度（如仅要求6位数字）。
- 禁止阻止粘贴（`autocomplete="current-password"`，不设置 `onpaste="return false"`）。

**代码示例**：

```html
<!-- 认证方式选择 -->
<fieldset>
  <legend>请选择登录方式</legend>
  
  <div class="auth-option">
    <input type="radio" id="auth-sms" name="auth-method" value="sms" checked>
    <label for="auth-sms">手机短信验证码</label>
  </div>
  
  <div class="auth-option">
    <input type="radio" id="auth-biometric" name="auth-method" value="biometric">
    <label for="auth-biometric">指纹/面容识别</label>
  </div>
  
  <div class="auth-option">
    <input type="radio" id="auth-card" name="auth-method" value="card">
    <label for="auth-card">社区服务卡刷卡</label>
  </div>
  
  <div class="auth-option">
    <input type="radio" id="auth-password" name="auth-method" value="password">
    <label for="auth-password">密码登录（可使用密码管理器自动填充）</label>
  </div>
</fieldset>

<!-- 密码输入区域（仅在选中密码登录时显示） -->
<div id="password-section" hidden>
  <label for="password">密码</label>
  <input type="password" id="password" name="password"
         autocomplete="current-password"
         aria-describedby="password-hint">
  <p id="password-hint">可使用密码管理器自动填充，或点击"显示密码"查看输入内容。</p>
  <button type="button" id="toggle-password">显示密码</button>
</div>

<!-- 线下协助兜底 -->
<p class="help-fallback">
  如以上方式均不方便使用，请拨打社区服务热线：
  <a href="tel:400-XXX-XXXX">400-XXX-XXXX</a>
  或前往社区服务中心由工作人员协助预约。
</p>
```

**超时处理改造**（结合 WAI Forms Tutorial 的超时指南）：

```html
<!-- 超时前2分钟显示警告弹窗 -->
<div id="timeout-warning" role="alertdialog" aria-labelledby="timeout-title" aria-describedby="timeout-desc" hidden>
  <h2 id="timeout-title">会话即将过期</h2>
  <p id="timeout-desc">您已有一段时间未操作。为保护您的信息安全，会话将在 <span id="countdown">120</span> 秒后结束。</p>
  <button id="extend-session" autofocus>继续操作（延长时间）</button>
  <button id="end-session">结束并退出</button>
</div>
```

- 默认超时延长至 **30分钟** 或完全取消（如仅在前端缓存数据、提交时再验证会话）。
- 超时前 **2分钟** 弹出可访问的警告对话框，包含明确的倒计时和一键延长按钮。
- 超时后不清空数据，而是提供"恢复上次填写内容"选项。

---

### 2.2 步骤3：服务选择 — 消除冗余输入

**适用准则**：WCAG 2.2 SC 3.3.7 Redundant Entry — **A级**

> 原文要求："Information previously entered by or provided to the user that is required to be entered again in the same process is either: auto-populated, or available for the user to select. Except when: re-entering the information is essential, the information is required to ensure the security of the content, or previously entered information is no longer valid."

#### 当前缺陷

步骤3要求用户"再次输入姓名和身份证号以确认身份"（`re_enter_name`、`re_enter_id`），而这两个字段在步骤2已完整填写。此冗余输入对老年人构成不必要的认知和体力负担。

此处的"身份确认"并非安全必需（已在步骤1完成认证），也不属于信息失效场景，因此不满足例外条件。

#### 改造方案

**方案：自动填充 + 只读确认视图**

将步骤3中的两个手动输入字段替换为只读信息展示区域，用户仅需确认信息正确：

```html
<!-- 替代原有的重复输入字段 -->
<section aria-labelledby="identity-confirm-title">
  <h2 id="identity-confirm-title">确认您的身份信息</h2>
  
  <dl class="info-summary">
    <dt>姓名</dt>
    <dd id="confirmed-name"><!-- 由步骤2自动填充 --></dd>
    
    <dt>身份证号</dt>
    <dd id="confirmed-id"><!-- 脱敏显示，如 310***********1234 --></dd>
    
    <dt>手机号</dt>
    <dd id="confirmed-phone"><!-- 脱敏显示，如 138****5678 --></dd>
  </dl>
  
  <button type="button" id="edit-identity">信息有误？返回修改</button>
  <!-- 点击后跳转到步骤2，保留已填数据 -->
</section>
```

**字段映射关系**：

| 步骤2字段ID | 步骤3展示元素 | 自动填充方式 |
|-------------|---------------|-------------|
| `full_name` | `#confirmed-name` | 前端状态管理直接读取，全文展示 |
| `id_card` | `#confirmed-id` | 前端脱敏后展示（中间段以*代替） |
| `phone` | `#confirmed-phone` | 前端脱敏后展示（中间4位以*代替） |

**异常处理**：

- 如果用户在步骤3发现信息有误，点击"信息有误？返回修改"按钮后，跳转回步骤2且保留所有已填数据，无需重新输入。
- 如果会话数据失效（如超过24小时），系统提示用户重新验证身份，而非静默失败。
- 如果用户在步骤2使用了自动填充（如身份证OCR识别），在步骤3同样展示OCR识别结果，并允许手动修正。

---

### 2.3 步骤3：服务选择 — 消除拖拽操作

**适用准则**：WCAG 2.2 SC 2.5.7 Dragging Movements — **AA级**

> 原文要求："All functionality that uses a dragging movement for operation can be achieved by a single pointer without dragging, unless dragging is essential or the functionality is determined by the user agent and not modified by the author."

#### 当前缺陷

当前设计使用"长按并拖拽卡片"来调整服务优先级。此操作对以下老年人不可用：

- **运动障碍用户**：无法精确控制拖拽起止位置
- **使用辅助设备的用户**：开关设备、头指针、眼动追踪均不支持拖拽
- **触屏不灵敏设备**：老旧平板电容屏对长按手势识别率低

服务排序不属于"essential"（本质需求），因为排序目的完全可以通过替代交互实现。

#### 改造方案

保留卡片视觉展示，但为每张卡片增加"上移"和"下移"按钮，通过单击即可完成排序：

```html
<div class="service-card" data-service="meal" role="listitem">
  <h3>助餐服务</h3>
  <p>提供每日三餐配送服务</p>
  
  <div class="card-actions">
    <button type="button" class="move-up" aria-label="将助餐服务上移一位">
      ▲ 上移
    </button>
    <button type="button" class="move-down" aria-label="将助餐服务下移一位">
      ▼ 下移
    </button>
    <!-- 首项时"上移"按钮禁用并 aria-disabled="true" -->
  </div>
  
  <span class="priority-badge" aria-label="当前优先级：第1位">优先级 #1</span>
</div>
```

**实现要点**：

- 每张卡片的"上移/下移"按钮尺寸不小于 44×44 CSS pixels（超过最低24×24标准，为老年用户提供更大触控区域）。
- 当服务位于列表顶部时，"上移"按钮自动 `disabled` 并设置 `aria-disabled="true"`。
- 排序变化后，通过 `aria-live="polite"` 区域播报当前排序结果。
- 拖拽仍可作为**附加**交互方式保留（供熟练用户），但不可作为唯一操作路径。

```html
<!-- 排序变化播报区域 -->
<div aria-live="polite" aria-atomic="true" class="sr-only" id="sort-announcement"></div>
```

```javascript
// 排序后更新播报
function announceSortChange(serviceName, newPosition) {
  document.getElementById('sort-announcement').textContent = 
    `${serviceName}已移动到第${newPosition}位`;
}
```

---

### 2.4 全局：一致的帮助入口

**适用准则**：WCAG 2.2 SC 3.2.6 Consistent Help — **A级**

> 原文要求："If a Web page contains any of the following help mechanisms, and those mechanisms are repeated on multiple Web pages within a set of Web pages, they occur in the same order relative to other page content."

#### 当前缺陷

当前流程无统一帮助入口。仅在步骤2有一个"忘记密码？"文字链接，且其他步骤完全没有帮助机制。老年用户在任一步骤遇到困难时，无法便捷获取帮助。

#### 改造方案

在表单所有4个步骤的**相同位置**（建议页面右下角固定悬浮区域，或页脚固定位置）提供帮助入口，且包含以下多种联系方式：

```html
<!-- 在所有步骤的页面底部或右下角，保持一致的DOM顺序 -->
<nav aria-label="帮助与支持" class="help-section">
  <h2>需要帮助？</h2>
  <ul>
    <li><a href="tel:400-XXX-XXXX">📞 拨打服务热线：400-XXX-XXXX</a></li>
    <li><a href="/help/faq">📖 常见问题解答</a></li>
    <li><a href="/help/video-guide">🎬 观看操作视频指南</a></li>
    <li><a href="/help/chat">💬 在线客服（工作时间 8:00-18:00）</a></li>
    <li><a href="/help/offline">🏢 前往社区服务中心</a></li>
  </ul>
</nav>
```

**要求**：

- 该帮助区域在所有4个步骤中**位置一致**（相同DOM顺序，建议视觉位置为页面右下角或页脚）。
- 帮助入口的链接文本清晰明确，避免使用"点击这里"等模糊表述。
- 服务热线使用 `tel:` 协议，支持一键拨号。

---

### 2.5 步骤4：提交按钮 — 目标尺寸

**适用准则**：WCAG 2.2 SC 2.5.8 Target Size (Minimum) — **AA级**

> 原文要求："The size of the target for pointer inputs is at least 24 by 24 CSS pixels."

#### 当前缺陷

当前提交按钮为"20×20 CSS pixels 的圆形图标"，低于 24×24 CSS pixels 的最低要求。对于运动控制能力退化的老年人，20px 的目标极易误触或无法点击。

此外，该按钮为"icon_only"类型且"无 aria-label 设置"，屏幕阅读器无法识别其用途。

#### 改造方案

**设计Token修正**：

```css
/* 修正前 */
:root {
  --button-height: 20px;
  --button-width: 20px;
}

/* 修正后 */
:root {
  --button-height: 44px;   /* 推荐：老年用户友好尺寸 */
  --button-width: auto;    /* 宽度由内容决定，最小44px */
  --button-min-size: 44px; /* 最小触控区域 */
  --button-padding: 12px 24px;
  --button-font-size: 16px; /* 放大字号 */
}
```

**提交按钮重构**：

```html
<!-- 修正后的提交按钮 -->
<button type="submit" 
        class="btn-submit"
        aria-label="确认提交预约信息">
  <svg aria-hidden="true" class="icon-check" width="24" height="24">
    <use href="#icon-check-circle"></use>
  </svg>
  确认提交
</button>
```

```css
.btn-submit {
  min-width: 44px;    /* 确保至少 24 CSS pixels，推荐 44px */
  min-height: 44px;
  padding: 12px 24px;
  font-size: 16px;
  border-radius: 8px;
  background-color: var(--color-primary);
  color: #FFFFFF;
  cursor: pointer;
  /* 确保触控区域与视觉区域一致 */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
```

**关键注意**：此处 24×24 指的是 **CSS pixels**（逻辑像素），非物理像素。在 Retina 屏幕（2x DPR）上，24 CSS pixels 对应 48 物理像素。建议老年用户表单统一使用 44×44 CSS pixels 作为最小触控目标。

---

### 2.6 步骤4：焦点外观 — 焦点不遮挡 & 焦点外观

**适用准则A**：WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum) — **AA级**

> 原文要求："When a user interface component receives keyboard focus, the component is not entirely hidden due to author-created content."

**适用准则B**：WCAG 2.2 SC 2.4.13 Focus Appearance — **AAA级**

> 原文要求："When the keyboard focus indicator is visible, an area of the focus indicator meets all the following: is at least as large as the area of a 2 CSS pixel thick perimeter of the unfocused component, and has a contrast ratio of at least 3:1 between the same pixels in the focused and unfocused states."

#### 当前缺陷

**焦点遮挡风险（2.4.11）**：
- 当前设计中若存在固定定位（`position: fixed/sticky`）的页眉、悬浮帮助按钮或弹窗，可能在键盘导航时完全遮挡焦点元素。
- 老年用户在使用键盘或开关设备时，焦点被遮挡将导致无法判断当前所在位置。

**焦点外观不足（2.4.13）**：
- 当前焦点样式为"1px dashed #999999"，存在两个问题：
  1. **厚度不足**：1px 低于 2 CSS pixel 的最低周长/厚度要求。
  2. **对比度不足**：`#999999` 在 `#F0F0F0` 背景上的对比度约为 **2.50:1**，低于 3:1 的最低要求。

  对比度计算依据：
  - #999999 相对亮度 L₁ ≈ 0.3185
  - #F0F0F0 相对亮度 L₂ ≈ 0.8714
  - 对比度 = (0.8714 + 0.05) / (0.3185 + 0.05) ≈ 2.50:1 < 3:1 ✗

#### 改造方案

**焦点不遮挡（2.4.11）**：

```css
/* 规则：避免在焦点元素上方放置固定内容 */

/* 错误做法：固定页眉遮挡焦点 */
.header-fixed {
  position: fixed;
  top: 0;
  z-index: 100;
}

/* 正确做法：为固定内容留出滚动空间 */
.main-content {
  scroll-padding-top: 80px; /* 确保焦点元素滚动后不被页眉遮挡 */
}

/* 如果使用固定定位的帮助按钮，确保它不覆盖表单区域 */
.help-fab {
  position: fixed;
  bottom: 20px;
  right: 20px;
  /* 不设置 z-index 覆盖表单内容 */
}
```

- 所有 `position: fixed` 或 `position: sticky` 的元素必须通过 `scroll-padding` 或 `scroll-margin` 确保焦点元素可见。
- 弹窗/对话框关闭后，焦点必须返回到触发元素，且不被新出现的固定内容遮挡。

**焦点外观修正（2.4.13）**：

```css
/* 修正前 */
:root {
  --color-focus-outline: #999999;  /* 对比度 2.50:1 ✗ */
}
*:focus {
  outline: 1px dashed var(--color-focus-outline); /* 1px ✗, 虚线 ✗ */
}

/* 修正后 */
:root {
  --color-focus-outline: #1A1A1A;  /* 在 #F0F0F0 上对比度 ≈ 14.7:1 ✓ */
}
*:focus-visible {
  outline: 3px solid var(--color-focus-outline);  /* 3px ≥ 2px ✓, 实线 ✓ */
  outline-offset: 2px;  /* 与元素保持间距，更清晰 */
}

/* 在深色背景上（如按钮），使用白色焦点 */
.btn-primary:focus-visible {
  outline: 3px solid #FFFFFF;
  outline-offset: 2px;
}
```

**设计Token修正**：

```css
:root {
  /* 颜色修正 */
  --color-focus-outline: #1A1A1A;   /* 原 #999999 对比度不足 */
  
  /* 排版修正 */
  --font-size-base: 16px;           /* 原 14px，放大以适应老年人 */
  --line-height-base: 1.5;          /* 原 1.2，增大行距提升可读性 */
}
```

---

### 2.7 全局：进度指示器

#### 当前缺陷

当前表单无进度指示器（`progress_indicator: "无"`），老年用户在多步骤流程中容易迷失方向，不知道已完成多少、还剩多少。

#### 改造方案

```html
<nav aria-label="表单进度">
  <ol class="progress-steps">
    <li aria-current="step" class="step-active">
      <span class="step-number">1</span>
      <span class="step-label">身份验证</span>
    </li>
    <li class="step-pending">
      <span class="step-number">2</span>
      <span class="step-label">基本信息</span>
    </li>
    <li class="step-pending">
      <span class="step-number">3</span>
      <span class="step-label">服务选择</span>
    </li>
    <li class="step-pending">
      <span class="step-number">4</span>
      <span class="step-label">提交确认</span>
    </li>
  </ol>
</nav>
```

```css
.progress-steps {
  display: flex;
  list-style: none;
  padding: 0;
  gap: 8px;
}
.step-active .step-number {
  background-color: var(--color-primary);
  color: #FFFFFF;
  min-width: 32px;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: bold;
}
.step-pending .step-number {
  background-color: var(--color-border);
  color: var(--color-text-primary);
}
```

- 当前步骤使用 `aria-current="step"` 标记。
- 视觉上使用数字+文字双重指示，不仅依赖颜色区分。
- 屏幕阅读器可朗读"表单进度，共4步，当前第1步：身份验证"。

---

### 2.8 全局：表单结构与语义

基于 WAI Forms Tutorial 最佳实践，对表单基础结构进行以下改造：

#### 2.8.1 标签关联

所有表单控件必须使用 `<label>` 元素显式关联：

```html
<!-- 错误：仅用 placeholder 作为标签 -->
<input type="text" placeholder="请输入姓名">

<!-- 正确：使用 label 元素 -->
<label for="full-name">姓名</label>
<input type="text" id="full-name" name="full_name" 
       required autocomplete="name"
       aria-describedby="name-hint">
<p id="name-hint">请填写身份证上的姓名</p>
```

#### 2.8.2 分组与语义

相关控件使用 `<fieldset>` 和 `<legend>` 分组：

```html
<fieldset>
  <legend>个人基本信息</legend>
  
  <div class="form-group">
    <label for="full-name">姓名 <span aria-hidden="true">*</span> <span class="sr-only">（必填）</span></label>
    <input type="text" id="full-name" name="full_name" required autocomplete="name">
  </div>
  
  <div class="form-group">
    <label for="id-card">身份证号 <span aria-hidden="true">*</span> <span class="sr-only">（必填）</span></label>
    <input type="text" id="id-card" name="id_card" required 
           pattern="\d{17}[\dXx]" maxlength="18"
           autocomplete="off"
           aria-describedby="id-hint">
    <p id="id-hint">请输入18位身份证号码，最后一位可能是X</p>
  </div>
  
  <div class="form-group">
    <label for="phone">手机号 <span aria-hidden="true">*</span> <span class="sr-only">（必填）</span></label>
    <input type="tel" id="phone" name="phone" required 
           pattern="1[3-9]\d{9}" maxlength="11"
           autocomplete="tel"
           aria-describedby="phone-hint">
    <p id="phone-hint">请输入11位手机号码，用于接收服务通知</p>
  </div>
</fieldset>
```

#### 2.8.3 输入说明（前置提示）

在每个输入框附近提供格式说明，而非仅在报错后才告知：

```html
<label for="id-card">身份证号</label>
<p id="id-hint" class="field-hint">格式：18位数字，最后一位可能为X。示例：310101199001011234</p>
<input type="text" id="id-card" aria-describedby="id-hint id-error">
```

#### 2.8.4 即时校验与错误提示

- **失焦校验（onBlur）**：用户离开字段时即时验证格式，而非等到最终提交。
- **错误提示不依赖单一颜色**：使用图标+文字+颜色三重指示。

```html
<div class="form-group has-error">
  <label for="id-card">身份证号</label>
  <input type="text" id="id-card" aria-invalid="true" aria-describedby="id-hint id-error">
  <p id="id-error" class="error-message" role="alert">
    <span aria-hidden="true">⚠️</span>
    身份证号格式不正确。请输入18位数字，最后一位可能为X。
  </p>
</div>
```

```css
.has-error input {
  border: 2px solid var(--color-error);
  /* 不仅依赖颜色，还使用边框宽度变化 */
}
.has-error .error-message {
  color: var(--color-error);
  font-weight: 600;
  /* 配合图标使用，不单独依赖颜色传达错误 */
}
```

#### 2.8.5 撤销与确认机制

```html
<!-- 提交前的确认对话框 -->
<dialog id="confirm-dialog" aria-labelledby="confirm-title">
  <h2 id="confirm-title">确认提交</h2>
  <p>您即将提交以下预约信息：</p>
  <dl>
    <dt>姓名</dt><dd>张三</dd>
    <dt>服务项目</dt><dd>助餐服务（优先级1）、助医服务（优先级2）</dd>
  </dl>
  <div class="dialog-actions">
    <button type="button" id="confirm-yes" class="btn-primary">确认提交</button>
    <button type="button" id="confirm-no" class="btn-secondary">返回修改</button>
  </div>
</dialog>
```

- 提交前弹出确认对话框，用户可选择"返回修改"（撤销）。
- 提交成功后显示明确的成功提示，并提供"返回首页"和"再预约一项"选项。

---

## 3. 设计Token修正汇总

| Token | 原值 | 修正值 | 依据 |
|-------|------|--------|------|
| `--color-focus-outline` | `#999999` | `#1A1A1A` | 2.4.13：对比度从 2.50:1 提升至 ≈14.7:1（≥3:1） |
| `--font-size-base` | `14px` | `16px` | 老年用户可读性 |
| `--line-height-base` | `1.2` | `1.5` | 提升文本可读性 |
| `--button-height` | `20px` | `44px` | 2.5.8：目标尺寸至少 24×24 CSS pixels，推荐 44px |
| `--button-width` | `20px` | `auto (min 44px)` | 2.5.8 |
| `--button-font-size` | `12px` | `16px` | 老年用户可读性 |
| `--input-height` | `32px` | `44px` | 触控友好 |
| `--input-padding` | `4px 8px` | `10px 12px` | 增大触控/可视区域 |

**焦点样式完整修正**：

```css
/* 焦点 outline 需同时满足 2.4.13 的两个条件 */
*:focus-visible {
  outline: 3px solid #1A1A1A;   /* ≥ 2px 厚度 ✓ */
  outline-offset: 2px;           /* 与元素分离，更清晰 */
}
/* 注：2.4.13 为 AAA 级准则，建议作为增强目标 */
```

---

## 4. 改造优先级

| 优先级 | 改造项 | 准则 | 级别 |
|--------|--------|------|------|
| P0 阻塞 | 替代认证方式（消除复杂密码依赖） | 3.3.8 | AA |
| P0 阻塞 | 消除拖拽排序 | 2.5.7 | AA |
| P0 阻塞 | 消除冗余输入 | 3.3.7 | A |
| P0 阻塞 | 提交按钮尺寸放大至≥24×24 CSS pixels | 2.5.8 | AA |
| P1 高 | 焦点外观修正（对比度+厚度） | 2.4.13 | AAA |
| P1 高 | 添加进度指示器 | 表单最佳实践 | — |
| P1 高 | 一致的帮助入口 | 3.2.6 | A |
| P1 高 | 超时延长+预警机制 | 表单最佳实践 | — |
| P2 中 | 焦点不遮挡（避免 fixed 遮挡） | 2.4.11 | AA |
| P2 中 | label 关联、fieldset 分组 | 表单最佳实践 | — |
| P2 中 | 即时校验+非颜色错误提示 | 表单最佳实践 | — |
| P2 中 | 基础字号/行高调整 | 老年友好 | — |

---

## 5. 注意事项

1. **本文档不声称全站合规**：所有改造建议仅适用于本表单。其他页面需独立评估。
2. **WCAG 2.2级别严格区分**：
   - A级：3.3.7（冗余输入）、3.2.6（一致帮助）
   - AA级：2.4.11（焦点不遮挡）、2.5.7（拖拽）、2.5.8（目标尺寸）、3.3.8（可无障碍认证）
   - AAA级：2.4.13（焦点外观）
3. **CSS像素 ≠ 物理像素**：所有尺寸要求（如24×24）均以 CSS pixels 为单位，在不同DPR设备上物理像素数不同。
4. **多元兜底方案**：针对无智能手机、无法接收短信的老年人，必须保留线下协助通道。
5. **认证方式不得降级**：若选择短信验证码，验证码应为6位数字（非8位复杂组合），且有效期合理（≥5分钟）。

---

*文档结束。如有疑问，请联系无障碍合规负责人。*
