"""Measured CJK terminal tails; no source/speaker/column proof is invented."""
from copy import deepcopy
from pathlib import Path

import pytest

from company_wiki.document_understanding.indented_tail_geometry import indented_terminal_tail_proof


LEFT = (110.87999725341797, 592.029296875, 530.76318359375, 602.4793090820312)
RIGHT = (89.87999725341797, 612.4293212890625, 110.76984405517578, 622.8793334960938)
SIZE = 10.449999809265137
TEXT = '如果公司未来不能持续获得政府支持或政府支持显著降低，将会对公司经营业绩产生不利影'


def proof(left=LEFT, right=RIGHT, size=SIZE, text=TEXT, tail='响。'):
    return indented_terminal_tail_proof(left, right, size, text, tail)


def test_actual_measured_short_tail_is_a_new_proof_not_old_overlap_pass():
    result = proof()
    assert result is not None
    assert result['basis'] == 'native_indented_terminal_tail'
    assert result['horizontal_overlap'] == pytest.approx(-0.1101531982421875)
    assert result['horizontal_overlap'] < 0
    assert result['x0_delta'] == pytest.approx(-21.0)
    assert result['vertical_gap'] == pytest.approx(9.95001220703125)
    assert result['measured_font_size'] == SIZE
    assert 'source_id' not in result and 'column' not in result


@pytest.mark.parametrize('scale,dx,dy', [(0.5, 0, 0), (2, 70, 40), (1, 100, 300)])
def test_proof_uses_font_relative_shape_not_fixed_pdf_coordinates(scale, dx, dy):
    def transform(b):
        return tuple(v * scale + (dx if i % 2 == 0 else dy) for i, v in enumerate(b))
    assert proof(transform(LEFT), transform(RIGHT), SIZE * scale,
                 text='本企业的新设备尚待确认，可能产生不利结', tail='果。')


@pytest.mark.parametrize('text,tail', [
    ('供應鏈波動或會影響客戶驗證及交付效', '率。'),
    ('这是一段尚未结束的正文，仍需观察其效', '益了。'),
    ('这是一段尚未结束的正文，仍需观察其效', '益。」'),
    ('这些原文需要保留原始汉字编码及边界𠀀', '𠀃。'),
])
def test_other_cjk_texts_and_closing_quote_remain_original_observations(text, tail):
    before = (text, tail)
    assert proof(text=text, tail=tail)
    assert (text, tail) == before


@pytest.mark.parametrize('right', [
    (20, RIGHT[1], 40, RIGHT[3]),  # neighbouring left column, no actual indent
    (150, RIGHT[1], 170, RIGHT[3]),  # starts to the right instead of indentation
    (89, 640, 110, 650),  # large gap
    (89, 580, 110, 590),  # wrong vertical direction
    (89, 601, 110, 611),  # overlaps prior line vertically
    (89, RIGHT[1], 140, RIGHT[3]),  # too wide for a terminal tail
    (89, RIGHT[1], 540, RIGHT[3]),  # exceeds body right edge
])
def test_same_original_words_with_different_layout_do_not_prove_continuity(right):
    assert proof(right=right) is None


@pytest.mark.parametrize('left,right', [
    ((20, 10, 100, 20), (10, 30, 30, 40)),  # exact8em/1em/1em gap
    ((22, 10, 142, 20), (0, 20, 30, 30)),  # exact2.2em indent and3em/quarter tail
])
def test_documented_relative_geometry_boundaries_are_inclusive(left, right):
    assert proof(left, right, 10)


@pytest.mark.parametrize('left,right', [
    ((20, 10, 99.99, 20), (10, 30, 30, 40)),  # body <8em
    ((20, 10, 100, 20), (10.01, 30, 30, 40)),  # indent <1em
    ((22.01, 10, 102.01, 20), (0, 20, 20, 30)),  # indent >2.2em
    ((20, 10, 100, 20), (10, 30.01, 30, 40)),  # gap >1em
    ((20, 10, 100, 20), (10, 30, 30.01, 40)),  # >quarter-width despite <3em
    ((20, 10, 200, 20), (10, 30, 40.01, 40)),  # >3em despite wide body
])
def test_just_outside_indentation_body_tail_and_gap_boundaries_is_rejected(left, right):
    assert proof(left, right, 10) is None


@pytest.mark.parametrize('text,tail', [
    (TEXT + '。', '响。'),  # prior assertion already terminated
    (TEXT + '。」', '响。'),
    ('A complete English body line with an unfinished impac', 't.'),
    (TEXT, 'a。'), (TEXT, '1。'), (TEXT, '一。'),
    (TEXT, '𠀁。'),  # U+20001 is a numeric CJK variant, not a lexical tail.
    (TEXT, '注1。'), (TEXT, 'a响。'),
    (TEXT, '响'), (TEXT, '响，'), (TEXT, '响……'),
    (TEXT, '响了很多。'),  # not a short terminal tail
    (TEXT, '响。另'), (TEXT, '响 。'),
    ('', '响。'), (TEXT, ''), (None, '响。'), (TEXT, None),
    ('字' * 2049, '响。'),
])
def test_unclosed_tail_footnote_latin_or_existing_terminal_left_are_rejected(text, tail):
    assert proof(text=text, tail=tail) is None


@pytest.mark.parametrize('size', [True, False, 0, -1, float('nan'), float('inf'), -float('inf'), '10'])
def test_font_must_be_positive_finite_measured_number_not_bool(size):
    assert proof(size=size) is None


@pytest.mark.parametrize('box', [
    None, [], [1, 2, 3], '1234', {1, 2, 3, 4},
    [True, 1, 50, 60], [-1, 1, 50, 60],
    [50, 1, 1, 60], [1, 60, 50, 1], [1, 1, 1, 60],
    [1, 1, float('nan'), 60], [1, 1, float('inf'), 60],
])
def test_malformed_or_nonfinite_box_cannot_supply_geometry_proof(box):
    assert proof(left=box) is None
    assert proof(right=box) is None


def test_original_lists_are_not_mutated_and_calls_are_deterministic():
    left, right = list(LEFT), list(RIGHT)
    before = deepcopy((left, right))
    assert proof(left, right) == proof(left, right)
    assert (left, right) == before


@pytest.mark.parametrize('left,right', [
    ((110, 590, 530, 620), (90, 630, 110, 640)),  # multi-line body box
    ((110, 590, 530, 600), (90, 610, 110, 640)),  # multi-line right paragraph
    ((110, 590, 530, 591), (90, 601, 110, 611)),  # too thin to be measured glyph line
    ((110, 590, 530, 600), (90, 610, 110, 611)),
])
def test_bounding_boxes_must_describe_glyph_lines_not_tall_paragraphs_or_rules(left, right):
    assert proof(left, right, 10) is None


def test_finite_inputs_cannot_publish_infinite_geometry_ratios():
    assert proof((1e-310, 0, 1e308, 1e-310),
                 (0, 2e-310, 1e-310, 3e-310), 1e-310) is None


def test_actual_worktree_module_is_loaded():
    import company_wiki.document_understanding.indented_tail_geometry as owner
    expected = Path(__file__).resolve().parents[3] / 'src/company_wiki/document_understanding/indented_tail_geometry.py'
    assert Path(owner.__file__).resolve() == expected
