"""
Pipeline 单元测试
测试 Layer 2 (build_extracts) → Layer 3 (tag_segments) → ingest_v2 (segments 模式) 的关键路径
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from build_extracts import file_hash, scan_pdf_files, build_extract
from tag_segments import (
    split_into_chunks,
    extract_frontmatter,
    process_extract,
)
from ingest_v2 import scan_pending_segments, process_segments_file


class TestBuildExtracts:
    """测试 Layer 2: PDF → Markdown"""

    def test_file_hash_consistency(self, tmp_path):
        """相同文件内容产生相同哈希"""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("hello world")
        h1 = file_hash(test_file)
        h2 = file_hash(test_file)
        assert h1 == h2
        assert isinstance(h1, str)
        assert len(h1) == 32  # md5

    def test_file_hash_changes_on_modify(self, tmp_path):
        """文件修改后哈希应变化"""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("hello world")
        h1 = file_hash(test_file)
        test_file.write_text("hello world modified")
        h2 = file_hash(test_file)
        assert h1 != h2

    @patch("build_extracts.extract_pdf_text")
    @patch("build_extracts.classify_pdf")
    @patch("build_extracts.Graph")
    def test_build_extract_success(
        self, mock_graph, mock_classify, mock_extract, tmp_path
    ):
        """成功提取 PDF 到 Markdown"""
        mock_extract.return_value = {
            "text": "这是测试内容。\n\n第二段内容。",
            "pages_read": 5,
            "total_pages": 5,
            "total_chars": 500,
            "error": None,
            "is_scanned": False,
        }
        mock_classify.return_value = "annual_report"

        # 设置 WIKI_ROOT 为临时目录
        with patch("build_extracts.WIKI_ROOT", tmp_path):
            pdf_path = tmp_path / "companies" / "测试公司" / "raw" / "test.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_text("fake pdf")

            result = build_extract("测试公司", pdf_path, dry_run=False)

            assert result["status"] == "success"
            assert result["chars"] == 500
            assert result["pages"] == 5

            # 验证文件已写入
            extract_path = tmp_path / "companies" / "测试公司" / "extracts" / "test.md"
            assert extract_path.exists()
            content = extract_path.read_text(encoding="utf-8")
            assert "---" in content
            assert "这是测试内容" in content

    @patch("build_extracts.extract_pdf_text")
    def test_build_extract_scanned_pdf(self, mock_extract, tmp_path):
        """扫描版 PDF 应跳过"""
        mock_extract.return_value = {
            "text": "",
            "pages_read": 0,
            "total_pages": 10,
            "total_chars": 0,
            "error": None,
            "is_scanned": True,
        }

        with patch("build_extracts.WIKI_ROOT", tmp_path):
            pdf_path = tmp_path / "companies" / "测试公司" / "raw" / "scan.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_text("fake")

            result = build_extract("测试公司", pdf_path)
            assert result["status"] == "skip"
            assert "扫描版" in result["error"]

    @patch("build_extracts.extract_pdf_text")
    def test_build_extract_too_short(self, mock_extract, tmp_path):
        """内容过短应跳过"""
        mock_extract.return_value = {
            "text": "短",
            "pages_read": 1,
            "total_pages": 1,
            "total_chars": 1,
            "error": None,
            "is_scanned": False,
        }

        with patch("build_extracts.WIKI_ROOT", tmp_path):
            pdf_path = tmp_path / "companies" / "测试公司" / "raw" / "short.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_text("fake")

            result = build_extract("测试公司", pdf_path)
            assert result["status"] == "skip"
            assert "过短" in result["error"]

    @patch("build_extracts.extract_pdf_text")
    def test_build_extract_dry_run(self, mock_extract, tmp_path):
        """dry_run 不应写入文件"""
        mock_extract.return_value = {
            "text": "内容",
            "pages_read": 2,
            "total_pages": 2,
            "total_chars": 100,
            "error": None,
            "is_scanned": False,
        }

        with patch("build_extracts.WIKI_ROOT", tmp_path):
            pdf_path = tmp_path / "companies" / "测试公司" / "raw" / "dry.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_text("fake")

            result = build_extract("测试公司", pdf_path, dry_run=True)
            assert result["status"] == "dry_run"

            extract_path = tmp_path / "companies" / "测试公司" / "extracts" / "dry.md"
            assert not extract_path.exists()


class TestTagSegments:
    """测试 Layer 3: Markdown → 标签化分段"""

    def test_split_into_chunks_small_text(self):
        """短文本不分块"""
        text = "这是一段短文本。"
        chunks = split_into_chunks(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_into_chunks_large_text(self):
        """长文本按段落分块"""
        paragraphs = [f"段落{i}: " + "x" * 500 for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = split_into_chunks(text, max_chars=1000)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 1000 + 20  # 允许一些边界容差

    def test_extract_frontmatter_present(self):
        """正确提取 frontmatter"""
        text = '---\ncompany: "测试公司"\npages: 10\n---\n\n正文内容'
        fm, body = extract_frontmatter(text)
        assert fm["company"] == "测试公司"
        assert fm["pages"] == 10
        assert "正文内容" in body

    def test_extract_frontmatter_absent(self):
        """无 frontmatter 时返回空和原文"""
        text = "只有正文内容"
        fm, body = extract_frontmatter(text)
        assert fm == {}
        assert body == text

    @patch("tag_segments.get_llm_client")
    def test_process_extract_success(self, mock_get_llm, tmp_path):
        """成功处理 extract 文件生成 segments"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps(
            [
                {
                    "text": "营收增长30%",
                    "category": "财务",
                    "sentiment": "正面",
                    "importance": "高",
                    "topics": ["营收"],
                    "entities": ["测试公司"],
                },
                {
                    "text": "新产品发布",
                    "category": "业务",
                    "sentiment": "正面",
                    "importance": "中",
                    "topics": ["产品"],
                    "entities": ["测试公司"],
                },
            ],
            ensure_ascii=False,
        )
        mock_response.error = None
        mock_llm.chat.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        with patch("tag_segments.WIKI_ROOT", tmp_path):
            extract_path = (
                tmp_path / "companies" / "测试公司" / "extracts" / "report.md"
            )
            extract_path.parent.mkdir(parents=True)
            extract_path.write_text(
                '---\ncompany: "测试公司"\ndoc_type: "annual_report"\n---\n\n这是一份年度报告。公司营收增长30%，达到历史新高。新产品线拓展顺利，市场份额持续提升。'
                + "x" * 200,
                encoding="utf-8",
            )

            result = process_extract("测试公司", extract_path, mock_llm, dry_run=False)

            assert result["status"] == "success"
            assert result["segments"] == 2

            # 验证 JSONL 文件
            segment_path = (
                tmp_path / "companies" / "测试公司" / "segments" / "report.jsonl"
            )
            assert segment_path.exists()
            lines = segment_path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 2
            seg0 = json.loads(lines[0])
            assert seg0["text"] == "营收增长30%"
            assert "_meta" in seg0
            assert seg0["_meta"]["company"] == "测试公司"

    @patch("tag_segments.get_llm_client")
    def test_process_extract_dry_run(self, mock_get_llm, tmp_path):
        """dry_run 不写入文件"""
        mock_llm = MagicMock()

        with patch("tag_segments.WIKI_ROOT", tmp_path):
            extract_path = tmp_path / "companies" / "测试公司" / "extracts" / "dry.md"
            extract_path.parent.mkdir(parents=True)
            extract_path.write_text(
                '---\ncompany: "测试公司"\n---\n\n这是一段测试内容，长度足够。'
                + "x" * 200,
                encoding="utf-8",
            )

            result = process_extract("测试公司", extract_path, mock_llm, dry_run=True)

            assert result["status"] == "dry_run"
            segment_path = (
                tmp_path / "companies" / "测试公司" / "segments" / "dry.jsonl"
            )
            assert not segment_path.exists()

    def test_process_extract_short_content(self, tmp_path):
        """内容过短应跳过"""
        mock_llm = MagicMock()

        with patch("tag_segments.WIKI_ROOT", tmp_path):
            extract_path = tmp_path / "companies" / "测试公司" / "extracts" / "short.md"
            extract_path.parent.mkdir(parents=True)
            extract_path.write_text("短", encoding="utf-8")

            result = process_extract("测试公司", extract_path, mock_llm)
            assert result["status"] == "skip"
            assert "过短" in result["error"]


class TestIngestSegments:
    """测试 ingest_v2 的 segments 处理"""

    @patch("ingest_v2.Graph")
    def test_scan_pending_segments(self, mock_graph_class, tmp_path):
        """扫描待处理 segments 文件"""
        mock_graph = MagicMock()
        mock_graph.get_all_companies.return_value = [
            {"name": "公司A"},
            {"name": "公司B"},
        ]
        mock_graph_class.return_value = mock_graph

        with patch("ingest_v2.WIKI_ROOT", tmp_path):
            # 创建 segments 文件
            seg_dir_a = tmp_path / "companies" / "公司A" / "segments"
            seg_dir_a.mkdir(parents=True)
            (seg_dir_a / "report.jsonl").write_text("{}")

            pending = scan_pending_segments(mock_graph)

            assert len(pending) == 1
            assert pending[0][1] == "公司A"
            assert pending[0][2] == "company"

    @patch("ingest_v2.Graph")
    def test_scan_pending_segments_filtered(self, mock_graph_class, tmp_path):
        """按公司过滤 segments"""
        mock_graph = MagicMock()
        mock_graph.get_all_companies.return_value = [
            {"name": "公司A"},
            {"name": "公司B"},
        ]
        mock_graph_class.return_value = mock_graph

        with patch("ingest_v2.WIKI_ROOT", tmp_path):
            seg_dir_a = tmp_path / "companies" / "公司A" / "segments"
            seg_dir_a.mkdir(parents=True)
            (seg_dir_a / "report.jsonl").write_text("{}")

            seg_dir_b = tmp_path / "companies" / "公司B" / "segments"
            seg_dir_b.mkdir(parents=True)
            (seg_dir_b / "report.jsonl").write_text("{}")

            pending = scan_pending_segments(mock_graph, company_name="公司A")

            assert len(pending) == 1
            assert pending[0][1] == "公司A"

    @patch("ingest_v2.get_wiki_path")
    @patch("ingest_v2.add_timeline_entries")
    @patch("ingest_v2.create_wiki_template")
    @patch("ingest_v2.Graph")
    def test_process_segments_file(
        self, mock_graph_class, mock_create, mock_add, mock_get_wiki, tmp_path
    ):
        """从 segments JSONL 合成 wiki 条目"""
        mock_graph = MagicMock()
        mock_graph_class.return_value = mock_graph

        wiki_path = tmp_path / "wiki.md"
        mock_get_wiki.return_value = wiki_path
        mock_add.return_value = 1

        seg_file = tmp_path / "segments.jsonl"
        segments = [
            {
                "text": "营收增长50%",
                "category": "财务",
                "importance": "高",
                "_meta": {
                    "source": "report.md",
                    "company": "测试公司",
                    "doc_type": "annual_report",
                },
            },
            {
                "text": "新产品线拓展",
                "category": "业务",
                "importance": "中",
                "_meta": {
                    "source": "report.md",
                    "company": "测试公司",
                    "doc_type": "annual_report",
                },
            },
        ]
        seg_file.write_text(
            "\n".join(json.dumps(s, ensure_ascii=False) for s in segments),
            encoding="utf-8",
        )

        result = process_segments_file(
            str(seg_file), "测试公司", "company", mock_graph, dry_run=False
        )

        assert result["status"] == "success"
        assert result["entries_added"] == 1
        mock_add.assert_called_once()

        # 验证传入的 entry 结构
        call_args = mock_add.call_args
        entry = call_args[0][1][0]
        assert entry["source_type"] == "财报"  # annual_report 映射
        assert "[财务/高] 营收增长50%" in entry["key_points"]
        assert entry["date"] != ""

    def test_process_segments_file_empty(self, tmp_path):
        """空 segments 文件应跳过"""
        seg_file = tmp_path / "empty.jsonl"
        seg_file.write_text("", encoding="utf-8")

        mock_graph = MagicMock()
        result = process_segments_file(str(seg_file), "测试公司", "company", mock_graph)

        assert result["status"] == "skip"
        assert "无 segments" in result["error"]

    def test_process_segments_file_dry_run(self, tmp_path):
        """dry_run 不写入 wiki"""
        seg_file = tmp_path / "segments.jsonl"
        segments = [
            {
                "text": "测试内容",
                "category": "其他",
                "importance": "中",
                "_meta": {"source": "test.md", "doc_type": "news"},
            }
        ]
        seg_file.write_text(
            json.dumps(segments[0], ensure_ascii=False), encoding="utf-8"
        )

        mock_graph = MagicMock()
        result = process_segments_file(
            str(seg_file), "测试公司", "company", mock_graph, dry_run=True
        )

        assert result["status"] == "dry_run"
        assert result["entries_added"] == 1


class TestPipelineIntegration:
    """测试端到端管道集成（无 LLM / 无 PDF 解析）"""

    @patch("build_extracts.extract_pdf_text")
    @patch("tag_segments.get_llm_client")
    @patch("ingest_v2.add_timeline_entries")
    @patch("ingest_v2.get_wiki_path")
    @patch("ingest_v2.create_wiki_template")
    @patch("ingest_v2.Graph")
    def test_full_pipeline(
        self,
        mock_graph_class,
        mock_create,
        mock_get_wiki,
        mock_add,
        mock_get_llm,
        mock_extract,
        tmp_path,
    ):
        """完整管道：PDF → extract → segments → wiki"""
        # 模拟 PDF 提取
        mock_extract.return_value = {
            "text": "公司2026年第一季度营收100亿元，同比增长30%。新产品发布，市场前景广阔。"
            + "x" * 200,
            "pages_read": 3,
            "total_pages": 3,
            "total_chars": 500,
            "error": None,
            "is_scanned": False,
        }

        # 模拟 LLM 分段
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps(
            [
                {
                    "text": "营收100亿元，同比增长30%",
                    "category": "财务",
                    "sentiment": "正面",
                    "importance": "高",
                    "topics": ["营收", "增长"],
                    "entities": ["测试公司"],
                }
            ],
            ensure_ascii=False,
        )
        mock_response.error = None
        mock_llm.chat.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # 模拟 wiki 路径
        wiki_path = tmp_path / "wiki" / "test.md"
        mock_get_wiki.return_value = wiki_path
        mock_add.return_value = 1

        mock_graph = MagicMock()
        mock_graph.get_all_companies.return_value = [{"name": "测试公司"}]
        mock_graph_class.return_value = mock_graph

        with (
            patch("build_extracts.WIKI_ROOT", tmp_path),
            patch("tag_segments.WIKI_ROOT", tmp_path),
            patch("ingest_v2.WIKI_ROOT", tmp_path),
        ):
            # Step 1: build_extract
            pdf_path = tmp_path / "companies" / "测试公司" / "raw" / "report.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_text("fake pdf")

            from build_extracts import build_extract

            result1 = build_extract("测试公司", pdf_path)
            assert result1["status"] == "success"

            extract_path = (
                tmp_path / "companies" / "测试公司" / "extracts" / "report.md"
            )
            assert extract_path.exists()

            # Step 2: tag_segments
            from tag_segments import process_extract

            result2 = process_extract("测试公司", extract_path, mock_llm)
            assert result2["status"] == "success"
            assert result2["segments"] == 1

            segment_path = (
                tmp_path / "companies" / "测试公司" / "segments" / "report.jsonl"
            )
            assert segment_path.exists()

            # Step 3: ingest segments
            from ingest_v2 import process_segments_file

            result3 = process_segments_file(
                str(segment_path), "测试公司", "company", mock_graph
            )
            assert result3["status"] == "success"
            assert result3["entries_added"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
