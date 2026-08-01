# Announcement Collector v1

`company-wiki-collect-announcement` is the narrow canonical intake for one company announcement supplied by an explicit official URL. It is separate from the read-only source-export CLI and never invokes a legacy Wiki writer.

## Contract

- Only `HTTPS` URLs on `sse.com.cn`, `szse.cn`, or their subdomains are accepted. Every redirect is checked before the next request.
- The response must be bounded, non-empty `application/pdf` content with PDF magic and a trailing EOF marker.
- Collection is single-threaded. It does not use a daemon, worker pool, LLM, browser automation, or research pipeline.
- Raw bytes use a content-addressed SHA-256 filename and a create-once hard-link operation. The collector has no overwrite primitive.
- Repeating the same URL/content is idempotent. Existing raw, manifest, or provenance bytes that disagree cause a fail-closed conflict.
- A crash after raw or manifest creation is recoverable by repeating the same command; an existing raw file is verified and never rewritten.

## Paths

For company `{company}`, content hash `{content_sha256}`, and provenance key `SHA-256(content_sha256 + NUL + canonical_url)`:

```text
companies/{company}/raw/announcements/{content_sha256}.pdf
source_manifests/companies/{company}/{content_sha256}.json
source_provenance/companies/{company}/announcements/{provenance_key}.json
```

The manifest is a Source Manifest v1 record with source type `company_announcement`, collector/version, immutable raw path, byte size, SHA-256, entity IDs, published date, and retrieval timestamp. The provenance receipt binds the requested URL, final official URL, title, selected HTTP metadata, manifest, and canonical paths to a content-derived collection ID.

## CLI

```powershell
company-wiki-collect-announcement `
  --root . `
  --company 中微公司 `
  --entity-id SSE:688012 `
  --url https://star.sse.com.cn/.../announcement.pdf `
  --title 关于召开2025年度业绩说明会的公告 `
  --published-date 2026-03-25
```

Success emits one canonical provenance JSON line to stdout. Failure emits no partial stdout. Raw, `source_manifests`, and `source_provenance` remain inside company-wiki; the collector does not write StockWiki, ratings, valuations, research conclusions, or accepted investment state.
