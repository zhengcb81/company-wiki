#!/usr/bin/env python3
"""
tag_segments.py — Layer 3: Markdown → 标签化分段

读取 companies/{name}/extracts/ 下的 Markdown 文件，
调用 LLM 将内容切分为语义段落并打多维标签，
保存到 companies/{name}/segments/ 下（JSONL 格式）。

标签维度：
  - category: 财务/业务/战略/风险/市场/治理/技术/其他
  - sentiment: 正面/负面/中性
  - importance: 高/中/低
  - topics: 主题关键词列表
  - entities: 提及的实体列表

用法：
    python3 scripts/tag_segments.py                    # 处理所有公司
    python3 scripts/tag_segments.py --company 北方华创  # 只处理指定公司
    python3 scripts/tag_segments.py --check             # 列出待处理文件
    python3 scripts/tag_segments.py --dry-run           # 预览
"""

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# 公共基础设施（路径、环境、配置、LLM）
from common import WIKI_ROOT

from llm_client import get_llm_client
from graph import Graph


def get_segments_db_path() -> Path:
    return WIKI_ROOT / ".segments_db.json"


def load_segments_db() -> dict:
    db_path = get_segments_db_path()
    if db_path.exists():
        try:
            return json.loads(db_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_segments_db(db: dict):
    get_segments_db_path().write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def file_hash(file_path: Path) -> str:
    stat = file_path.stat()
    return hashlib.md5(
        f"{file_path.name}:{stat.st_size}:{stat.st_mtime}".encode()
    ).hexdigest()


def split_into_chunks(text: str, max_chars: int = 6000) -> List[str]:
    """将长文本按自然段落分块"""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para

    if current:
        chunks.append(current.strip())

    return chunks


def extract_frontmatter(text: str) -> tuple:
    """提取 YAML frontmatter"""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            try:
                import yaml

                fm = yaml.safe_load(text[3:end])
                return fm, text[end + 3 :].strip()
            except Exception:
                pass
    return {}, text


SEGMENT_PROMPT = """请将以下文档切分为语义段落，对每个段落提取结构化信息。

要求：
1. 每个段落对应文档中的一个独立事实、数据或观点
2. text 保留原文核心信息（不超过300字），不添加额外分析
3. category 从 [财务, 业务, 战略, 风险, 市场, 治理, 技术, 其他] 中选择最贴切的一个
4. sentiment 从 [正面, 负面, 中性] 中选择
5. importance 基于对投资者决策的影响程度：[高, 中, 低]
6. topics 列出该段落涉及的 1-3 个主题关键词
7. entities 列出该段落提及的公司、产品、技术、人物等实体（最多5个）

输出严格的 JSON 数组格式，不要有任何额外说明：

[
  {
    "text": "段落核心内容",
    "category": "财务",
    "sentiment": "正面",
    "importance": "高",
    "topics": ["营收增长", "毛利率"],
    "entities": ["中微公司", "刻蚀设备"]
  }
]

文档内容：
"""


def _extract_json_objects(text: str) -> List[Dict]:
    """从可能截断的文本中提取完整的 JSON 对象"""
    objects = []
    # 匹配完整的 {...} 对象
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    obj = json.loads(text[start : i + 1])
                    if isinstance(obj, dict) and "text" in obj:
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    return objects


def tag_segments(text: str, llm_client, doc_type: str = "") -> List[Dict]:
    """调用 LLM 对文本分段打标签"""
    # 限制 chunk 大小，确保 LLM 有足够输出空间
    chunks = split_into_chunks(text, max_chars=3000)
    all_segments = []

    for i, chunk in enumerate(chunks):
        prompt = SEGMENT_PROMPT + chunk
        system = "你是一名专业的金融文档分析助手。请严格按要求的 JSON 数组格式输出。"

        response = llm_client.chat(
            user=prompt,
            system=system,
            json_mode=True,
            max_tokens=4000,
            temperature=0.1,
        )

        if not response.success:
            print(
                f"    -> LLM 失败: {response.error[:80] if response.error else 'unknown'}"
            )
            continue

        # 提取并清洗 LLM 输出
        raw_content = response.content or ""
        content = raw_content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            segments = json.loads(content)
            if not isinstance(segments, list):
                print("    -> 解析失败: 不是数组")
                continue

            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                # 验证必要字段
                if "text" not in seg:
                    continue
                # 填充默认值
                seg.setdefault("category", "其他")
                seg.setdefault("sentiment", "中性")
                seg.setdefault("importance", "中")
                seg.setdefault("topics", [])
                seg.setdefault("entities", [])
                seg["chunk_index"] = i
                all_segments.append(seg)

        except json.JSONDecodeError:
            # 尝试提取部分 JSON 对象
            objects = _extract_json_objects(content)
            if objects:
                print(f"    -> JSON 截断，提取 {len(objects)} 个对象")
                for seg in objects:
                    seg.setdefault("category", "其他")
                    seg.setdefault("sentiment", "中性")
                    seg.setdefault("importance", "中")
                    seg.setdefault("topics", [])
                    seg.setdefault("entities", [])
                    seg["chunk_index"] = i
                    all_segments.append(seg)
            else:
                print("    -> JSON 解析失败，无法提取对象")
            continue
        except Exception as e:
            print(f"    -> 处理失败: {e}")
            continue

    return all_segments


def process_extract(
    company_name: str, extract_path: Path, llm_client, dry_run=False
) -> dict:
    """处理单个 extract 文件，生成 segments"""
    try:
        text = extract_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"status": "error", "error": f"读取失败: {e}"}

    frontmatter, body = extract_frontmatter(text)
    if not body or len(body) < 100:
        return {"status": "skip", "error": "内容过短"}

    doc_type = frontmatter.get("doc_type", "unknown")

    # 提取原始日期（从 frontmatter 或文件名）
    original_date = frontmatter.get("published_date", "")
    if not original_date:
        # 尝试从文件名提取日期（如 20220416 → 2022-04-16）
        import re

        date_match = re.search(
            r"(20\d{2})[-_]?([01]\d)[-_]?([0123]\d)", extract_path.name
        )
        if date_match:
            y, m, d = date_match.groups()
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                original_date = f"{y}-{m}-{d}"

    # 确定输出路径
    extract_path_abs = extract_path.resolve()
    extracts_base = (WIKI_ROOT / "companies" / company_name / "extracts").resolve()
    relative = extract_path_abs.relative_to(extracts_base)
    segment_path = WIKI_ROOT / "companies" / company_name / "segments" / relative
    segment_path = segment_path.with_suffix(".jsonl")

    if dry_run:
        # 估算段数（简单按段落数估算）
        est_segments = max(1, len(body.split("\n\n")) // 3)
        return {
            "status": "dry_run",
            "segment_path": str(segment_path),
            "est_segments": est_segments,
        }

    segments = tag_segments(body, llm_client, doc_type)

    if not segments:
        return {"status": "skip", "error": "无有效段落"}

    # 添加元数据
    for seg in segments:
        seg["_meta"] = {
            "source": str(relative.as_posix()),
            "company": company_name,
            "doc_type": doc_type,
            "original_date": original_date,
            "segmented_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "id": str(uuid.uuid4())[:8],
        }

    # 写入 JSONL
    segment_path.parent.mkdir(parents=True, exist_ok=True)
    with open(segment_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(json.dumps(seg, ensure_ascii=False) + "\n")

    return {
        "status": "success",
        "segment_path": str(segment_path),
        "segments": len(segments),
    }


def scan_extract_files(company_filter=None):
    """扫描所有待处理的 extract 文件，按文件大小排序（小文件优先）"""
    graph = Graph()
    companies = graph.get_all_companies()
    if company_filter:
        companies = [c for c in companies if c["name"] == company_filter]

    extract_files = []
    for company in companies:
        name = company["name"]
        extracts_dir = WIKI_ROOT / "companies" / name / "extracts"
        if not extracts_dir.exists():
            continue
        for md_path in extracts_dir.rglob("*.md"):
            extract_files.append((name, md_path, md_path.stat().st_size))

    # 按文件大小排序（小文件优先），避免大文件阻塞流程
    extract_files.sort(key=lambda x: x[2])
    return [(name, path) for name, path, _ in extract_files]


def main():
    parser = argparse.ArgumentParser(description="Markdown → 标签化分段")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, help="最多处理 N 个文件")
    args = parser.parse_args()

    extract_files = scan_extract_files(args.company)
    db = load_segments_db()

    pending = []
    for company_name, extract_path in extract_files:
        fh = file_hash(extract_path)
        key = f"{company_name}/{extract_path.name}"
        if db.get(key) != fh:
            pending.append((company_name, extract_path, fh))

    print(f"找到 {len(extract_files)} 个 extract，待处理 {len(pending)} 个")

    if args.check:
        for company_name, extract_path, _ in pending:
            print(f"  [{company_name}] {extract_path.name}")
        return 0 if not pending else 1

    if not pending:
        print("没有待处理的 extract")
        return 0

    if args.limit:
        pending = pending[: args.limit]
        print(f"限制处理前 {args.limit} 个")

    llm_client = get_llm_client()

    success = 0
    skipped = 0
    errors = 0
    total_segments = 0

    for i, (company_name, extract_path, fh) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {company_name}/{extract_path.name}")
        result = process_extract(
            company_name, extract_path, llm_client, dry_run=args.dry_run
        )

        status = result["status"]
        if status == "success":
            success += 1
            segs = result["segments"]
            total_segments += segs
            print(f"  -> OK | {segs} segments -> {result['segment_path']}")
            if not args.dry_run:
                key = f"{company_name}/{extract_path.name}"
                db[key] = fh
        elif status == "dry_run":
            print(
                f"  -> DRY-RUN | ~{result['est_segments']} segments -> {result['segment_path']}"
            )
        elif status == "skip":
            skipped += 1
            print(f"  -> SKIP | {result.get('error', '')}")
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    if not args.dry_run:
        save_segments_db(db)

    print(
        f"\n完成: {success} 成功, {skipped} 跳过, {errors} 错误, {total_segments} 总段数"
    )
    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
