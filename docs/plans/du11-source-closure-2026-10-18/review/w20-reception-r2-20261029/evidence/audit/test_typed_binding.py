"""ROOT r2 neutral typed-binding counterexamples. Synthetic; no network/writes."""
import sys,pathlib,unittest
repo=pathlib.Path(r'C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints');sys.path.insert(0,str(repo/'skills/revenue-forecast-audit/scripts'))
import summary_checkpoint_observations as c
class TypedBindingRegression(unittest.TestCase):
 def value_anchor(self,text,value,unit,source):
  obs=c.claim_checkpoint_observations({'claim_id':'c','text':text,'value':value,'unit':unit},[{'fragment_id':'f','text':source,'role':'narrative','reading_state':'read','source_ref':{}}]);return next(a for a in obs['anchors']['rows'] if a['anchor_kind']=='value')
 def test_explicit_amount_unit_must_not_borrow_another_percent(self):
  for value,quoted in [('1000','1,000'),('2500','2,500'),('-1000','-1,000')]:
   with self.subTest(value=value):
    result=self.value_anchor(f'收入{value}元，同比增长10%',value,'元',f'收入{quoted}元，同比增长10%')
    self.assertEqual(result['status'],'literal_match',result)
 def test_currency_must_stay_bound_to_the_matching_number(self):
  for claim_currency,amount_currency,other_currency in [('人民币','USD','人民币'),('港币','CNY','港币'),('美元','HKD','美元')]:
   with self.subTest(claim_currency=claim_currency,amount_currency=amount_currency):
    result=self.value_anchor(f'收入12.5亿元{claim_currency}','12.5',f'亿元{claim_currency}',f'收入{amount_currency} 1,250,000,000；{other_currency}余额2元。')
    self.assertNotEqual(result['status'],'scale_equivalent',result)
 def test_plain_amount_literal_control(self):
  self.assertEqual(self.value_anchor('收入1000元','1000','元','收入1,000元')['status'],'literal_match')
 def test_single_currency_conversion_control(self):
  self.assertEqual(self.value_anchor('收入12.5亿元人民币','12.5','亿元人民币','收入1,250,000,000元人民币')['status'],'scale_equivalent')
if __name__=='__main__':unittest.main(verbosity=2)
