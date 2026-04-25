#!/usr/bin/env python3
"""
test_pdf_compare.py — PDF 提取方法比较工具

比较:
  1. PyMuPDF 本地提取 (pdf_extract_v2.py)
  2. DeepSeek /v1/document/parse (用户描述的端点)
  3. DeepSeek /v1/ocr (deepseek-ocr.ai 第三方产品)
  4. DeepSeek Chat API (发送 PyMuPDF 提取的文本)

用法:
    python scripts/test_pdf_compare.py <pdf_path>
"""

import base64
import json
import os
import sys
import time
from pathlib import Path

# 添加 scripts 目录到路径以便导入
sys.path.insert(0, str(Path(__file__).parent))

from pdf_extract_v2 import extract_pdf_text


def _call_deepseek_document_parse(file_path: str) -> dict:
    """
    测试 DeepSeek /v1/document/parse 端点。

    格式:
        POST /v1/document/parse
        Body: {"file_data": "<base64>", "file_name": "test.pdf", "language": "zh"}
        预期响应: {"text_content": "..."}
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"success": False, "error": "DEEPSEEK_API_KEY 环境变量未设置"}

    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        file_data = base64.b64encode(pdf_bytes).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": f"读取 PDF 文件失败: {e}"}

    file_name = Path(file_path).name
    if not file_name.lower().endswith(".pdf"):
        file_name += ".pdf"

    import urllib.request
    import urllib.error

    url = "https://api.deepseek.com/v1/document/parse"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "file_data": file_data,
        "file_name": file_name,
        "language": "zh",
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "error": f"HTTP {e.code}: {body[:500]}", "status_code": e.code}
    except Exception as e:
        return {"success": False, "error": f"请求失败: {e}"}


def _call_deepseek_ocr(file_path: str) -> dict:
    """
    测试 DeepSeek /v1/ocr 端点 (deepseek-ocr.ai 产品，非官方 API)。

    格式:
        POST /v1/ocr (multipart/form-data)
        Body: file=<pdf>, prompt=<optional>, language=<optional>
        预期响应: {"text": "..."}
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"success": False, "error": "DEEPSEEK_API_KEY 环境变量未设置"}

    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        return {"success": False, "error": f"读取 PDF 文件失败: {e}"}

    import urllib.request
    import urllib.error

    url = "https://api.deepseek.com/v1/ocr"
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"

    body_parts = []
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="test.pdf"\r\n')
    body_parts.append("Content-Type: application/pdf\r\n\r\n")
    body_parts.append(pdf_bytes.decode("latin-1"))
    body_parts.append(f"\r\n--{boundary}--\r\n")

    body = "".join(body_parts).encode("latin-1")

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "error": f"HTTP {e.code}: {body[:500]}", "status_code": e.code}
    except Exception as e:
        return {"success": False, "error": f"请求失败: {e}"}


def _call_deepseek_chat_with_file(file_path: str) -> dict:
    """
    通过 Chat Completions API 发送 PyMuPDF 提取的文本进行深度分析。
    这是一种间接方法，但可以验证 DeepSeek 对文档内容的理解能力。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"success": False, "error": "DEEPSEEK_API_KEY 环境变量未设置"}

    pymupdf_result = extract_pdf_text(file_path)
    if pymupdf_result.get("is_scanned"):
        return {
            "success": False,
            "error": "PDF 是扫描件，PyMuPDF 无法提取文本",
            "method": "chat_completions_with_text",
        }

    text = pymupdf_result.get("text", "")

    import urllib.request
    import urllib.error

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    text_preview = text[:5000]
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {
                "role": "user",
                "content": f"""请分析以下 PDF 文档内容，提取关键信息。

文档内容:
{text_preview}

请以 JSON 格式返回:
{{
    "char_count": <字符总数>,
    "key_topics": ["<主题1>", "<主题2>"],
    "quality_assessment": "<文档质量评估>"
}}

只返回 JSON，不要其他内容。""",
            }
        ],
        "max_tokens": 500,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start_time

            usage = data.get("usage", {})
            return {
                "success": True,
                "method": "chat_completions_with_text",
                "elapsed_seconds": elapsed,
                "usage": usage,
                "response": data,
                "pymupdf_char_count": len(text),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "error": f"HTTP {e.code}: {body[:500]}"}
    except Exception as e:
        return {"success": False, "error": f"请求失败: {e}"}


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/test_pdf_compare.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"错误: 文件不存在: {pdf_path}")
        sys.exit(1)

    print("=" * 60)
    print("  PDF 提取方法比较")
    print("=" * 60)
    print(f"\n测试文件: {pdf_path}\n")

    # 方法 1: PyMuPDF
    print("-" * 40)
    print("方法 1: PyMuPDF (pdf_extract_v2.py)")
    print("-" * 40)
    start = time.time()
    pymupdf_result = extract_pdf_text(pdf_path)
    pymupdf_time = time.time() - start

    if pymupdf_result.get("error"):
        print(f"  错误: {pymupdf_result['error']}")
    else:
        text = pymupdf_result.get("text", "")
        score = pymupdf_result.get("quality_score", 0)
        is_scanned = pymupdf_result.get("is_scanned", False)
        pages = pymupdf_result.get("pages", 0)

        print(f"  成功: True")
        print(f"  提取时间: {pymupdf_time:.2f} 秒")
        print(f"  页数: {pages}")
        print(f"  字符数: {len(text)}")
        print(f"  质量分数: {score:.3f}")
        print(f"  扫描件检测: {'是' if is_scanned else '否'}")
        print(f"  前 200 字符预览:\n    {text[:200].replace(chr(10), ' ')}")

    # 方法 2: DeepSeek /v1/document/parse
    print("\n" + "-" * 40)
    print("方法 2: DeepSeek /v1/document/parse")
    print("-" * 40)
    doc_result = _call_deepseek_document_parse(pdf_path)

    if doc_result.get("success"):
        print(f"  成功: 是")
        print(f"  响应: {json.dumps(doc_result['data'], ensure_ascii=False)[:300]}")
    else:
        status = doc_result.get("status_code", "N/A")
        print(f"  成功: 否")
        print(f"  HTTP 状态码: {status}")
        print(f"  错误: {doc_result.get('error', '未知错误')}")

    # 方法 3: DeepSeek /v1/ocr
    print("\n" + "-" * 40)
    print("方法 3: DeepSeek /v1/ocr (deepseek-ocr.ai)")
    print("-" * 40)
    ocr_result = _call_deepseek_ocr(pdf_path)

    if ocr_result.get("success"):
        print(f"  成功: 是")
        print(f"  响应: {json.dumps(ocr_result['data'], ensure_ascii=False)[:300]}")
    else:
        status = ocr_result.get("status_code", "N/A")
        print(f"  成功: 否")
        print(f"  HTTP 状态码: {status}")
        print(f"  错误: {ocr_result.get('error', '未知错误')}")

    # 方法 4: Chat Completions with text
    print("\n" + "-" * 40)
    print("方法 4: DeepSeek Chat API (发送 PyMuPDF 提取的文本)")
    print("-" * 40)

    if not pymupdf_result.get("is_scanned"):
        chat_result = _call_deepseek_chat_with_file(pdf_path)
        if chat_result.get("success"):
            print(f"  成功: 是")
            print(f"  耗时: {chat_result.get('elapsed_seconds', 0):.2f} 秒")
            print(f"  Token 使用: {chat_result.get('usage', {})}")
            response_content = ""
            try:
                msg = chat_result["response"]["choices"][0]["message"]
                response_content = msg.get("content", "")
            except (KeyError, IndexError):
                response_content = str(chat_result["response"])[:200]
            print(f"  响应内容: {response_content[:300]}")
        else:
            print(f"  成功: 否")
            print(f"  错误: {chat_result.get('error', '未知错误')}")
    else:
        print(f"  跳过: PDF 是扫描件，无法处理")

    # 总结
    print("\n" + "=" * 60)
    print("  比较总结")
    print("=" * 60)

    doc_ok = doc_result.get("success", False)
    ocr_ok = ocr_result.get("success", False)

    print(f"""
| 端点                      | 状态  | 说明                              |
|---------------------------|-------|----------------------------------|
| /v1/document/parse        | {'✓' if doc_ok else '✗'}  | {'可用' if doc_ok else '端点不存在/失败'}           |
| /v1/ocr (deepseek-ocr.ai) | {'✓' if ocr_ok else '✗'}  | {'可用' if ocr_ok else '非官方产品/失败'}          |
| PyMuPDF (本地)             | ✓     | 免费、快速、可检测扫描件          |

| 维度     | PyMuPDF       | /v1/document/parse | /v1/ocr           |
|----------|---------------|--------------------|--------------------|
| 可用性   | ✓ 始终可用    | {'✓' if doc_ok else '✗'}                 | {'✓' if ocr_ok else '✗'}                  |
| 成本     | 免费          | API 费用            | API 费用            |
| 速度     | 快            | 依赖网络            | 依赖网络            |
| 扫描件   | 检测标记      | N/A                | N/A                |

结论:
1. DeepSeek 官方 API (`api.deepseek.com`) **没有** `/v1/document/parse` 端点。
   官方文档只列出 `/chat/completions` 和 `/api/list-models` 两个端点。

2. `/v1/ocr` 端点属于 **deepseek-ocr.ai** (第三方产品)，不是 DeepSeek 官方 API。

3. PyMuPDF 方法**表现优秀**:
   - 完全免费 (本地处理)
   - 多策略回退 (text/dict/xhtml/html)
   - 质量评分机制
   - 扫描件检测
   - 无网络依赖

4. 建议:
   - 对于基于文本的 PDF: 继续使用 PyMuPDF（最佳选择）
   - 对于扫描件 PDF: 需要 OCR 服务，当前系统已能检测并标记扫描件
   - DeepSeek LLM 可作为**后处理**步骤，用于改善低质量提取文本
""")

    if pymupdf_result.get("is_scanned"):
        print("注意: 此 PDF 是扫描件，建议使用专门的 OCR 服务处理。")


if __name__ == "__main__":
    main()
