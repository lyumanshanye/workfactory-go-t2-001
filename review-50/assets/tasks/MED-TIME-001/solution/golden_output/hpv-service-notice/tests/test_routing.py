"""Forward behavior tests; not certification of clinical appropriateness."""
import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/route_intake.py'
s=importlib.util.spec_from_file_location('router',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def sample(**kw):
    r=dict(id='new-case',as_of='2025-11-12',birth_date='2012-02-29',sex='female',prior_doses=0,full_course_reported=False,special_health=False,current_health_question=False);r.update(kw);return r

class Routing(unittest.TestCase):
    def get(self,**kw):return m.route([sample(**kw)])['cases'][0]
    def test_routine_does_not_clear(self):
        r=self.get();self.assertEqual(r['route'],'SERVICE_REVIEW');self.assertFalse(r['clinical_clearance']);self.assertFalse(r['appointment_confirmed']);self.assertNotIn('birth_date',r)
    def test_birthday(self):self.assertEqual(self.get(birth_date='2012-11-13')['route'],'AGE_REVIEW')
    def test_prelaunch(self):self.assertEqual(self.get(as_of='2025-11-09')['route'],'PRELAUNCH')
    def test_snapshot_not_expiry(self):self.assertEqual(self.get(as_of='2025-11-13')['route'],'POLICY_REVIEW')
    def test_boundary(self):self.assertEqual(self.get(birth_date='2011-11-10')['route'],'POLICY_CLARIFICATION')
    def test_unknown_history(self):self.assertEqual(self.get(prior_doses=None)['route'],'DATA_REVIEW')
    def test_health_before_prior(self):self.assertEqual(self.get(prior_doses=1,special_health=True)['route'],'CLINICIAN_REVIEW')
    def test_completed_not_restart(self):self.assertEqual(self.get(prior_doses=3,full_course_reported=True)['route'],'COURSE_RECORD_REVIEW')
    def test_prior_not_restart(self):self.assertEqual(self.get(prior_doses=1)['route'],'PRIOR_HISTORY_REVIEW')
    def test_scope_not_global_ban(self):self.assertEqual(self.get(sex='male')['route'],'PROGRAM_SCOPE_REVIEW')
    def test_missing_field(self):
        r=sample();del r['special_health']
        with self.assertRaises(ValueError):m.route([r])
    def test_bad_calendar_date(self):
        with self.assertRaises(ValueError):self.get(birth_date='2012-02-30')
    def test_boolean_dose_count(self):
        with self.assertRaises(ValueError):self.get(prior_doses=True)
    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):m.route([sample(),sample()])

if __name__=='__main__':unittest.main()
