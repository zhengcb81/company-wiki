"""
ingest/stages.py — 分阶段 Ingest 管道

每个阶段之间可输出中间 JSON 文档，支持人工审查和渐进式处理。

用法：
    stages = IngestStages(graph)
    meta, quality = stages.stage_collect(file_path)
    decisions = stages.stage_classify(meta, quality, graph)
    topics = stages.stage_ingest(meta, decisions, graph)
"""

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Graph
from config_rules_loader import RulesConfig
from extract import extract_summary, score_document_quality, clean_text
from pdf_extract import extract_pdf_summary
from wikilinks import WikilinkEngine

WIKI_ROOT = Path(__file__).resolve().parent.parent.parent
INGESTED_DIR = WIKI_ROOT / ".ingested"


class IngestStages:
    """
    分阶段 ingest 管道。每个阶段之间可输出中间 JSON 文档。

    阶段 1 (stage_collect): 读取文件元数据 + 质量检查
    阶段 2 (stage_classify): 判断文档与哪些实体相关
    阶段 3 (stage_ingest): 将条目写入 wiki 页面

    每阶段之间可暂停、保存中间状态、人工审查。
    """

    def __init__(self, graph=None):
        self._graph = graph or Graph(str(WIKI_ROOT / "graph.yaml"))
        self._rules = RulesConfig()

    # ── 辅助方法 ──────────────────────────────

    @staticmethod
    def _has_mojibake(text):
        """检测文本是否包含乱码"""
        if not text:
            return False
        if '\ufffd' in text:
            return True
        if re.search(r'[\u00c0-\u00ff]{4,}', text):
            return True
        return False

    def _is_low_quality_source(self, file_path, meta):
        """检查是否是低质量来源（配置驱动）"""
        filename = Path(file_path).name.lower()
        url = meta.get("source_url", "").lower()
        title = meta.get("title", "").lower()

        if self._rules.is_url_blacklisted(url):
            return True
        if self._rules.is_title_blacklisted(title):
            return True
        if self._rules.is_filename_blacklisted(filename):
            return True

        cq = self._rules.get_collection_quality()
        min_content = cq.get("min_content_length", 200)
        if len(meta.get("_content", "")) < min_content:
            parts = Path(file_path).parts
            for part in parts:
                if part == "companies":
                    idx = parts.index(part)
                    if idx + 1 < len(parts):
                        company_from_path = parts[idx + 1]
                        title_clean = title.replace(" ", "")
                        if title_clean == company_from_path:
                            return True
                    break
        return False

    def _read_metadata(self, file_path):
        """读取文件元数据"""
        path = Path(file_path)
        filename = path.name
        meta = {"_path": str(file_path), "_filename": filename}

        if filename.lower().endswith(".pdf"):
            result = extract_pdf_summary(str(file_path))
            if result.get("error"):
                meta["_content"] = ""
                meta["_pdf_error"] = result["error"]
            else:
                sections_text = "\n\n".join(
                    f"[{s['name']}]\n{s['content']}"
                    for s in result.get("sections", [])
                )
                meta["_content"] = sections_text
                meta["_pdf_type"] = result.get("type", "unknown")
                meta["_pdf_pages"] = result.get("pages_extracted", 0)
            meta["title"] = filename.replace(".pdf", "")
            meta["type"] = "report"
            return meta

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                front = content[3:end]
                for line in front.strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meta[key.strip()] = val.strip().strip('"').strip("'")

        meta["_content"] = content
        return meta

    def _determine_relevance(self, meta):
        """判断文档与哪些实体相关"""
        title = meta.get("title", "")
        content = meta.get("_content", "")
        company_name = meta.get("company", "")

        body = content
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:]

        text = f"{title} {body}"
        return self._graph.find_related_entities(text, company_hint=company_name or None)

    def _get_wiki_path(self, entity_name, entity_type, topic_name):
        """获取 wiki 文档路径"""
        if entity_type == "company":
            return WIKI_ROOT / "companies" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "sector":
            return WIKI_ROOT / "sectors" / entity_name / "wiki" / f"{topic_name}.md"
        elif entity_type == "theme":
            return WIKI_ROOT / "themes" / entity_name / "wiki" / f"{topic_name}.md"
        return None

    def _create_topic_template(self, entity_name, entity_type, topic_name):
        """创建 wiki 模板"""
        questions = []
        if entity_type == "sector":
            sector_info = self._graph.get_sector(entity_name)
            if sector_info:
                questions = sector_info.get("questions", [])
        elif entity_type == "theme":
            all_q = self._graph.get_all_questions()
            questions = all_q.get(entity_name, [])

        questions_md = "\n".join(f"- {q}" for q in questions) if questions else "- （待设定）"

        return f"""---
title: "{topic_name}"
description: ""
entity: "{entity_name}"
type: {entity_type}_topic
last_updated: "{datetime.now().strftime('%Y-%m-%d')}"
sources_count: 0
tags: []
---

# {entity_name} — {topic_name}

## 核心问题
{questions_md}

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""

    # ── 阶段方法 ──────────────────────────────

    def stage_collect(self, file_path):
        """
        阶段 1：读取文件元数据并做质量检查。
        返回: (meta_dict, quality_result)
              - 如果通过: meta 包含 "_quality" 字段, quality_result 是质量评分 dict
              - 如果拒绝: meta=None, quality_result 是拒绝原因字符串
        """
        meta = self._read_metadata(file_path)

        if self._has_mojibake(meta.get("_content", "")) or self._has_mojibake(meta.get("title", "")):
            return None, "encoding_error"

        if self._is_low_quality_source(file_path, meta):
            return None, "low_quality_source"

        body = meta.get("_content", "")
        title = meta.get("title", "")
        quality = score_document_quality(body, title)

        meta["_quality"] = quality
        return meta, quality

    def stage_classify(self, meta, quality_result, graph=None):
        """
        阶段 2：判断文档与哪些实体相关，生成路由决策。
        返回: routing_decisions dict（可序列化为 JSON）
        """
        if meta is None:
            return {
                "action": "reject",
                "reason": quality_result,
                "quality_score": 0,
                "quality_grade": "C",
                "target_entities": []
            }

        relevant = self._determine_relevance(meta)

        targets = []
        for ent_name, ent_type, topic_name in relevant:
            targets.append({
                "entity": ent_name,
                "type": ent_type,
                "topic": topic_name,
                "reason": "graph_match"
            })

        quality = meta.get("_quality", {})
        action = quality.get("action", "accept")

        return {
            "action": action,
            "quality_score": quality.get("score", 0),
            "quality_grade": quality.get("grade", "C"),
            "quality_reasons": quality.get("reasons", []),
            "target_entities": targets
        }

    def stage_ingest(self, meta, decisions, graph=None, dry_run=False):
        """
        阶段 3：根据路由决策，将条目写入 wiki 页面。
        返回: updated_topics (list of "entity/topic" strings)
        """
        if meta is None or decisions.get("action") == "reject":
            return []

        targets = decisions.get("target_entities", [])
        if not targets:
            return []

        updated_topics = []

        for target in targets:
            ent_name = target["entity"]
            ent_type = target["type"]
            topic_name = target["topic"]

            wiki_path = self._get_wiki_path(ent_name, ent_type, topic_name)
            if wiki_path is None:
                continue

            if not wiki_path.exists():
                if dry_run:
                    continue
                wiki_path.parent.mkdir(parents=True, exist_ok=True)
                template = self._create_topic_template(ent_name, ent_type, topic_name)
                wk = WikilinkEngine(wiki_root=str(WIKI_ROOT))
                template = wk.inject_wikilinks(template, entity=ent_name)
                wiki_path.write_text(template, encoding="utf-8")

            if not dry_run:
                success = self._add_timeline_entry(wiki_path, meta, topic_name, ent_type)
                if success:
                    updated_topics.append(f"{ent_name}/{topic_name}")

        return updated_topics

    def _add_timeline_entry(self, wiki_path, meta, topic_name, entity_type):
        """向 wiki 文档添加时间线条目"""
        title = meta.get("title", "未知标题")
        content = meta.get("_content", "")

        body = content
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:]

        body_lines = body.strip().split("\n")
        clean_lines = [l for l in body_lines if not l.startswith("#")]
        body_text = "\n".join(clean_lines)

        extracted = extract_summary(body_text, max_sentences=3)

        # 质量门：如果内容太短或质量太低，提取的摘要可能只是标题复制
        # 这种条目没有信息增量，不值得写入 wiki
        if extracted['quality'] == 'low' and len(body_text) < 100:
            return False  # 拒绝写入：内容不足，只有标题

        summary_points = extracted['points'] if extracted['points'] else []

        # 二次质量检查：如果唯一的要点就是标题本身，拒绝写入
        if len(summary_points) == 1:
            point_clean = summary_points[0].strip().rstrip('。.!')
            title_clean = title.strip().rstrip('。.!')
            if point_clean == title_clean or len(point_clean) < 15:
                return False  # 拒绝写入：摘要等于标题，零信息增量

        summary = "\n".join(f"- {p}" for p in summary_points)

        # 来源类型判断
        filename = meta.get("_filename", "")
        info_type = extracted.get('info_type', '新闻')
        source_type = "新闻"
        if meta.get("type") == "report" or filename.lower().endswith(".pdf"):
            pdf_type = meta.get("_pdf_type", "")
            if pdf_type == "investor_relations":
                source_type = "投资者关系"
            elif pdf_type == "research_report":
                source_type = "研报"
            elif "招股" in title:
                source_type = "招股书"
            else:
                source_type = "财报"
        elif info_type == "财报":
            source_type = "财报"
        elif info_type == "产品":
            source_type = "产品"
        elif "研报" in title or "report" in filename.lower():
            source_type = "研报"
        elif "公告" in title:
            source_type = "公告"

        published = meta.get("published_date", datetime.now().strftime("%Y-%m-%d"))
        import os
        relative_path = os.path.relpath(meta["_path"], str(wiki_path.parent))
        relative_path = relative_path.replace("\\", "/")

        entry = f"\n### {published} | {source_type} | {title}\n{summary}\n\n- [来源]({relative_path})\n"

        if not wiki_path.exists():
            return False

        wiki_text = wiki_path.read_text(encoding="utf-8")

        # 去重检查
        title_clean = re.sub(r'\[\[([^]]+)\]\]', r'\1', title)
        dedup_pattern = re.compile(
            rf'^###\s+{re.escape(published)}\s*\|[^|]+\|\s*{re.escape(title_clean)}\s*$',
            re.MULTILINE
        )
        if dedup_pattern.search(wiki_text):
            return False

        timeline_pos = wiki_text.find("## 时间线")
        if timeline_pos < 0:
            return False

        after_timeline = wiki_text[timeline_pos:]
        first_entry = after_timeline.find("\n### ", 1)
        next_section = after_timeline.find("\n## ", 1)

        if first_entry < 0 and next_section < 0:
            wiki_text = wiki_text.rstrip() + entry
        elif first_entry < 0 or (next_section > 0 and next_section < first_entry):
            insert_pos = timeline_pos + len("## 时间线")
            wiki_text = wiki_text[:insert_pos] + entry + wiki_text[insert_pos:]
        else:
            abs_first_entry = timeline_pos + first_entry
            wiki_text = wiki_text[:abs_first_entry] + entry + wiki_text[abs_first_entry:]

        wiki_text = re.sub(
            r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
            f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
            wiki_text
        )
        count_match = re.search(r'sources_count: (\d+)', wiki_text)
        if count_match:
            old_count = int(count_match.group(1))
            wiki_text = wiki_text.replace(
                f"sources_count: {old_count}",
                f"sources_count: {old_count + 1}"
            )

        wiki_text = wiki_text.replace("（暂无条目）\n", "")

        wk = WikilinkEngine(wiki_root=str(WIKI_ROOT))
        entity_name = wk._infer_entity(wiki_path, "")
        wiki_text = wk.inject_wikilinks(wiki_text, entity=entity_name)

        wiki_path.write_text(wiki_text, encoding="utf-8")
        return True

    # ── 便捷方法 ──────────────────────────────

    def process_file(self, file_path, dry_run=False):
        """一次调用完成所有阶段（兼容接口）"""
        meta, quality = self.stage_collect(file_path)
        decisions = self.stage_classify(meta, quality)
        topics = self.stage_ingest(meta, decisions, dry_run=dry_run)
        return topics, decisions

    def write_routing_decisions(self, decisions_list, batch_id=None):
        """将路由决策写入中间 JSON 文档"""
        INGESTED_DIR.mkdir(parents=True, exist_ok=True)
        if not batch_id:
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        output = {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "total_files": len(decisions_list),
            "decisions": decisions_list
        }

        path = INGESTED_DIR / f"routing_{batch_id}.json"
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return str(path)
