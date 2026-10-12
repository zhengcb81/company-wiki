"""W04 real native excerpts, no network/model and no semantic completeness score.

Exact parser units from native-semantic-replay.json; six original SHAs pinned.
These are focused excerpt replays. Full-original replay has a separate receipt.
"""
from dataclasses import replace
import json
import pytest
from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeUnit
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence, _make_unit, _candidate_rules
from company_wiki.source_catalog.narrative_business_groups import enrich_business_groups
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

_NATIVE = json.loads(r'''
{
  "cn-h1": {
    "source_sha256": "182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe",
    "units": [
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:d24231c9cc87a22d97c0a45b76d8177c62b92eea22f84e4fc391585e66654eb2",
        "coordinates": {
          "page_number": 17,
          "paragraph_index": 9,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "针对先进逻辑、先进存储器件的高选择比、低电阻金属-半导体接触层需求，公司推出了金",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            110.87999725341797,
            178.41729736328125,
            523.6846923828125,
            192.127685546875
          ],
          "block_char_end": 40,
          "block_char_start": 0,
          "block_sha256": "f5b3f1d00bb99decbaa83cb863486d44f971fd7f7ce2961f6c5da0e4b0bcea0d",
          "pdf_block": 7
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:428a691e21114c891658a21322f9bdab7ab2605d049246480db2c447e34918f9",
        "coordinates": {
          "page_number": 17,
          "paragraph_index": 10,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "属硅化物集成系统Preforma Uniflash ®，包含原位高选择性前清洁产品SA & SU，等离子体增强",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            198.8173065185547,
            525.4877319335938,
            212.52769470214844
          ],
          "block_char_end": 55,
          "block_char_start": 0,
          "block_sha256": "9d604caf73f12c8ad7b73f30ce6c1fc8e169b3446730e5b931197a49f8cf03ea",
          "pdf_block": 8
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:6b2d3be87c0ae5cb181b436be12f3b46e2a5653b1f136bc9a1ddefc6bdfdb74c",
        "coordinates": {
          "page_number": 17,
          "paragraph_index": 11,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "化学气相沉积金属钛SPTi，和原子层沉积氮化钛ALD TiNM 产品。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            217.27035522460938,
            521.8854370117188,
            232.9276885986328
          ],
          "block_char_end": 35,
          "block_char_start": 0,
          "block_sha256": "112ff17afa6d4991f92aee62f9aac7550b5780f9af0cfb8732339aabdd34819f",
          "pdf_block": 9
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:4ac7a953f721811e444b0238849586f12d68fe8c6ea0ef98177d4de57f6131d9",
        "coordinates": {
          "page_number": 17,
          "paragraph_index": 12,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "该系列产品已交付多个先进",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            217.27035522460938,
            521.8854370117188,
            232.9276885986328
          ],
          "block_char_end": 47,
          "block_char_start": 35,
          "block_sha256": "112ff17afa6d4991f92aee62f9aac7550b5780f9af0cfb8732339aabdd34819f",
          "pdf_block": 9
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:d0c07a9e6414602c8ec261661b52264ea58d88acb4ba232e9ab2a8ec36920cf3",
        "coordinates": {
          "page_number": 17,
          "paragraph_index": 13,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "逻辑、先进存储客户，现场验证顺利推进，能够满足客户各项性能需求的同时，实现高生产效",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            241.27035522460938,
            520.3148193359375,
            251.72035217285156
          ],
          "block_char_end": 41,
          "block_char_start": 0,
          "block_sha256": "0c7a4a90d56f382379562a0eb878944ca166c64a26b9dc43e4556ee70b041feb",
          "pdf_block": 10
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:6cb36c8cf8a8e7dc03cfbc5fd1a229c57eb9db327c4a79f446ede5ea3eed56a9",
        "coordinates": {
          "page_number": 17,
          "paragraph_index": 14,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "率。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            261.67034912109375,
            530.7546997070312,
            272.1203308105469
          ],
          "block_char_end": 2,
          "block_char_start": 0,
          "block_sha256": "c4fbccd6ee2df1c22bfe7cc6dccc8c81b8f07f68ee4b2d14b4281634b268b8b9",
          "pdf_block": 11
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:4cf32a0a10a05725b0c62241e20d945050bb6fcacc17bb0087a1e65675decb19",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 39,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "公司在上",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            650.1373291015625,
            530.7660522460938,
            663.8477172851562
          ],
          "block_char_end": 47,
          "block_char_start": 43,
          "block_sha256": "7c7a1b36012bc2e3625da2195dc7b65d1ba29fc509a4ad916740797f25eb573e",
          "pdf_block": 28
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:006bba1f67ae07c5a33a9dbb5be42d1e728941c0ced59fe9264d8dc9ceb18260",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 40,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "海临港的约18 万平方米的生产和研发基地已于2024 年8 月正式投入使用，临港二期约20 万平",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            670.5372924804688,
            525.4898681640625,
            684.2476806640625
          ],
          "block_char_end": 48,
          "block_char_start": 0,
          "block_sha256": "3bd46ddffea70820fd0f72be42c5333357ece8e26d40389229407a3ad6eb67c3",
          "pdf_block": 29
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:1c8b00ba23bc78fd47cf05587274bf2d9d8065bc19401ff3346393ae5d3327e4",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 41,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "方米的生产和研发基地拟于2026 年下半年开工建设；",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            690.9373168945312,
            530.767578125,
            704.647705078125
          ],
          "block_char_end": 26,
          "block_char_start": 0,
          "block_sha256": "89286bd7f91b9675bff6fd640603be4724c6647266b4e57de11681de0225081b",
          "pdf_block": 30
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:6d8f018ea6cfa5b3b3207a033a533857de2a4945152a3100912d06701d27aa98",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 42,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "上海临港滴水湖畔约10 万平方米的总部大",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            690.9373168945312,
            530.767578125,
            704.647705078125
          ],
          "block_char_end": 46,
          "block_char_start": 26,
          "block_sha256": "89286bd7f91b9675bff6fd640603be4724c6647266b4e57de11681de0225081b",
          "pdf_block": 30
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:640a8adba7a93befaacf8262aa2a89d46d11be1c37c9380dd1f82405b97f51c4",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 43,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "楼暨研发中心已于2026 年8 月1 日举办落成典礼；",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            711.456298828125,
            525.4801025390625,
            725.1666870117188
          ],
          "block_char_end": 27,
          "block_char_start": 0,
          "block_sha256": "0b75ff461dad2881976dd208db36691b042f89faa88d48f6e58b70e9c5665b19",
          "pdf_block": 31
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:42d2dd7481ccfe8123a89b7a7b699b3d155855b59b1503066cdb9b4c08bf5b81",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 44,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "位于广州的华南总部研发及生产基地总体规",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            711.456298828125,
            525.4801025390625,
            725.1666870117188
          ],
          "block_char_end": 46,
          "block_char_start": 27,
          "block_sha256": "0b75ff461dad2881976dd208db36691b042f89faa88d48f6e58b70e9c5665b19",
          "pdf_block": 31
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:2a7accd9ed6e3a1d1a9c0a7297769438ba0ec5bf8d30bdfb1dbf8dc3b5253a93",
        "coordinates": {
          "page_number": 19,
          "paragraph_index": 45,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "划占地约130 亩，一期项目占地约50 亩，主体结构已于2026 年7 月封顶，计划2027 年投产；",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            731.8563232421875,
            525.4890747070312,
            745.5667114257812
          ],
          "block_char_end": 51,
          "block_char_start": 0,
          "block_sha256": "2e9d1242b531f5a94167fed18bdc96970849cc75a78bd73869f0e4a70715a47d",
          "pdf_block": 32
        },
        "quality_flags": []
      }
    ]
  },
  "cn-annual": {
    "source_sha256": "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
    "units": [
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:24d48496d533b1e7cd063f0f2f82f850ce2bf6082da11585d70640d5ed7bca8a",
        "coordinates": {
          "page_number": 41,
          "paragraph_index": 20,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "已有多款新型设备产品进入市场，其中部分设备已获得重复性订单，LPCVD 设备累计出货量突破",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            649.8963012695312,
            531.4869995117188,
            663.606689453125
          ],
          "block_char_end": 45,
          "block_char_start": 0,
          "block_sha256": "7f019f1c41ee83a11a2638b1b84a5002d5964bd13d32d1fcaf674878a9f68eb8",
          "pdf_block": 18
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:cef8095854757ac8ced5352442a284ef21f40506244b2f39a93f0e25cd039daf",
        "coordinates": {
          "page_number": 41,
          "paragraph_index": 21,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "三百个反应台，其他多个关键薄膜沉积设备研发项目正在顺利推进；",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            670.2963256835938,
            531.3661499023438,
            684.0067138671875
          ],
          "block_char_end": 30,
          "block_char_start": 0,
          "block_sha256": "05443e67a0bfc6aa8dddf2b5542c5d160a88a7e7d76c406cf79ce584d4f49fae",
          "pdf_block": 19
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:bd306f76e8a3fe7d1f4366b9a1af1f8a52e4af9968100c49aefb5665b8908b08",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 11,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "中微公司钨系列薄膜沉积产品：CVD（化学气相",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            110.87999725341797,
            237.33731079101562,
            531.3690795898438,
            251.04769897460938
          ],
          "block_char_end": 41,
          "block_char_start": 19,
          "block_sha256": "970024498df0691d4937f062f42399535d570232b0bf1b977bc2068d77d65b30",
          "pdf_block": 9
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:cd56e30cf27f473e35b4434ca13344452280d376e9a3d71482fca5688c6377ba",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 12,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "沉积）钨设备，HAR（高深宽比）钨设备和ALD（原子层沉积）钨设备，可覆盖存储器件所有钨",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            257.7373046875,
            531.3668212890625,
            271.44769287109375
          ],
          "block_char_end": 44,
          "block_char_start": 0,
          "block_sha256": "9dd120a8d0ac072de70c9fad83b17dd0a69a0ac444af3e7f30473738503eb23a",
          "pdf_block": 10
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:07412542862ca6cb0c48f0d56540cab8237426af029caf949fe6ef737d1764a5",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 13,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "应用；",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            279.67034912109375,
            531.3690185546875,
            290.1203308105469
          ],
          "block_char_end": 3,
          "block_char_start": 0,
          "block_sha256": "4aa51cf484ca1e4527b1efe33c2090eeca4ca729c44f5115a6f10ad80700038a",
          "pdf_block": 11
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:3b1418eb555732bcbf240fd78e8c5623aacb735be0d666f880d5878bbda623e1",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 14,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "该系列设备均已通过关键存储客户端现场验证，满足先进存储应用中所有金属互连应用（包",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            279.67034912109375,
            531.3690185546875,
            290.1203308105469
          ],
          "block_char_end": 43,
          "block_char_start": 3,
          "block_sha256": "4aa51cf484ca1e4527b1efe33c2090eeca4ca729c44f5115a6f10ad80700038a",
          "pdf_block": 11
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:150024c478a1d9c015eba37ff8b973a7fb7fce64c9d61f18d12a7cea61625719",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 15,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "含高深宽比金属互连应用）及三维存储器件字线应用各项性能指标，并获得客户重复量产订单。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            300.1893615722656,
            530.7546997070312,
            310.63934326171875
          ],
          "block_char_end": 42,
          "block_char_start": 0,
          "block_sha256": "3d5c00684d3c7a598cb401665ac5fde96f510587b89a3e2a84c2429395e32250",
          "pdf_block": 12
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:86713e92073bdd41c2ee85bcd79369f414c486359f127d7b7db30850b585a0d2",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 16,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "同时，公司钨系列产品也可满足先进逻辑器件中多道金属钨互连应用需求，已通过关键逻辑客户",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            320.58935546875,
            530.7546997070312,
            331.0393371582031
          ],
          "block_char_end": 42,
          "block_char_start": 0,
          "block_sha256": "66b9e8b52742c7a7fd1179d59c21aee0574c28879517c36e8312a49f0896a81b",
          "pdf_block": 13
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:87d58c07fe16ee70fe3a8db4974ffe7476f30d5fa596c4bf7fd1221ba7ce94db",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 17,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "端现场验证，满足先进逻辑应用中各项性能指标，已获得客户重复量产订单。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            340.9903564453125,
            530.7546997070312,
            351.4403381347656
          ],
          "block_char_end": 34,
          "block_char_start": 0,
          "block_sha256": "637e029471c9d0508f37fabc28e6da8e615ed4fdefb16879ba811169356c687a",
          "pdf_block": 14
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:15207dd426508d195988abc2ba8f390587bf00df4b78f4757e3d6a1ee30c160d",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 18,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "此外，公司钨系列",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            340.9903564453125,
            530.7546997070312,
            351.4403381347656
          ],
          "block_char_end": 42,
          "block_char_start": 34,
          "block_sha256": "637e029471c9d0508f37fabc28e6da8e615ed4fdefb16879ba811169356c687a",
          "pdf_block": 14
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:b5788a73bdbddd4d1c1efebf97ece231923a89dff4a21978625319e8db1a1bf1",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 19,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "产品也通过了特殊器件客户金属钨应用现场验证。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            361.3903503417969,
            530.7546997070312,
            371.84033203125
          ],
          "block_char_end": 22,
          "block_char_start": 0,
          "block_sha256": "a9b9092b542f42ff48f7d96c37ece9e6658946ae675d155673cf2e14aa5e9462",
          "pdf_block": 15
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:4359fbd36c0b2742f645791818320b691313dbf1474e103d9345d4871616fcfd",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 20,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "基于公司钨系列产品独特的性能优势，已顺利",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            361.3903503417969,
            530.7546997070312,
            371.84033203125
          ],
          "block_char_end": 42,
          "block_char_start": 22,
          "block_sha256": "a9b9092b542f42ff48f7d96c37ece9e6658946ae675d155673cf2e14aa5e9462",
          "pdf_block": 15
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:426706ec38935e8c1772335884e08ddf4151cdff596a6db4087caa4a05021498",
        "coordinates": {
          "page_number": 44,
          "paragraph_index": 21,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "完成先进逻辑，先进存储和特殊器件的现场验证，未来将进一步扩大市场占有率。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            381.9103698730469,
            467.7569885253906,
            392.3603515625
          ],
          "block_char_end": 36,
          "block_char_start": 0,
          "block_sha256": "cab3c433ac3f674e84af0491b7d8746f7522dda20ad474431e3f6e7be4d8dbe9",
          "pdf_block": 16
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:8c31e5b724871e6b22b8c6cd49c2d6864d47c9950aba2af7fce56f0454db9e94",
        "coordinates": {
          "page_number": 62,
          "paragraph_index": 30,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "公司科学管理供应厂商，对关键零部件供应商采取多厂商策略保障零部件",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            564.0703125,
            531.4719848632812,
            574.5203247070312
          ],
          "block_char_end": 42,
          "block_char_start": 10,
          "block_sha256": "ec3d43b394696b1d6fda69ee2866b3c03ecf6115d448c71fd7a501169ecbd3ad",
          "pdf_block": 25
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:64dca2e66d25da7c1e7ff2644d8641559a81ab1ac9c4bf90e8ce5a87df4b0b13",
        "coordinates": {
          "page_number": 62,
          "paragraph_index": 31,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "及时供应。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            584.4703369140625,
            457.317138671875,
            594.9203491210938
          ],
          "block_char_end": 5,
          "block_char_start": 0,
          "block_sha256": "504b4a40413ab0eacd515af9473e486073828cfd121decb90bad7829d57351f0",
          "pdf_block": 26
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:9b9a81d344aa8ceb783e897a37db9fa57f2a1734b881fc278c642e68207a183b",
        "coordinates": {
          "page_number": 62,
          "paragraph_index": 32,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "若未来上游供应链产能紧张形势延续，将对公司设备交期产生影响。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            584.4703369140625,
            457.317138671875,
            594.9203491210938
          ],
          "block_char_end": 35,
          "block_char_start": 5,
          "block_sha256": "504b4a40413ab0eacd515af9473e486073828cfd121decb90bad7829d57351f0",
          "pdf_block": 26
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:751de1af22092ddcdee454d37e81e34445baacee07eb1e7c8467214bfe31f89d",
        "coordinates": {
          "page_number": 40,
          "paragraph_index": 3,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "新产品开发已经取得了显著成效，近两年新开发的",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            77.82935333251953,
            530.77001953125,
            88.27935028076172
          ],
          "block_char_end": 42,
          "block_char_start": 20,
          "block_sha256": "6ffdb8f7e650c85a22c8f62bdb9abea7dcb5a585abcb344c68f2c9e541a5496e",
          "pdf_block": 2
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:d2b921214f084604cb2b1a7b37cfc419a7aeb52fef81a9e67c916fdb650cd0ce",
        "coordinates": {
          "page_number": 40,
          "paragraph_index": 4,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "LPCVD 薄膜设备和ALD 薄膜设备，已有多款新型设备顺利进入市场并获得重要客户的重复性订",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            96.69629669189453,
            531.3607177734375,
            110.40670013427734
          ],
          "block_char_end": 46,
          "block_char_start": 0,
          "block_sha256": "a9fa2b64ab93d10f19ef1c206eac83df76f54bd83d93a44a7d9126ff4f3a8a18",
          "pdf_block": 3
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:4b10de892d837a87b72fa2714bad95a1432f4e0f973f0bcca55b88ed139716c8",
        "coordinates": {
          "page_number": 40,
          "paragraph_index": 5,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "单。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            117.09629821777344,
            531.3592529296875,
            130.80670166015625
          ],
          "block_char_end": 2,
          "block_char_start": 0,
          "block_sha256": "836bb151b8e19f0860a94aa8adea2d1296e337561cbabbd40e38a9428726262b",
          "pdf_block": 4
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:8f07c1ca3fc692f2d0e644e8a50cbf997e23c8f25f7bc26e2bb8acf45bb277ef",
        "coordinates": {
          "page_number": 40,
          "paragraph_index": 6,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "其中，薄膜设备累计出货量已突破300 个反应台，其他多个关键薄膜沉积设备研发项目的研",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            117.09629821777344,
            531.3592529296875,
            130.80670166015625
          ],
          "block_char_end": 44,
          "block_char_start": 2,
          "block_sha256": "836bb151b8e19f0860a94aa8adea2d1296e337561cbabbd40e38a9428726262b",
          "pdf_block": 4
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:f2aa886e07542dec5f755ecf482cb4edfda5b4f725cb500eb198fcd056b06b68",
        "coordinates": {
          "page_number": 40,
          "paragraph_index": 7,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "发进程均比较顺利，有望尽快进入客户验证阶段。",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "zh",
        "metadata": {
          "bbox": [
            89.87999725341797,
            137.49630737304688,
            531.483154296875,
            151.20669555664062
          ],
          "block_char_end": 22,
          "block_char_start": 0,
          "block_sha256": "013792806e4d4e3944610207453360a3ec6108ff37cf92feccf9b640cd5245c3",
          "pdf_block": 5
        },
        "quality_flags": []
      }
    ]
  },
  "hk-release": {
    "source_sha256": "64d8d2038eeef993571b96bb3361b6f1a567d6e84157eb16af20d2fd9a095f0a",
    "units": [
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:1a0d83b92eaa5d8faceec318553a099ec37347582b24fe2c37a0b2b81c23f383",
        "coordinates": {
          "page_number": 1,
          "paragraph_index": 4,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "Hong Kong, 12 August 2026 – Tencent Holdings Limited (HKEX: 00700 (HKD Counter) and 80700 (RMB \nCounter), “Tencent” or “the Company”), a world-leading Internet and technology company in China, today \nannounced the unaudited consolidated results for the quarter ended 30 June 2026 (“2Q2026”). \n \nMr. Ma Huateng, Chairman and CEO of Tencent, said, “As we entered into the third quarter of the year, we \nare making substantial progress towards building a new, AI-empowered Tencent in terms of intelligence, \napplications, and infrastructure. At the intelligence level, Hy3’s production version provides users a widely \nused model with strong cost-performance metrics, and serves as a stepping-stone toward the Hy family of \nmodels attaining state-of-the-art capabilities in the future. At the application level, our WorkBuddy AI office \nproductivity service and CodeBuddy AI coding tool are achieving breakout user growth and are the clear \nleaders in their fields in China today1. At the infrastructure level, we substantially stepped up our procurement \nof compute, which will enable us to convert usage of our applications and models into revenue going forward. \nAt the same time, we continue to enhance our existing services, with sustained marketing services revenue \ngrowth, several successful recently released games, and rapidly increasing video views on Weixin Video \nAccounts.” \n \n2Q2026 Financial Highlights \nRevenues: +11% YoY, gross profit: +13% YoY, non-IFRS operating profit: +9% YoY \n▪ \nTotal revenues were RMB204.8 billion, up 11% over the second quarter of 2025 (“YoY”).  \n▪ \nGross profit was RMB118.4 billion, up 13% YoY. \n▪ \nOn a non-IFRS basis, which is intended to reflect core earnings by excluding certain one-time and/or \nnon-cash items:",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            33.959999084472656,
            148.75999450683594,
            564.4296264648438,
            483.7083740234375
          ],
          "block_char_end": 1759,
          "block_char_start": 0,
          "block_sha256": "3cc22ce6d37b33ca132f45502ec2d767e6267fb9c93394fee39d37afb6f0591e",
          "pdf_block": 6
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:64a050e8997f5b7017ec81ba26d227d8c48780e934702bd30975f27032caf98d",
        "coordinates": {
          "page_number": 2,
          "paragraph_index": 1,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "▪ \nWe recorded negative free cash flow of RMB13.8 billion for 2Q2026, as net cash generated from operating \nactivities of RMB52.7 billion was more than offset by capital expenditure payments of RMB59.3 billion, \nmedia content payments of RMB5.0 billion and lease liability payments of RMB2.2 billion. Included in our \noperating cash flow were large AI-related prepayments to provide infrastructure to support our Hy model \nenhancements, WorkBuddy and CodeBuddy inference needs, Weixin AI initiatives, and development of \nAI capabilities across our products and services, as well as to meet growing external demand for our cloud \nservices. Excluding the prepayments for compute procurement, our free cash flow would have been \nRMB37.6 billion. \n▪ \nThe fair value of our shareholdings3 in listed investee companies (excluding subsidiaries) totalled \nRMB487.2 billion as at 30 June 2026, compared with RMB547.1 billion as at 31 March 2026. The carrying \nbook value of our shareholdings in unlisted investee companies (excluding subsidiaries) was \nRMB387.9 billion as at 30 June 2026, compared with RMB365.1 billion as at 31 March 2026.  \n▪ \nDuring 2Q2026, the Company repurchased approximately 37.4 million shares on the Hong Kong Stock \nExchange for an aggregate consideration of approximately HKD16.9 billion. \n \n2Q2026 Management Discussion and Analysis \nRevenues from VAS increased by 8% year-on-year to RMB98.4 billion for 2Q2026. Domestic Games revenues \nwere RMB47.3 billion, up 17% year-on-year, driven by growth from most of our major games, with notable \ncontributions from Delta Force, VALORANT PC and MOBILE, and Roco Kingdom: World. International Games \nrevenues were RMB18.6 billion, down 0.8% year-on-year due to foreign currency movements, or up 4% year-\non-year in constant currency terms, as higher revenues from Wuthering Waves and VALORANT PC were \noffset by lower revenues from certain Supercell games. Social Networks revenues increased by 0.8% year-\non-year to RMB32.5 billion.",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            33.959999084472656,
            52.04877853393555,
            564.4290771484375,
            387.5683898925781
          ],
          "block_char_end": 1997,
          "block_char_start": 0,
          "block_sha256": "07667d3655c227a7d51d92c1d344f86f3a4fa87bed56f6d64da4d4e2fa9d2258",
          "pdf_block": 3
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:fd634041301f47ca63ba6d69f367e2946bef737e389e0de363c3f4c5570dda51",
        "coordinates": {
          "page_number": 2,
          "paragraph_index": 2,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "Revenues from Marketing Services were RMB43.6 billion for 2Q2026, up 22% year-on-year, supported by \nenhancements to our AI-driven ad recommendation model (which determines the ad shown to each user for \neach impression), upgrades to our automated campaign management solution AIM+ (which helps advertisers \npurchase performant impressions), and integration of closed-loop marketing capabilities within the Weixin \necosystem (which facilitates Weixin-integrated services, such as Mini Games and Mini Shops, to advertise \nmore effectively on Tencent-managed ad properties). Most major industry categories increased marketing \nspending on our platforms during the quarter. \n \nRevenues from FinTech and Business Services rose by 9% year-on-year to RMB60.3 billion for 2Q2026. \nFinTech Services revenue growth was mainly due to higher revenues from commercial payment, wealth \nmanagement and consumer loan services. Business Services revenue growth was primarily driven by \nincreased revenues from our cloud services, underpinned by greater demand for AI-related services, ongoing \ninternational expansion, and a more favourable pricing environment. \n \nOperating Metrics",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            33.959999084472656,
            389.79876708984375,
            564.437255859375,
            623.02001953125
          ],
          "block_char_end": 1166,
          "block_char_start": 0,
          "block_sha256": "8a4dd6231f8abf38fa2e8a2f83d53f021fadcc018a0e70f612cab8b91d1d025b",
          "pdf_block": 4
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:0a10fe2b5d582d79a0ff837598e026b7f55e5fb19a94654b862b2c6630672dcc",
        "coordinates": {
          "page_number": 3,
          "paragraph_index": 1,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "Business Review and Outlook  \n▪ \nWe released the full Hy3 production version in July 2026, which delivered a substantial step-up in \nperformance versus the Hy3 preview version, and significantly outperforms most similar-sized models. \nSince its launch, Hy3 has consistently ranked among the top 3 models globally in terms of token \nconsumption on OpenRouter5. \n▪ \nWorkBuddy is achieving rapid user growth and healthy user retention rates, with high user willingness to \npay for tokens via subscriptions and top-ups. WorkBuddy‘s market leadership is underpinned by its robust \nharness engineering, wide range of model availability, and industry-leading Skills library. \n▪ \nIn recent weeks, we have begun a small-scale prototype test for Xiaowei, the agentic AI inside Weixin. \nXiaowei is powered by a customised model, WeLM, built for user privacy, Weixin-specific use cases and \ninference efficiency. \n▪ \nVideo Accounts’ total time spent grew more than 20% year-on-year in 2Q2026, benefitting from enriched \ncontent for younger users, upgraded interactive features and a new multi-variable content ranking system. \n▪ \nOur domestic evergreen games6, Delta Force and VALORANT PC, achieved lifetime highs in average \nDAU in 2Q2026. Our new game, Roco Kingdom: World, ranked first by average DAU7 and by gross \nreceipts8 among all new mobile titles released in China year-to-date. \n▪ \nMiniclip attained breakout success in international markets as Arrows – Puzzle Escape became the most \ndownloaded mobile game globally in 2Q20269, generating robust in-app advertising revenues. \n▪ \nWe upgraded our automated campaign management solution, AIM+, with AI-powered end-to-end \nexecution capabilities for mini shop and mini drama advertisers.",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            33.959999084472656,
            52.13999938964844,
            564.427734375,
            356.12646484375
          ],
          "block_char_end": 1733,
          "block_char_start": 0,
          "block_sha256": "0ea232ec121f11176ac2f9ffb81768ec45438e1969a4e1cdb46b14ac79939ac7",
          "pdf_block": 3
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:fabc408dde4593703e58a0eb60315931a98815786eb26f76e066b1c621bc2f87",
        "coordinates": {
          "page_number": 1,
          "paragraph_index": 3,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "at Intelligence, Application and Infrastructure Levels",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            148.4600067138672,
            132.7999725341797,
            450.19598388671875,
            146.1799774169922
          ],
          "block_char_end": 54,
          "block_char_start": 0,
          "block_sha256": "522b0bdd6d6565bee23c39d2de7f7a7404c121bc58298ccd6dc64055fdfeecd9",
          "pdf_block": 5
        },
        "quality_flags": []
      }
    ]
  },
  "hk-deck": {
    "source_sha256": "b9eeeb4d903d8a15f4a3df59fbf9b513845301665991012215b0956ff5874632",
    "units": [
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:cb2d50c6c8506184e4d5b9b08619810a0619598fb164df2d82a9e445003c8c98",
        "coordinates": {
          "page_number": 10,
          "paragraph_index": 16,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "•\nUnlocks huge opportunities in productivity market, including coding and existing office work scenarios\n•\nCurrent focus is on market education and extending leadership position;",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            66.23999786376953,
            266.927978515625,
            896.9559936523438,
            352.0850524902344
          ],
          "block_char_end": 178,
          "block_char_start": 0,
          "block_sha256": "a4cd3b459484d582a6b3c9115b897f97a7d35946a03a48129c3e4a4196a1bacd",
          "pdf_block": 14
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:db1c27e5313ab2d62fcc64d1fc6420cebdaa1afd91d6787f90369f69e29883cc",
        "coordinates": {
          "page_number": 10,
          "paragraph_index": 17,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "economics to improve over time as we enhance paying user benefits and \nincrease penetration, and as we reduce token costs through agent efficiency, inference efficiency and model optimisation\n•\nTencent applications already widely used within and by enterprises (e.g., Weixin, WeCom, Tencent Meeting) – WorkBuddy provides new way to \nmonetise enterprise relationships",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            66.23999786376953,
            266.927978515625,
            896.9559936523438,
            352.0850524902344
          ],
          "block_char_end": 545,
          "block_char_start": 179,
          "block_sha256": "a4cd3b459484d582a6b3c9115b897f97a7d35946a03a48129c3e4a4196a1bacd",
          "pdf_block": 14
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:5b2ae19dd888a7d0f22a1fe80b661b5e0f07b8b6508eae557614a136ebae1b45",
        "coordinates": {
          "page_number": 18,
          "paragraph_index": 2,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "League of Legends",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            295.82000732421875,
            89.97209167480469,
            422.9164123535156,
            105.65345001220703
          ],
          "block_char_end": 17,
          "block_char_start": 0,
          "block_sha256": "d23cb318a8665a861d823375ea30b39beb5660ff62477e2719e5ef36774d34ba",
          "pdf_block": 2
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:53ccec59532d81defca9b7980cd5992768a9561d6b7e524fe058538b6ae779fd",
        "coordinates": {
          "page_number": 18,
          "paragraph_index": 3,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "Arrows – Puzzle Escape",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            279.2200012207031,
            362.8437805175781,
            439.3807373046875,
            378.4983825683594
          ],
          "block_char_end": 22,
          "block_char_start": 0,
          "block_sha256": "e89dc68f6ef0852761e711995f9b46a28501a0668c4553a3b765000b2e009a58",
          "pdf_block": 3
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:c66dccbf33e301f806a2cf4e988f625051ed1f77ea2a8123509cf6a4361572bd",
        "coordinates": {
          "page_number": 18,
          "paragraph_index": 4,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "Warframe\n•\nDAU grew YoY and gross receipts achieved lifetime high in 2Q26, benefiting from a new \nwolf-themed Prime Warframe, Voruna Prime, and new storyline Jade Shadows: \nConstellations\n•\nTennoCon 2026 in July unveiled Warframe’s next major content update, Tau, bringing \nplayers to the homeworld of the Sentients",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            81.02400207519531,
            226.45379638671875,
            641.26953125,
            330.1015930175781
          ],
          "block_char_end": 315,
          "block_char_start": 0,
          "block_sha256": "bd0d21377167394f87d849d5d149e8056c7856e86e98c1f4e0fb4d7a922d4f8b",
          "pdf_block": 4
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:d6eef5bc3713dbcf119196dd537d4f2c61b2233c4a970ee54d5e5221ee33f84a",
        "coordinates": {
          "page_number": 18,
          "paragraph_index": 5,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "•\nDAU increased YoY in 2Q26, mainly driven by ARAM: Mayhem mode\n•\nLeague Classic, a nostalgic mode launched in July, re-engages longtime fans by recreating \nearly-era gameplay with pre-rework champions, classic runes, and original Summoner’s Rift \nmap layout",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            81.02400207519531,
            116.37199401855469,
            641.2628784179688,
            186.01161193847656
          ],
          "block_char_end": 258,
          "block_char_start": 0,
          "block_sha256": "57146645520c1e3f6a47ddcaec8478ec636f2c0ec880c750936c33a654228df5",
          "pdf_block": 5
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:27bca92e3854e91241671f617a579c9aac52bcfd99d45b1c8e8e0f69e72f990d",
        "coordinates": {
          "page_number": 18,
          "paragraph_index": 6,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "•\n#1 downloaded mobile game globally in 2Q261. Collision-free clearing of intricate mazes \nprovides deeply satisfying and self-paced game experience\n•\nDemonstrates that the innovative capabilities of Miniclip’s family of studios, supported by \nMiniclip’s publishing expertise, can together pioneer and break out leaders in new genres of \ncasual game\n•\nMonetises via in-app-advertising, revenue reported in marketing services segment",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            81.0719985961914,
            382.5802917480469,
            641.28955078125,
            490.0199890136719
          ],
          "block_char_end": 432,
          "block_char_start": 0,
          "block_sha256": "5e65c8a4e77d0c794f70c0ced9dce4eddad995aaede5a5d761e625f463e1dd01",
          "pdf_block": 6
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:1fc79125d67b6cc3a0189a60c9a997e60cb2756f419a5e0d3fa20780f8ab0380",
        "coordinates": {
          "page_number": 20,
          "paragraph_index": 15,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "•\nAI-related demand translated into increased revenue across GPU rental, \nModel-as-a-Service, and WorkBuddy & CodeBuddy, although we are still \ncompute constrained",
        "source_role": "company_filing",
        "unit_kind": "pdf_text_block",
        "parser_name": "selective_narrative_parser",
        "parser_version": "0.1.1",
        "language": "en",
        "metadata": {
          "bbox": [
            436.25,
            375.9020080566406,
            908.4095458984375,
            423.9715881347656
          ],
          "block_char_end": 163,
          "block_char_start": 0,
          "block_sha256": "f72a0616b9a23e4b3e833677fdb4a7c5b4b66792ebf75a50b3056a4d46529b70",
          "pdf_block": 15
        },
        "quality_flags": []
      }
    ]
  },
  "us-release": {
    "source_sha256": "8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e",
    "units": [
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:50260e8e8a29c38390bc653e2efbb5d3c9c44e98ed81bd97b5578057658db28a",
        "coordinates": {
          "page_number": null,
          "paragraph_index": 11,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "“We are advancing the frontier on the cost-to-outcome curve, ensuring every customer can turn tokens into business results,\" said Satya Nadella, chairman and chief executive officer of Microsoft. “This year, Azure revenue surpassed $100 billion for the first time, and Microsoft 365 Copilot reached over 30 million paid seats, reflecting the confidence customers are placing in us to power their AI transformation.”",
        "source_role": "company_filing",
        "unit_kind": "html_paragraph",
        "parser_name": "cwp_document_normalization",
        "parser_version": "1.0.0",
        "language": "en",
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "html",
          "source_sha256": "8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e",
          "source_locator": "cwp-html-dom/1|n=0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.8",
          "transform": "html_visible_text_v1",
          "dom_path": "0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.8",
          "backend": "html.parser",
          "normalization_quality": {
            "coverage_complete": true,
            "opaque_pages": [],
            "errors": []
          }
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:fd992daade4e6ba4f3b6b1d2f85fbbd570a94839daea3e3368a7d843a244f364",
        "coordinates": {
          "page_number": null,
          "paragraph_index": 57,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "Microsoft Cloud revenue was $59.3 billion and increased 27%, and commercial remaining performance obligation increased 84% to $678 billion.",
        "source_role": "company_filing",
        "unit_kind": "html_paragraph",
        "parser_name": "cwp_document_normalization",
        "parser_version": "1.0.0",
        "language": "en",
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "html",
          "source_sha256": "8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e",
          "source_locator": "cwp-html-dom/1|n=0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.15",
          "transform": "html_visible_text_v1",
          "dom_path": "0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.15",
          "backend": "html.parser",
          "normalization_quality": {
            "coverage_complete": true,
            "opaque_pages": [],
            "errors": []
          }
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:c01c9f490fc0c84040206f7b3691040cac1d48f2c74ca57de6a21ae1d236d2ae",
        "coordinates": {
          "page_number": null,
          "paragraph_index": 59,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "· Microsoft 365 Commercial cloud revenue increased 16% when adjusted for the prior year comparable that benefited from 2 points of in-period revenue recognition. On a reported basis, Microsoft 365 Commercial cloud revenue increased 14%.",
        "source_role": "company_filing",
        "unit_kind": "html_paragraph",
        "parser_name": "cwp_document_normalization",
        "parser_version": "1.0.0",
        "language": "en",
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "html",
          "source_sha256": "8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e",
          "source_locator": "cwp-html-dom/1|n=0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.17",
          "transform": "html_visible_text_v1",
          "dom_path": "0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.17",
          "backend": "html.parser",
          "normalization_quality": {
            "coverage_complete": true,
            "opaque_pages": [],
            "errors": []
          }
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:02aa2d8c2b2e4c75862e50a7f2595efdcb82ed204d1a7614bbbb5dd209522db3",
        "coordinates": {
          "page_number": null,
          "paragraph_index": 60,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "· Microsoft 365 Consumer cloud revenue increased 24% (up 22% in constant currency)",
        "source_role": "company_filing",
        "unit_kind": "html_paragraph",
        "parser_name": "cwp_document_normalization",
        "parser_version": "1.0.0",
        "language": "en",
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "html",
          "source_sha256": "8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e",
          "source_locator": "cwp-html-dom/1|n=0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.18",
          "transform": "html_visible_text_v1",
          "dom_path": "0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.18",
          "backend": "html.parser",
          "normalization_quality": {
            "coverage_complete": true,
            "opaque_pages": [],
            "errors": []
          }
        },
        "quality_flags": []
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:971ef3c78c312b5b12b00ae5b879e8a480d6f019d9995adea80c72ac9e5c68cf",
        "coordinates": {
          "page_number": null,
          "paragraph_index": 64,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "· Azure and other cloud services revenue increased 43%",
        "source_role": "company_filing",
        "unit_kind": "html_paragraph",
        "parser_name": "cwp_document_normalization",
        "parser_version": "1.0.0",
        "language": "en",
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "html",
          "source_sha256": "8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e",
          "source_locator": "cwp-html-dom/1|n=0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.22",
          "transform": "html_visible_text_v1",
          "dom_path": "0.1.5.0.1.0.0.0.0.1.0.0.0.1.0.2.4.1.1.0.22",
          "backend": "html.parser",
          "normalization_quality": {
            "coverage_complete": true,
            "opaque_pages": [],
            "errors": []
          }
        },
        "quality_flags": []
      }
    ]
  },
  "us-slide7-ocr": {
    "source_sha256": "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4",
    "units": [
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:1a7dfd3a866633326fb5343d38924b778ea59d2b2763b21535f040612417009e",
        "coordinates": {
          "page_number": 7,
          "paragraph_index": 1,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "our consulting and support businesses. Devices and Consumer will include our Windows, XBOX, and advertising businesses. With these segment",
        "source_role": "company_filing",
        "unit_kind": "pptx_image_ocr_line",
        "parser_name": "cwp_document_normalization",
        "parser_version": "2.0.0",
        "language": "en",
        "quality_flags": [
          "ocr_used",
          "layout_ambiguous"
        ],
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "pptx",
          "source_sha256": "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4",
          "source_locator": "cwp-pptx-image-ocr/1|s=7|p=0|m=d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea|ocr=7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d|l=1|b=95.000,220.000,2359.000,259.000",
          "transform": "rapidocr-image-rgb/1",
          "slide_number": 7,
          "slide_id": 262,
          "shape_path": "0",
          "media_sha256": "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea",
          "ocr_fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
          "ocr_box": [
            95.0,
            220.0,
            2359.0,
            259.0
          ],
          "coordinate_space": "image_pixels",
          "image_width": 2560,
          "image_height": 1440,
          "ocr_line_index": 1,
          "ocr_confidence": 0.9871,
          "reading_order": "top-left-box/1",
          "table_cells_inferred": false,
          "recall_status": "unverified",
          "normalization_quality": {
            "coverage_complete": false,
            "opaque_pages": [
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15,
              16,
              17,
              18,
              19,
              20,
              21,
              22
            ],
            "errors": [],
            "ocr": {
              "fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
              "recall_status": "unverified",
              "unattempted_image_pages": [
                1,
                2,
                3,
                4,
                5,
                6,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22
              ],
              "page_statuses": {
                "7": "recognized"
              }
            }
          }
        }
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:854bb4cae94e618361cd8bf3945b5e0553b280181fed255cf9c8dad5a3a258dd",
        "coordinates": {
          "page_number": 7,
          "paragraph_index": 2,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "changes and to provide transparency to investors, we are updating our product and services reporting definitions to better represent the businesses as",
        "source_role": "company_filing",
        "unit_kind": "pptx_image_ocr_line",
        "parser_name": "cwp_document_normalization",
        "parser_version": "2.0.0",
        "language": "en",
        "quality_flags": [
          "ocr_used",
          "layout_ambiguous"
        ],
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "pptx",
          "source_sha256": "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4",
          "source_locator": "cwp-pptx-image-ocr/1|s=7|p=0|m=d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea|ocr=7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d|l=2|b=97.000,263.000,2437.000,300.000",
          "transform": "rapidocr-image-rgb/1",
          "slide_number": 7,
          "slide_id": 262,
          "shape_path": "0",
          "media_sha256": "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea",
          "ocr_fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
          "ocr_box": [
            97.0,
            263.0,
            2437.0,
            300.0
          ],
          "coordinate_space": "image_pixels",
          "image_width": 2560,
          "image_height": 1440,
          "ocr_line_index": 2,
          "ocr_confidence": 0.99461,
          "reading_order": "top-left-box/1",
          "table_cells_inferred": false,
          "recall_status": "unverified",
          "normalization_quality": {
            "coverage_complete": false,
            "opaque_pages": [
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15,
              16,
              17,
              18,
              19,
              20,
              21,
              22
            ],
            "errors": [],
            "ocr": {
              "fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
              "recall_status": "unverified",
              "unattempted_image_pages": [
                1,
                2,
                3,
                4,
                5,
                6,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22
              ],
              "page_statuses": {
                "7": "recognized"
              }
            }
          }
        }
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:6300934e4f1eea7a1430de458d54a465df0dfd3c8ebef0a8400bbcfac3904499",
        "coordinates": {
          "page_number": 7,
          "paragraph_index": 3,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "we manage them today, which will be used in our SEC filings going forward.",
        "source_role": "company_filing",
        "unit_kind": "pptx_image_ocr_line",
        "parser_name": "cwp_document_normalization",
        "parser_version": "2.0.0",
        "language": "en",
        "quality_flags": [
          "ocr_used",
          "layout_ambiguous"
        ],
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "pptx",
          "source_sha256": "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4",
          "source_locator": "cwp-pptx-image-ocr/1|s=7|p=0|m=d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea|ocr=7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d|l=3|b=93.000,304.000,1275.000,345.000",
          "transform": "rapidocr-image-rgb/1",
          "slide_number": 7,
          "slide_id": 262,
          "shape_path": "0",
          "media_sha256": "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea",
          "ocr_fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
          "ocr_box": [
            93.0,
            304.0,
            1275.0,
            345.0
          ],
          "coordinate_space": "image_pixels",
          "image_width": 2560,
          "image_height": 1440,
          "ocr_line_index": 3,
          "ocr_confidence": 0.98376,
          "reading_order": "top-left-box/1",
          "table_cells_inferred": false,
          "recall_status": "unverified",
          "normalization_quality": {
            "coverage_complete": false,
            "opaque_pages": [
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15,
              16,
              17,
              18,
              19,
              20,
              21,
              22
            ],
            "errors": [],
            "ocr": {
              "fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
              "recall_status": "unverified",
              "unattempted_image_pages": [
                1,
                2,
                3,
                4,
                5,
                6,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22
              ],
              "page_statuses": {
                "7": "recognized"
              }
            }
          }
        }
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:0a2e4c032b4adf31e4e2491f7ed78b3bc8864380332de4cae0a2e280fbe20ce5",
        "coordinates": {
          "page_number": 7,
          "paragraph_index": 8,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "· Microsoft 365 commercial cloud will now include GitHub cloud and other developer cloud services as well as Security Copilot which were",
        "source_role": "company_filing",
        "unit_kind": "pptx_image_ocr_line",
        "parser_name": "cwp_document_normalization",
        "parser_version": "2.0.0",
        "language": "en",
        "quality_flags": [
          "ocr_used",
          "layout_ambiguous"
        ],
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "pptx",
          "source_sha256": "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4",
          "source_locator": "cwp-pptx-image-ocr/1|s=7|p=0|m=d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea|ocr=7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d|l=8|b=235.000,601.000,2385.000,644.000",
          "transform": "rapidocr-image-rgb/1",
          "slide_number": 7,
          "slide_id": 262,
          "shape_path": "0",
          "media_sha256": "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea",
          "ocr_fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
          "ocr_box": [
            235.0,
            601.0,
            2385.0,
            644.0
          ],
          "coordinate_space": "image_pixels",
          "image_width": 2560,
          "image_height": 1440,
          "ocr_line_index": 8,
          "ocr_confidence": 0.98956,
          "reading_order": "top-left-box/1",
          "table_cells_inferred": false,
          "recall_status": "unverified",
          "normalization_quality": {
            "coverage_complete": false,
            "opaque_pages": [
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15,
              16,
              17,
              18,
              19,
              20,
              21,
              22
            ],
            "errors": [],
            "ocr": {
              "fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
              "recall_status": "unverified",
              "unattempted_image_pages": [
                1,
                2,
                3,
                4,
                5,
                6,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22
              ],
              "page_statuses": {
                "7": "recognized"
              }
            }
          }
        }
      },
      {
        "unit_id": "urn:company-wiki:narrative-unit:sha256:2f7ab73ce23cc5a460e0e80dfc80623b6f88ac5c93cbc202e5ada8b850993332",
        "coordinates": {
          "page_number": 7,
          "paragraph_index": 9,
          "table_index": null,
          "row_index": null,
          "column_index": null,
          "char_start": null,
          "char_end": null
        },
        "raw_text": "previously reported in Azure",
        "source_role": "company_filing",
        "unit_kind": "pptx_image_ocr_line",
        "parser_name": "cwp_document_normalization",
        "parser_version": "2.0.0",
        "language": "en",
        "quality_flags": [
          "ocr_used",
          "layout_ambiguous"
        ],
        "metadata": {
          "normalization_schema": "cwp-document-normalization/1",
          "format": "pptx",
          "source_sha256": "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4",
          "source_locator": "cwp-pptx-image-ocr/1|s=7|p=0|m=d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea|ocr=7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d|l=9|b=262.000,645.000,702.000,690.000",
          "transform": "rapidocr-image-rgb/1",
          "slide_number": 7,
          "slide_id": 262,
          "shape_path": "0",
          "media_sha256": "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea",
          "ocr_fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
          "ocr_box": [
            262.0,
            645.0,
            702.0,
            690.0
          ],
          "coordinate_space": "image_pixels",
          "image_width": 2560,
          "image_height": 1440,
          "ocr_line_index": 9,
          "ocr_confidence": 0.98433,
          "reading_order": "top-left-box/1",
          "table_cells_inferred": false,
          "recall_status": "unverified",
          "normalization_quality": {
            "coverage_complete": false,
            "opaque_pages": [
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15,
              16,
              17,
              18,
              19,
              20,
              21,
              22
            ],
            "errors": [],
            "ocr": {
              "fingerprint": "7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d",
              "recall_status": "unverified",
              "unattempted_image_pages": [
                1,
                2,
                3,
                4,
                5,
                6,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22
              ],
              "page_statuses": {
                "7": "recognized"
              }
            }
          }
        }
      }
    ]
  }
}
''')


def native(key, *, page=None, indices=None):
    source=_NATIVE[key]
    return tuple(NarrativeUnit(source_id=source_id_for_sha256(source["source_sha256"]),
        coordinates=EvidenceCoordinates.from_dict(row["coordinates"]),
        **{k:v for k,v in row.items() if k != "coordinates"})
        for row in source["units"] if (page is None or row["coordinates"]["page_number"]==page)
        and (indices is None or row["coordinates"]["paragraph_index"] in indices))


def package(members,version="0.8.0",limit=96):
    sha=members[0].source_id.rsplit(":",1)[-1]
    doc=DocumentStructure(source_id=members[0].source_id,source_sha256=sha,
        language=members[0].language,units=tuple(members),line_count=len(members))
    return select_narrative_evidence(doc,title="Company business results",
        existing_kind="investor_relations",max_selected=limit,
        **({} if version is None else {"selector_version":version}))


def assert_originals(result,members):
    expected={u.coordinates.locator():u for u in members}
    assert set(expected).issubset({s.locator for s in result.evidence_spans})
    for span in result.evidence_spans:
        if span.locator in expected:
            u=expected[span.locator]
            assert (span.raw_text,span.parser_name,span.parser_version,tuple(sorted(span.quality_flags)))==(u.raw_text,u.parser_name,u.parser_version,tuple(sorted(u.quality_flags)))


@pytest.mark.parametrize("page,indices",[(1,[4]),(2,[1]),(2,[2]),(3,[1])])
def test_real_mixed_release_preserves_whole_original(page,indices):
    members=native("hk-release",page=page,indices=indices)
    assert_originals(package(members),members)
    assert all(len(u.raw_text)<=4800 for u in members)


def test_real_operating_seats_rpo_and_comparability_not_blanket_finance():
    members=native("us-release")
    assert_originals(package(members),members)
    assert package(members,"0.7.1").evidence_spans==()
    assert [s.to_dict() for s in package(members,None).evidence_spans]==[s.to_dict() for s in package(members).evidence_spans]


@pytest.mark.parametrize("key,page",[("cn-h1",17),("cn-annual",41),("cn-annual",44),("cn-annual",62)])
def test_real_cn_business_subject_event_quantity_and_conditional_risk(key,page):
    members=native(key,page=page)
    assert_originals(package(members),members)


def test_real_lpcvd_quantity_stays_with_original_product_chinese_unit():
    members=native("cn-annual",page=41)
    result=package(members)
    assert_originals(result,members)
    assert any("LPCVD" in g["raw_text"] and "三百个反应台" in g["raw_text"] for g in result.summary_input()["evidence"])


def test_real_semicolon_keeps_current_market_education_scope():
    members=native("hk-deck",page=10)
    result=package(members)
    assert_originals(result,members)
    assert len(result.summary_input()["evidence"])==1


def test_real_visual_nearest_title_keeps_arrows_not_other_game():
    result=package(native("hk-deck",page=18))
    arrows=next(g for g in result.summary_input()["evidence"] if "Monetises via in-app-advertising" in g["raw_text"])
    assert "Arrows – Puzzle Escape" in arrows["raw_text"]
    assert "League of Legends" not in arrows["raw_text"]
    assert "Warframe" not in arrows["raw_text"]
    assert "marketing services segment" in arrows["raw_text"]


def test_real_compute_conversion_preserves_although_constrained():
    members=native("hk-deck",page=20)
    assert_originals(package(members),members)


def fake(text,*,index=0,kind="html_paragraph",metadata=None):
    unit=_make_unit(source_id=source_id_for_sha256("a"*64),parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=index),raw_text=text,
        unit_kind=kind,source_role="company_filing",language="en",metadata=metadata or {})
    return replace(unit,parser_name="cwp_document_normalization")


@pytest.mark.parametrize("text",["Revenue increased 20% to $10 billion.","EPS increased 20% to $1.20.",
    "Total assets were $20 billion and liabilities were $10 billion.","Operating income was $2 billion, up 20%.",
    "Revenue increased 20% while our product philosophy remains unchanged."])
def test_plain_accounting_and_boilerplate_excluded(text):
    assert package((fake(text),)).evidence_spans==()


@pytest.mark.parametrize("kind",["pdf_table_row","html_table_cell","docx_table_cell","pptx_table_cell"])
def test_business_number_does_not_lift_financial_table_row(kind):
    unit=replace(fake("Cloud services revenue increased 43% in constant currency.",kind=kind),
        coordinates=EvidenceCoordinates(table_index=0,row_index=0,column_index=0))
    assert package((unit,)).evidence_spans==()


def test_over_local_limit_is_explicitly_omitted_never_clipped():
    text="Our service uses model routing to reduce token costs. "+"x"*4800
    unit=fake(text)
    result=enrich_business_groups((unit,),initial_candidates=(),initial_group_ids={},
        rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,preserve_operating_context=True)
    assert unit.unit_id in result.excluded_unit_ids
    assert any(d.reason=="business_group_character_limit" for d in result.diagnostics)
    assert all(c.unit.raw_text==text for c in result.candidates)
    assert package((unit,)).evidence_spans==()


@pytest.mark.parametrize("change",["source","actor","page","block"])
def test_semicolon_cannot_cross_real_boundary(change):
    members = list(native("hk-deck", page=10))
    right = members[1]
    if change == "source":
        right = replace(right, source_id=source_id_for_sha256("b"*64))
    elif change == "actor":
        right = replace(right, source_role="analyst")
    elif change == "page":
        right = replace(right, coordinates=replace(right.coordinates, page_number=11))
    else:
        right = replace(right, metadata={**right.metadata, "pdf_block":99,
            "block_sha256":"b"*64, "bbox":[0,500,20,510]})
    members[1]=right
    result=package(members)
    assert not any("Current focus is on market education" in g["raw_text"] and "economics to improve" in g["raw_text"] for g in result.summary_input()["evidence"])


def test_restored_ids_only_include_successful_bounded_native_reconstruction():
    small=fake("Our service uses model routing to reduce token costs.")
    large=fake(small.raw_text+" "+"x"*4800,index=1)
    result=enrich_business_groups((small,large),initial_candidates=(),initial_group_ids={},
        rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,preserve_operating_context=True)
    assert small.unit_id in result.restored_unit_ids
    assert large.unit_id not in result.restored_unit_ids
    assert large.unit_id in result.excluded_unit_ids


def test_distinct_pdf_bullets_are_independent_even_without_full_stop():
    first=native("hk-deck",page=20)[0]
    second=replace(first,unit_id="urn:company-wiki:narrative-unit:sha256:"+"d"*64,
        raw_text="• Our new service uses model routing to reduce token costs",
        coordinates=replace(first.coordinates,paragraph_index=16),
        metadata={**first.metadata,"pdf_block":16,"block_sha256":"b"*64,
            "bbox":[436.25,425,908.40,450]})
    result=package((first,second))
    assert_originals(result,(first,second))
    assert len(result.summary_input()["evidence"])==2


def test_character_overrun_fragment_chain_is_atomic_omission_not_head_only_recovery():
    base=native("cn-h1",page=17)[0]
    members=tuple(replace(base,unit_id="urn:company-wiki:narrative-unit:sha256:"+f"{i:064x}",
        raw_text=("公司产品通过现场验证并获得客户重复订单，" if i==0 else "这是同一句的连续限定内容，"*20)+("仍受限。" if i==8 else ""),
        coordinates=replace(base.coordinates,paragraph_index=i),
        metadata={"pdf_block":i,"block_sha256":f"{i:064x}","bbox":[0,20*i,400,20*i+10]})
        for i in range(9))
    result=enrich_business_groups(members,initial_candidates=(),initial_group_ids={},
        rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,preserve_operating_context=True)
    assert {u.unit_id for u in members} <= result.excluded_unit_ids
    assert not result.restored_unit_ids
    assert any(d.reason=="business_group_character_limit" for d in result.diagnostics)
    assert package(members).evidence_spans==()


def test_fundraising_native_table_group_keeps_separate_atomic_owner():
    from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
    unit=native("cn-h1",page=17)[0]
    gid="urn:company-wiki:fundraising-context:sha256:"+"c"*64
    initial=(EvidenceCandidate(unit,("capacity_projects",),("fundraising_table_context",),8),)
    result=enrich_business_groups((unit,),initial_candidates=initial,initial_group_ids={unit.unit_id:gid},
        rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,preserve_operating_context=True)
    assert result.group_ids[unit.unit_id]==gid
    assert unit.unit_id not in result.restored_unit_ids


def test_broader_film_metric_never_relabelled_as_lpcvd_specific_shipments():
    members=native("cn-annual",page=40)+native("cn-annual",page=41)
    groups=package(members).summary_input()["evidence"]
    specific=next(g for g in groups if "三百个反应台" in g["raw_text"])
    assert "LPCVD 设备累计出货量突破" in specific["raw_text"]
    assert "薄膜设备累计出货量已突破300" not in specific["raw_text"]


def test_base_execution_windows_2026_h2_and_2027_are_original_not_invented():
    members=native("cn-h1",page=19)
    result=package(members)
    assert_originals(result,members)
    assert any("拟于2026 年下半年开工建设" in g["raw_text"] for g in result.summary_input()["evidence"])
    assert any("计划2027 年投产" in g["raw_text"] for g in result.summary_input()["evidence"])


def test_native_slide7_ocr_retains_original_boxes_flags_and_comparison_scope():
    members=native("us-slide7-ocr",page=7,indices=[8,9])
    result=package(members)
    assert_originals(result,members)
    assert len(result.summary_input()["evidence"])==1
    assert "previously reported in Azure" in result.summary_input()["evidence"][0]["raw_text"]
    for span in result.evidence_spans:
        assert {"ocr_used","layout_ambiguous"} <= set(span.quality_flags)
        assert span.structured_value["recall_status"]=="unverified"
        assert span.structured_value["coordinate_space"]=="image_pixels"


def test_native_missing_ocr_first_line_is_unknown_never_invented_by_selection():
    members=native("us-slide7-ocr",page=7,indices=[1,2,3])
    result=package(members)
    assert_originals(result,members)
    assert all("Agents and Infra will include" not in span.raw_text for span in result.evidence_spans)
    assert all("layout_ambiguous" in span.quality_flags for span in result.evidence_spans)


@pytest.mark.parametrize("key,page,indices",[("hk-release",1,[4]),("hk-release",2,[1]),("hk-release",3,[1]),("us-release",None,[11,57,59,60,64])])
def test_explicit_old_selector_keeps_old_native_misses(key,page,indices):
    assert package(native(key,page=page,indices=indices),"0.7.1").evidence_spans==()


def test_whole_native_release_paragraph_does_not_inherit_title_window_limit():
    members=native("hk-release",page=1,indices=[3,4])
    result=package(members)
    body=next(u for u in members if u.coordinates.paragraph_index==4)
    assert_originals(result,(body,))
    assert not any("at Intelligence, Application and Infrastructure Levels" in g["raw_text"] and body.raw_text in g["raw_text"] for g in result.summary_input()["evidence"])


def test_actual_commercialization_milestones_get_existing_budget_reason():
    for members in (native("cn-h1",page=17),native("cn-annual",page=41)):
        result=enrich_business_groups(members,initial_candidates=(),initial_group_ids={},
            rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,preserve_operating_context=True)
        assert any("new_product_commercialization_milestone" in c.reasons for c in result.candidates)


# W04 stage-classification amendment: proof of operating progress is distinct
# from a contractual step. Business meaning stays original in both categories.
def stage_fact(text):
    from company_wiki.source_catalog.narrative_business_groups import _operating_fact
    return _operating_fact(text, _candidate_rules(selector_version="0.8.0"))


@pytest.mark.parametrize("text", [
    "新型农业设备已经交付给三家客户，现场验证正在推进。",
    "诊断产品首次交付医院，正在进行现场验证。",
    "电池系统累计出货达到一万套，已获重复订单。",
    "新服务已向首批客户交付，客户验证顺利推进。",
    "公司产品通过客户验证并获得重复订单。",
    "设备已通过客户验证，但尚未实现量产。",
    "LPCVD设备累计出货量突破三百个反应台。",
    "该系列产品已交付多个先进逻辑客户，现场验证顺利推进。",
    "The equipment has already been delivered to three agricultural customers.",
    "Our diagnostic product was first shipped to hospitals this quarter.",
    "Our platforms have completed customer qualification.",
    "We have delivered the first batch of battery systems to customers.",
    "The software product has secured repeat orders from enterprise customers.",
    "Our product's customer qualification is progressing.",
    "Cumulative shipments of the equipment reached300 units.",
])
def test_stage_classifier_proven_operating_progress(text):
    assert "new_product_commercialization_milestone" in stage_fact(text).reasons


@pytest.mark.parametrize("text", [
    "备品备件产品交付后，客户具有自行使用产品的权利并承担该产品可能发生价格波动或毁损的风险。",
    "主要分为两个节点：①设备交付后30-45日，收取85-90%到货款。",
    "流动资金的增加加强采供销能力，为设备产品的按时生产和交付提供基础。",
    "产品交付按时率保持较高水平。",
    "公司设备从设计到生产交付的常规流程包括采购和组装。",
    "产品尚未交付客户，仍处于验证计划阶段。",
    "新产品预计明年首次交付。",
    "产品已交付后，方可确认收入。",
    "Our equipment is delivered according to customer contract terms.",
    "After the product has been delivered, customers pay the remaining balance.",
    "Once the new system has been delivered, ownership and risk pass to the customer.",
    "The product has not yet been delivered to customers.",
    "The equipment will be delivered after payment.",
    "The product is expected to be delivered after qualification.",
    "Products are delivered within30 days after a purchase order.",
    "The new platform brand is popular, but its launch schedule remains unknown.",
    "The equipment underwent routine inspection.",
])
def test_stage_classifier_routine_or_unproven_delivery_not_commercialization(text):
    assert "new_product_commercialization_milestone" not in stage_fact(text).reasons


@pytest.mark.parametrize("text", [
    "新产品已交付第一家客户，交付后按合同收取货款。",
    "The new system has already been delivered to its first customer, and payment follows the contract terms.",
    "预计明年扩大产能；产品已交付三家客户。",
    "公司产品已交付客户，但付款延迟。",
])
def test_stage_classifier_routine_terms_cannot_erase_independent_proven_stage(text):
    assert "new_product_commercialization_milestone" in stage_fact(text).reasons


@pytest.mark.parametrize("text", [
    "新型农业设备已经交付给三家客户，现场验证正在推进。",
    "The equipment has already been delivered to three agricultural customers.",
])
def test_stage_classifier_realized_progress_public_leaf_keeps_original(text):
    unit=fake(text)
    result=enrich_business_groups((unit,),initial_candidates=(),initial_group_ids={},
        rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,
        preserve_operating_context=True)
    assert result.candidates[0].unit==unit
    assert "new_product_commercialization_milestone" in result.candidates[0].reasons
    assert_originals(package((unit,)), (unit,))


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0", "0.7.1"])
def test_stage_classifier_explicit_legacy_native_fingerprint_unchanged(version):
    import hashlib
    members=native("cn-h1",page=17)+native("cn-h1",page=19)
    result=package(members,version)
    payload={"candidate_count":result.candidate_count,"status":result.status,
        "evidence_spans":[span.to_dict() for span in result.evidence_spans]}
    observed=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()
    assert observed=="54c4bd4dd96d6366613ccbe1aca1f00847d515cd15a574843114b3a1db1e49ce"

_STAGE_NATIVE_H1_COMPLETED = json.loads(r'''
[
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:2ac378360e521b34af633e4c383a9d6f165adfbedb8da99a170edcfc30fc87bd",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 2,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "求的同时，设备的薄膜均一性，污染物控制和生产效率均达到世界先进水平。",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        77.82935333251953,
        530.7546997070312,
        88.27935028076172
      ],
      "block_char_end": 34,
      "block_char_start": 0,
      "block_sha256": "b9d79eee878dbee39d2439c133ce7e60ab6ab3941f5567ea3886a84a23e47d18",
      "pdf_block": 2
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:68013aa19efaa16a8ed0dbc3fd73aff84cc23282eb1fcd960125c5727144fbdc",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 3,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "该系列设备已付运",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        77.82935333251953,
        530.7546997070312,
        88.27935028076172
      ],
      "block_char_end": 42,
      "block_char_start": 34,
      "block_sha256": "b9d79eee878dbee39d2439c133ce7e60ab6ab3941f5567ea3886a84a23e47d18",
      "pdf_block": 2
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:629f86365de638e5fadd2edcd63fd997be9836397acbfaa877fa0b20d340f788",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 4,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "到多个先进逻辑客户端进行验证，已顺利通过客户现场验证。",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        96.69629669189453,
        523.4492797851562,
        110.40670013427734
      ],
      "block_char_end": 27,
      "block_char_start": 0,
      "block_sha256": "7e4e666ffbc7ea3d6ec06e073b8f17ca616818aef7bd14ed28b10fe0bf5d2a66",
      "pdf_block": 3
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:7ad9ad0e111d111c00745eaaaca7ac00111b8e92bee8264b580a6cbdd39ac972",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 5,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "其中，ALD 氮化钛薄膜也可运用",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        96.69629669189453,
        523.4492797851562,
        110.40670013427734
      ],
      "block_char_end": 43,
      "block_char_start": 27,
      "block_sha256": "7e4e666ffbc7ea3d6ec06e073b8f17ca616818aef7bd14ed28b10fe0bf5d2a66",
      "pdf_block": 3
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:9b9027a5071076bc34acaab087b721cc51e8c073ac483b955082c40092467097",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 6,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "于先进存储器件中钨填充阻挡层和粘结层、先进存储及先进封装中的电容器极板等关键应用场",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        118.62935638427734,
        520.2037353515625,
        129.079345703125
      ],
      "block_char_end": 41,
      "block_char_start": 0,
      "block_sha256": "044bbcf475d354fd5c7770f9548c676aa1b8ce833f362d003bf6ca0bdb6c5e76",
      "pdf_block": 4
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:92e533f625e5cc411c30b0d8e8486f1c9f3f1ce59522e08c425b3f62581fcf31",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 7,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "景，公司开发的ALD 氮化钛设备可满足高深宽比及三维结构的台阶覆盖率需求及各项性能指",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        137.49630737304688,
        515.6386108398438,
        151.20669555664062
      ],
      "block_char_end": 42,
      "block_char_start": 0,
      "block_sha256": "e941280bf84db960638e8f6129e58bb51298b8d17c725943ad5f344cb92d8924",
      "pdf_block": 5
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:46087d32763ca43498ce32ad92b4e8a5a8f46ba70ab05a26fcc3823e0ece1199",
    "coordinates": {
      "page_number": 17,
      "paragraph_index": 8,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "标，并已交付多个关键客户进行现场验证，有利于进一步扩大市场规模。",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        159.55035400390625,
        425.7652893066406,
        170.00035095214844
      ],
      "block_char_end": 32,
      "block_char_start": 0,
      "block_sha256": "078fc2c58b055b7473086fb50e04de8dda8d475d59ecdb170c4dbbc17bd15fb0",
      "pdf_block": 6
    },
    "quality_flags": []
  }
]
''')
_STAGE_NATIVE_H1_PLANNED = json.loads(r'''
[
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:9ac812c10d8d1d52d8af8a440c5aba7a15aec642fea667da2b0aa813e919dd2b",
    "coordinates": {
      "page_number": 18,
      "paragraph_index": 32,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "下半年将结合客户反馈意见，加快产品开发，",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        484.7773132324219,
        536.6500244140625,
        498.4877014160156
      ],
      "block_char_end": 45,
      "block_char_start": 25,
      "block_sha256": "88c0747425bf3a249669e5c89a5c80aabcf049dabff690d6395ee2d47d8268c1",
      "pdf_block": 22
    },
    "quality_flags": []
  },
  {
    "unit_id": "urn:company-wiki:narrative-unit:sha256:8a749fc5aea3f6b716857ab55dda13e993546a62345e2495743f6f963edcbdf6",
    "coordinates": {
      "page_number": 18,
      "paragraph_index": 33,
      "table_index": null,
      "row_index": null,
      "column_index": null,
      "char_start": null,
      "char_end": null
    },
    "raw_text": "尽早付运样机至客户端开展生产验证。",
    "source_role": "company_filing",
    "unit_kind": "pdf_text_block",
    "parser_name": "selective_narrative_parser",
    "parser_version": "0.1.1",
    "language": "zh",
    "metadata": {
      "bbox": [
        89.87999725341797,
        506.7103576660156,
        268.3240051269531,
        517.1603393554688
      ],
      "block_char_end": 17,
      "block_char_start": 0,
      "block_sha256": "39a2ffb016715b7da0bfd393be23928cafd80adcf31e56c956b482767bdca9c0",
      "pdf_block": 23
    },
    "quality_flags": []
  }
]
''')


@pytest.mark.parametrize("text", [
    "该系列设备已付运到客户进行验证，已顺利通过客户现场验证。",
    "新型医疗设备进入医院测试，已经成功通过现场验证。",
    "公司已将新型农业设备交付给首批客户。",
    "电池系统已发运至储能客户，现场验证持续推进。",
    "Our new equipment has successfully passed on-site customer qualification.",
    "The product has already been dispatched to its first industrial customers.",
    "Our medical equipment entered customer trials, and it has successfully passed validation.",
    "The platform has been validated by customers and has received repeat orders.",
])
def test_stage_followup_realized_synonyms_and_bounded_subject_reference(text):
    assert "new_product_commercialization_milestone" in stage_fact(text).reasons


@pytest.mark.parametrize("text", [
    "下半年将结合客户反馈意见，加快产品开发，尽早付运样机至客户端开展生产验证。",
    "公司计划明年开发新型农业设备并送客户验证。",
    "新型诊断产品预计下季度付运样机开展医院测试。",
    "设备尚未交付，计划在第三季度完成客户验证。",
    "We plan to develop a new agricultural product and ship prototypes for customer trials next quarter.",
    "The company intends to deploy the new platform in a customer pilot.",
    "Our medical product is expected to undergo customer validation next year.",
])
def test_stage_followup_future_business_progress_is_candidate_not_completed(text):
    fact=stage_fact(text)
    assert fact.eligible
    assert "project_plan_or_status" in fact.reasons
    assert "new_product_commercialization_milestone" not in fact.reasons


@pytest.mark.parametrize("text", [
    "若设备已付运，则按合同收取货款。",
    "产品付运后，客户承担所有权和毁损风险。",
    "Once the product has been dispatched, title and risk pass to the customer.",
    "Products are validated only if customers agree to pay the qualification fees.",
    "A new product name is registered but its development schedule is unknown.",
])
def test_stage_followup_conditional_procedure_or_brand_not_proven_or_planned(text):
    fact=stage_fact(text)
    assert "new_product_commercialization_milestone" not in fact.reasons
    assert "project_plan_or_status" not in fact.reasons


def stage_native(rows):
    return tuple(NarrativeUnit(source_id=source_id_for_sha256("182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe"),
        coordinates=EvidenceCoordinates.from_dict(row["coordinates"]),
        **{k:v for k,v in row.items() if k!="coordinates"}) for row in rows)


def test_stage_followup_actual_native_h1_dispatch_and_validation_retains_stage():
    from company_wiki.source_catalog.narrative_visual_units import join_unit_text
    members=stage_native(_STAGE_NATIVE_H1_COMPLETED)
    assert "new_product_commercialization_milestone" in stage_fact(join_unit_text(members)).reasons
    assert_originals(package(members),members)


def test_stage_followup_actual_native_h1_future_prototype_keeps_candidate_and_raw():
    members=stage_native(_STAGE_NATIVE_H1_PLANNED)
    result=enrich_business_groups(members,initial_candidates=(),initial_group_ids={},
        rules=_candidate_rules(selector_version="0.8.0"),respect_native_structure=True,
        preserve_operating_context=True)
    assert {c.unit.unit_id for c in result.candidates}=={u.unit_id for u in members}
    assert all("new_product_commercialization_milestone" not in c.reasons for c in result.candidates)
    assert all("project_plan_or_status" in c.reasons for c in result.candidates)
    assert_originals(package(members),members)
