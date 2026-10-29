"""ROOT independent W20 regression expectations; source-only import, no network/writes."""
import pathlib,sys,unittest
repo=pathlib.Path(r'C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints')
sys.path.insert(0,str(repo/'skills/revenue-forecast-audit/scripts'))
import summary_checkpoint_observations as c
class RootRegressions(unittest.TestCase):
 def anchor(self,claim,text,kind):
  f={'fragment_id':'f','text':text,'role':'narrative','reading_state':'read','source_ref':{}}
  obs=c.claim_checkpoint_observations({'claim_id':'c',**claim},[f])
  return next(a for a in obs['anchors']['rows'] if a['anchor_kind']==kind)
 def test_ratio_must_not_equal_monetary_amount(self):
  self.assertNotEqual(self.anchor({'text':'金额0.1元','value':'0.1','unit':'元'},'比例10%','value')['status'],'scale_equivalent')
 def test_signed_value_must_not_lose_minus(self):
  self.assertNotEqual(self.anchor({'text':'利润5元','value':'5','unit':'元'},'亏损-5元','value')['status'],'literal_match')
 def test_yen_is_not_literal_cny_token(self):
  self.assertNotIn('CNY',c.currency_families('5日元'))
 def test_h2_is_not_full_h1_literal_anchor(self):
  self.assertNotEqual(self.anchor({'text':'2024H1收入','period':'2024H1'},'2024H2收入','period')['status'],'literal_match')
 def test_explicit_unread_support_cannot_be_positive_anchor(self):
  f={'fragment_id':'f','text':'2024H1收入1亿元人民币','role':'narrative','reading_state':'unread','source_ref':{}}
  obs=c.claim_checkpoint_observations({'claim_id':'c','text':'2024H1收入1亿元人民币','value':'1','unit':'亿元人民币','period':'2024H1','subject':'收入'},[f])
  self.assertFalse(any(a['status'] in ('literal_match','scale_equivalent') for a in obs['anchors']['rows']))
 def test_explicit_unchanged_period_remains_literal(self):
  self.assertEqual(self.anchor({'text':'2024H1收入','period':'2024H1'},'2024H1收入','period')['status'],'literal_match')
 def test_valid_same_currency_scale_equivalence_remains(self):
  self.assertEqual(self.anchor({'text':'收入12.5亿元人民币','value':'12.5','unit':'亿元人民币'},'收入1,250,000,000元人民币','value')['status'],'scale_equivalent')
if __name__=='__main__':unittest.main(verbosity=2)
