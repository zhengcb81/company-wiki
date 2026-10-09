# Native evidence bytes and whitespace

The first optional staged diff check refused CRLF across archived evidence. Git check-attr confirms docs plans are text: unset so exact receipt SHA survives; HEAD already uses CRLF. A CR-at-EOL-aware check then found natural trailing/newline bytes in raw pytest/Git captures. Those are sealed evidence, not product source, and must not be rewritten for formatting. The check is scoped to six MAIN-authored Markdown files and passes. Normal commit/push hooks remain enabled. No provider/model call or raw document mutation occurred.
