# 星芒社区设计系统 Token 定义

> 版本: v2.1.0  |  最后更新: 2024-03-28  
> 本文档定义了星芒社区全产品线的设计Token，前端代码中通过CSS自定义属性引用。

## 颜色 (Colors)

```css
:root {
  --color-primary: #2563EB;
  --color-primary-hover: #1D4ED8;
  --color-error: #DC2626;
  --color-success: #16A34A;
  --color-text-primary: #1F2937;
  --color-text-secondary: #6B7280;
  --color-text-disabled: #9CA3AF;
  --color-focus-outline: #999999;
  --color-bg-surface: #F0F0F0;
  --color-bg-card: #FFFFFF;
  --color-border: #D1D5DB;
}
```

## 排版 (Typography)

```css
:root {
  --font-family-base: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-size-base: 14px;
  --font-size-small: 12px;
  --font-size-large: 16px;
  --font-size-h1: 20px;
  --font-size-h2: 18px;
  --line-height-base: 1.2;
  --font-weight-normal: 400;
  --font-weight-bold: 600;
}
```

## 间距 (Spacing)

```css
:root {
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 12px;
  --spacing-lg: 16px;
  --spacing-xl: 24px;
  --spacing-xxl: 32px;
}
```

## 组件 (Components)

### 按钮
```css
:root {
  --button-height: 20px;
  --button-width: 20px;
  --button-padding: 0;
  --button-border-radius: 4px;
  --button-font-size: 12px;
}
```

### 表单控件
```css
:root {
  --input-height: 32px;
  --input-padding: 4px 8px;
  --input-border-radius: 4px;
  --input-border-color: var(--color-border);
  --input-focus-border-color: var(--color-primary);
  --input-font-size: var(--font-size-base);
}
```

### 卡片
```css
:root {
  --card-padding: 16px;
  --card-border-radius: 8px;
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
```
