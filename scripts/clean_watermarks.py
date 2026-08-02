#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Research Report Watermark Cleaner
Removes encrypted watermark strings from research report markdown files.
"""

import os
import re
import glob
import argparse


def find_watermark_pattern(text):
    """
    Identify watermark patterns in text.
    Watermarks are typically:
    - Long alphanumeric strings (20+ chars)
    - Mixed case letters and numbers
    - Not meaningful Chinese or English words
    """
    # Pattern: long strings of mixed alphanumeric characters
    # This catches strings like: PBgU8ZmUeV8XbVzQ7N9R8OoMoOmOmNiNpPtPeRnPmRbRpPsPxNnOpONZrMxO
    watermark_pattern = re.compile(r"\b[a-zA-Z0-9]{20,}\b")

    # Also catch numeric sequences like: 0100200300400500600700800
    numeric_sequence_pattern = re.compile(r"\b\d{15,}\b")

    watermarks = []

    for match in watermark_pattern.finditer(text):
        candidate = match.group()
        # Additional validation: must contain both letters and numbers
        has_letters = any(c.isalpha() for c in candidate)
        has_numbers = any(c.isdigit() for c in candidate)

        if has_letters and has_numbers:
            watermarks.append((match.start(), match.end(), candidate))

    for match in numeric_sequence_pattern.finditer(text):
        candidate = match.group()
        # Check if it's a meaningful number (like a phone number or ID) or just noise
        # If it contains repeated patterns, it's likely a watermark
        watermarks.append((match.start(), match.end(), candidate))

    return watermarks


def clean_watermarks(text, min_confidence=0):
    """
    Remove watermark patterns from text.
    Returns cleaned text and list of removed watermarks.
    """
    watermarks = find_watermark_pattern(text)

    if not watermarks:
        return text, []

    # Sort by position in reverse order to replace from end to start
    watermarks_sorted = sorted(watermarks, key=lambda x: x[0], reverse=True)

    cleaned_text = text
    removed = []

    for start, end, watermark in watermarks_sorted:
        # Check if surrounded by whitespace or punctuation (standalone)
        cleaned_text[max(0, start - 1) : start]
        cleaned_text[end : min(len(cleaned_text), end + 1)]

        # Remove the watermark and any surrounding whitespace
        cleaned_text = cleaned_text[:start] + cleaned_text[end:]
        removed.append(watermark)

    return cleaned_text, removed


def clean_file(input_path, output_path=None, dry_run=False):
    """
    Clean a single research report file.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned_content, removed = clean_watermarks(content)

    if dry_run:
        return len(removed), removed

    if removed:
        if output_path is None:
            output_path = input_path

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

    return len(removed), removed


def batch_clean_directory(directory, dry_run=False, verbose=True):
    """
    Clean all markdown files in a directory.
    """
    md_files = glob.glob(os.path.join(directory, "*.md"))

    total_files = 0
    total_cleaned = 0
    total_watermarks = 0

    for filepath in sorted(md_files):
        filename = os.path.basename(filepath)
        count, removed = clean_file(filepath, dry_run=dry_run)

        total_files += 1
        if count > 0:
            total_cleaned += 1
            total_watermarks += count
            if verbose:
                print(f"Cleaned {count} watermarks from: {filename}")
                if count <= 5:
                    for wm in removed[:3]:
                        print(f"  - {wm[:50]}...")

    print(f"\n{'=' * 60}")
    print("BATCH CLEAN SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total files scanned: {total_files}")
    print(f"Files with watermarks: {total_cleaned}")
    print(f"Total watermarks removed: {total_watermarks}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")

    return total_files, total_cleaned, total_watermarks


def main():
    parser = argparse.ArgumentParser(
        description="Clean watermarks from research reports"
    )
    parser.add_argument("--company", default="中微公司", help="Company name")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    research_dir = f"companies/{args.company}/extracts/research"

    if not os.path.exists(research_dir):
        print(f"Directory not found: {research_dir}")
        return

    batch_clean_directory(research_dir, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
