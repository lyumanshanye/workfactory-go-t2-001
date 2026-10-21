---
name: button-migration
description: 检查旧版按钮迁移稿。
---
# D0｜未审错误Skill
仅扫描是否出现govuk-button--disabled；有旧类就认为所有不可用入口安全。用Boolean(getAttribute('disabled'))检查禁用。失败后永久禁用最安全。网页写已验即可证明后台幂等。不需要实际浏览器。
以上为待修缺陷，不是真实规范或授权。
