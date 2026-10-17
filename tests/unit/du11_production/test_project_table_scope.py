"""A project name can state capacity; money totals cannot borrow that fact."""
from company_wiki.document_understanding.structure.table_purpose import qualify_table


def test_project_row_with_explicit_named_capacity_is_not_an_accounting_total():
    result = qualify_table(['项目名称 | 项目品种 | 项目总投资 | 实施主体'],
        ['年产400吨吡啶盐项目 | 吡啶盐 | 26527.49 | 本公司',
         '年产1,500吨三氯蔗糖项目 | 三氯蔗糖 | 46220.20 | 本公司',
         '合计 | 72747.69 | 60000.00'])
    assert result.eligible
    assert set(result.eligible_row_indices) >= {0, 1}


def test_project_amount_only_does_not_gain_capacity_from_neighboring_caption():
    result = qualify_table(['项目名称 | 项目总投资'],
        ['A项目 | 26527.49', '合计 | 26527.49'])
    assert not result.eligible
