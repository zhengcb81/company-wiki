# W05 interfaces and TDD

## DOCX
- Dispatcher MIME application/vnd.openxmlformats-officedocument.wordprocessingml.document => format docx, parser cwp_document_normalization version 1.0.0, locator cwp-docx-body/1|p=<body paragraph ordinal> or |t=<table>|r=<row>|c=<cell>|p=<cell paragraph>.
- Pure ZIP preflight rejects duplicate/traversal/encrypted members, >10000 members, declared/actual expansion over configured total, source cap; reads the body XML and bounded relationship parts, with no disk extraction. XML no DTD/entities/external fetch and fixed depth/elements limits; deadline checkpoints throughout.
- Main document/body required; document body child order is retained. Paragraph ordinal counts source paragraphs including blanks/deletions, table cell paragraph index scoped to its cell. Duplicate headings yield distinct ordinal locators; no text dedup in parser.
- Current visible text excludes w:del, moveFrom, vanished text; w:ins/moveTo retained with explicit tracked_changes_present diagnostic; structure not silently complete. Embedded objects/images/header/footer and unsupported table wrappers remain named coverage gaps. Regular external hyperlink visible label retained, external targets not fetched, bounded relationship count diagnostic (no full URL in metadata).
- Table units expose stable row/column/header metadata, including financial classification so known financial tables may be excluded while actual business cells remain selectable.
- Obvious Q:/A: and 问:/答:/答复: paragraphs and inline paired labels keep original literal label/text, source_role analyst/management and qa_group_id. Inline fragments preserve exact character intervals within the original paragraph; plain generic paragraphs remain company_filing. No issuer-specific names.
- All text replay via exact original SHA + version + locator; no durable full MD/cache/extra queue.

## Official transcript
- New transcript parser version 0.2.0 binds only transcript generation; PDF parser remains 0.1.1. Old transcript 0.1.1 layout remains replayable.
- Existing explicit complete headings remain valid with actual speaker body. Natural Transcript / issuer Earnings Conference Call heading needs subsequent recognized speakers and substantive call text; nearby title/navigation alone rejected.
- Speaker colon layout and speaker -- role label layout, prepared remarks and Q&A transition supported. Plain named speaker following QA is analyst unless previously management; first prepared speakers management by observed section/role.
- Exact END/end-of-call/disconnect controls stop footer; source lines unchanged so existing TranscriptMaterial and byte bindings replay. No translation, no external execution.

## Major acceptance only
Focused RED before implementation, grouped parser/official-import/selection/replay responsibility GREEN, actual 273436B/SHA bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656 whole original read-only replay; MAIN independent M2 then M3 original-company research. Second issuer synthetic layouts prove mechanism but real company generalization remains MAIN M4.
