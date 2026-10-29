"""ROOT r3 same-invariant window bound regression. Synthetic, read-only."""
import os,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(os.environ.get('W20_AUDIT_REPO', r'C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints'))/'skills/revenue-forecast-audit/scripts'))
import summary_checkpoint_observations as c
class LocalWindowBound(unittest.TestCase):
 def test_far_currency_does_not_bind(self):
  for distance in (20,40,80):
   with self.subTest(distance=distance):
    text='收入1,250,000,000'+'业'*distance+'人民币余额2元'
    match=next(c._NUMBER.finditer(text))
    self.assertEqual(c._local_currency_families(text,match.start(),match.end()),set())
    obs=c.claim_checkpoint_observations({'claim_id':'c','text':'收入12.5亿元人民币','value':'12.5','unit':'亿元人民币'},[{'fragment_id':'f','role':'narrative','reading_state':'read','text':text,'source_ref':{}}])
    anchor=next(a for a in obs['anchors']['rows'] if a['anchor_kind']=='value')
    self.assertNotEqual(anchor['status'],'scale_equivalent')
 def test_near_currency_of_another_amount_does_not_donate(self):
  for text in ('收入1,250,000,000和人民币余额2元','收入1,250,000,000及CNY现金2元'):
   with self.subTest(text=text):
    obs=c.claim_checkpoint_observations({'claim_id':'c','text':'收入12.5亿元人民币','value':'12.5','unit':'亿元人民币'},[{'fragment_id':'f','role':'narrative','reading_state':'read','text':text,'source_ref':{}}])
    anchor=next(a for a in obs['anchors']['rows'] if a['anchor_kind']=='value')
    self.assertNotEqual(anchor['status'],'scale_equivalent')
 def test_left_slice_cannot_drop_marker_word_guard(self):
  for marker in ('CNY','USD','RMB'):
   with self.subTest(marker=marker):
    text='A'+marker+' '*9+'1,250,000,000'
    match=next(c._NUMBER.finditer(text))
    self.assertEqual(c._local_currency_families(text,match.start(),match.end()),set())
 def test_truly_attached_left_currency_at_window_edge(self):
  text='CNY'+' '*9+'1,250,000,000'
  match=next(c._NUMBER.finditer(text))
  self.assertEqual(c._local_currency_families(text,match.start(),match.end()),{'CNY'})
 def test_right_guard_rejects_cut_currency_word(self):
  text='1,250,000,000'+' '*9+'CNYx'
  match=next(c._NUMBER.finditer(text))
  self.assertEqual(c._local_currency_families(text,match.start(),match.end()),set())
 def test_near_explicit_currency_still_binds(self):
  text='收入1,250,000,000元人民币'
  match=next(c._NUMBER.finditer(text))
  self.assertEqual(c._local_currency_families(text,match.start(),match.end()),{'CNY'})
if __name__=='__main__':unittest.main(verbosity=2)
