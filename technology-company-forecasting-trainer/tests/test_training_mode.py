import csv,json,subprocess,sys,tempfile,unittest
from datetime import datetime, timezone
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
class TrainingModeTest(unittest.TestCase):
  def test_cutoff_blocks_used_future_source(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td);(w/'mode_config.json').write_text(json.dumps({'run_mode':'historical_train','phase':'forecast','as_of':'2020-01-31T23:59:59Z','actuals_retrieval_allowed':False,'forbidden_query_terms':['fy2021 actual']}))
      (w/'source_manifest.json').write_text(json.dumps({'as_of':'2020-01-31T23:59:59Z','sources':[{'source_id':'FUT','published_at':'2020-02-01T00:00:00Z','source_time_status':'eligible_pre_cutoff','forecast_permission':'eligible'}]}))
      with (w/'assumption_register.csv').open('w',newline='') as f:csv.writer(f).writerows([['source_ids'],['FUT']])
      with (w/'forward_signal_cards.csv').open('w',newline='') as f:csv.writer(f).writerow(['signal_id','source_id','published_at','allowed_use'])
      with (w/'historical_query_log.csv').open('w',newline='') as f:csv.writer(f).writerows([['query_id','cutoff','query_text','future_outcome_terms_used'],['Q1','2020-01-31T23:59:59Z','normal historical query','false']])
      r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_time_boundary.py'),'--workspace',str(w),'--strict'],capture_output=True,text=True)
      self.assertNotEqual(r.returncode,0)

  def test_historical_manifest_cannot_disable_the_profile_cutoff(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)
      cutoff='2020-01-31T23:59:59Z'
      (w/'mode_config.json').write_text(json.dumps({
        'run_mode':'historical_train','phase':'forecast','as_of':cutoff,
        'enforce_source_cutoff':True,'actuals_retrieval_allowed':False
      }))
      (w/'run_manifest.json').write_text(json.dumps({
        'run_mode':'historical_train','as_of':cutoff,
        'time_boundary_enforced':False
      }))
      (w/'source_manifest.json').write_text(json.dumps({'as_of':cutoff,'sources':[]}))
      r=subprocess.run([
        sys.executable,str(SKILL/'scripts/validate_time_boundary.py'),
        '--workspace',str(w),'--strict'
      ],capture_output=True,text=True)
      self.assertNotEqual(r.returncode,0)
      self.assertIn('manifest-cutoff-policy',r.stdout+r.stderr)
  def test_live_mode_uses_all_current_data_and_records_snapshot_time_without_a_cutoff(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--as-of','2026-07-20','--mode','live_forecast'
      ],capture_output=True,text=True)
      self.assertEqual(scaffold.returncode,0,scaffold.stdout+scaffold.stderr)
      mode=json.loads((w/'mode_config.json').read_text())
      self.assertNotIn('enforce_source_cutoff',mode)
      self.assertNotIn('post_cutoff_policy',mode)
      self.assertNotIn('actuals_retrieval_allowed',mode)
      self.assertEqual(mode['evidence_acceptance'],'current_until_bundle_freeze')
      manifest=json.loads((w/'run_manifest.json').read_text())
      self.assertNotIn('time_boundary_enforced',manifest)
      (w/'source_manifest.json').write_text(json.dumps({
        'as_of':manifest['as_of'],
        'sources':[{
          'source_id':'NEW_CURRENT_DATA',
          'published_at':'2026-07-21T00:00:00Z',
          'source_time_status':'currently_available',
          'forecast_permission':'eligible'
        }]
      }))
      with (w/'assumption_register.csv').open('w',newline='') as f:
        csv.writer(f).writerows([['source_ids'],['NEW_CURRENT_DATA']])
      # The Trainer time validator is intentionally unavailable to live work;
      # production openness is owned by the package-boundary test.

  def test_live_scaffold_records_snapshot_time_without_requiring_as_of(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      started=datetime.now(timezone.utc)
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--mode','live_forecast'
      ],capture_output=True,text=True)
      self.assertEqual(scaffold.returncode,0,scaffold.stdout+scaffold.stderr)
      manifest=json.loads((w/'run_manifest.json').read_text())
      snapshot_at=datetime.fromisoformat(manifest['as_of'].replace('Z','+00:00'))
      self.assertGreaterEqual(snapshot_at,started)
      self.assertNotIn('time_boundary_enforced',manifest)

  def test_historical_scaffold_requires_explicit_as_of_cutoff(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--mode','historical_train'
      ],capture_output=True,text=True)
      self.assertNotEqual(scaffold.returncode,0)
      self.assertIn('historical_train requires --as-of',scaffold.stdout+scaffold.stderr)

  def test_historical_scaffold_uses_only_historical_source_statuses(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--as-of','2020-01-31','--mode','historical_train'
      ],capture_output=True,text=True)
      self.assertEqual(scaffold.returncode,0,scaffold.stdout+scaffold.stderr)
      mode=json.loads((w/'mode_config.json').read_text())
      self.assertTrue(mode['enforce_source_cutoff'])
      self.assertEqual(mode['allowed_source_statuses'],['eligible_pre_cutoff'])
      self.assertEqual(mode['post_cutoff_policy'],'quarantine')

  def test_live_forward_signal_after_initial_snapshot_is_allowed(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)
      (w/'run_manifest.json').write_text(json.dumps({
        'as_of':'2026-07-20T00:00:00Z','run_mode':'live_forecast',
        'time_boundary_enforced':False
      }))
      (w/'source_manifest.json').write_text(json.dumps({'sources':[{
        'source_id':'S1','publisher':'Regulator A','authors':['Filing Team'],
        'source_type':'regulatory_measurement',
        'origin_record_kind':'original_measurement_observation',
        'epistemic_class':'independent_external_observation',
        'root_original_source_id':'S1','derived_from_source_id':None,
        'common_origin':False,'independence_cluster':'C1',
        'measurement_method_id':'regulatory_census','role':'leading_indicator',
        'authority':'regulator','independence':'independent','directness':'direct'
      }]}))
      with (w/'forward_signal_cards.csv').open('w',newline='') as f:
        csv.writer(f).writerows([
          ['signal_id','source_id','publisher','published_at','evidence_tier','evidence_role','independence_cluster','allowed_use','model_driver'],
          ['SIG1','S1','Regulator A','2026-07-21T00:00:00Z','E1','direct_measurement','C1','monitor','demand']
        ])
      with (w/'historical_query_log.csv').open('w',newline='') as f:
        csv.writer(f).writerow(['query_id','future_outcome_terms_used','cutoff'])
      with (w/'source_independence_map.csv').open('w',newline='') as f:
        csv.writer(f).writerows([
          ['source_id','cluster_id','root_original_source_id','derived_from_source_id','relationship','common_origin','publisher','authors','measurement_method_id','independence_basis','notes'],
          ['S1','C1','S1','','original','false','Regulator A','Filing Team','regulatory_census','direct measurement','']
        ])
      r=subprocess.run([
        sys.executable,str(SKILL/'scripts/validate_forward_evidence_workspace.py'),
        '--workspace',str(w),'--strict'
      ],capture_output=True,text=True)
      self.assertEqual(r.returncode,0,r.stdout+r.stderr)

  def test_live_delivery_does_not_reapply_a_source_cutoff(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--as-of','2026-07-20','--mode','live_forecast'
      ],capture_output=True,text=True)
      self.assertEqual(scaffold.returncode,0,scaffold.stdout+scaffold.stderr)
      manifest=json.loads((w/'run_manifest.json').read_text())
      (w/'source_manifest.json').write_text(json.dumps({
        'as_of':manifest['as_of'],
        'sources':[{'source_id':'CURRENT','published_at':'2026-07-21T00:00:00Z'}]
      }))
      subprocess.run([
        sys.executable,str(SKILL/'scripts/validate_delivery.py'),
        '--workspace',str(w)
      ],capture_output=True,text=True)
      result=json.loads((w/'delivery_validation.json').read_text())
      date_check=next(c for c in result['checks'] if c['check']=='sources:date-integrity')
      self.assertTrue(date_check['passed'],date_check)

  def test_training_freeze_refuses_a_live_workspace_before_validation_or_mutation(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--mode','live_forecast'
      ],capture_output=True,text=True)
      self.assertEqual(scaffold.returncode,0,scaffold.stdout+scaffold.stderr)
      (w/'training_state.json').write_text(json.dumps({
        'case_id':'TEST-LIVE','case_role':'development','phase':'forecast'
      }))
      freeze=subprocess.run([
        sys.executable,str(SKILL/'scripts/freeze_training_forecast.py'),
        '--workspace',str(w)
      ],capture_output=True,text=True)
      self.assertNotEqual(freeze.returncode,0)
      self.assertIn('historical_train',freeze.stdout+freeze.stderr)
      self.assertFalse((w/'forecast_seal.json').exists())
      mode=json.loads((w/'mode_config.json').read_text())
      self.assertEqual(mode['phase'],'forecast')
      self.assertNotIn('actuals_retrieval_allowed',mode)
      self.assertNotIn('enforce_source_cutoff',mode)

  def test_training_freeze_accepts_historical_identity_before_research_gates(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td)/'run'
      scaffold=subprocess.run([
        sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),
        '--workspace',str(w),'--entity','TEST','--security','TEST',
        '--as-of','2020-01-31','--mode','historical_train'
      ],capture_output=True,text=True)
      self.assertEqual(scaffold.returncode,0,scaffold.stdout+scaffold.stderr)
      freeze=subprocess.run([
        sys.executable,str(SKILL/'scripts/freeze_training_forecast.py'),
        '--workspace',str(w)
      ],capture_output=True,text=True)
      self.assertNotEqual(freeze.returncode,0)
      self.assertNotIn('historical_train preflight failed',freeze.stdout+freeze.stderr)
      self.assertIn('research contract',freeze.stdout+freeze.stderr)
if __name__=='__main__':unittest.main()
