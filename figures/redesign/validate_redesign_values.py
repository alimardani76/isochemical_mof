#!/usr/bin/env python3
"""Validate frozen numerical invariants before/after figure redesign."""
from __future__ import annotations
from pathlib import Path
import argparse,json
import numpy as np,pandas as pd
from data_utils import modern,read_csv,read_parquet,summary_dict

EXPECTED={
 'primary_pairs':11072,'tier20':6948,'tier30':5115,
 'primary_median':0.5835545,'primary_ci_low':0.5545650,'primary_ci_high':0.6149215,'positive_fraction':0.70502,
 'ASA':2.9964,'AVA':1.2201,'Df':-0.1457,
 'pressure_activated_pairs':3100,'pressure_suppressed_pairs':687,
}
def close(a,b,tol): return bool(np.isclose(float(a),float(b),atol=tol,rtol=0))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();root=a.project_root.resolve();rows=[]
 def check(name,actual,expected,tol=0):
  ok=(actual==expected) if tol==0 else close(actual,expected,tol);rows.append({'check':name,'actual':float(actual) if isinstance(actual,(float,np.floating)) else int(actual) if isinstance(actual,(int,np.integer)) else actual,'expected':expected,'tolerance':tol,'pass':ok});return ok
 pairs=read_parquet(modern(root,'results/step2/03_geometry_pairs/primary_geometry_pairs.parquet'));check('Figure1 frozen pair rows',len(pairs),11072)
 e=read_parquet(modern(root,'results/step3/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet'));check('Figure2 primary effect rows',len(e),11072)
 s=summary_dict(read_csv(modern(root,'results/step3/04_primary_ch4_analysis/primary_ch4_summary.csv')));check('Primary median',s['median_delta_q_mmol_g'],EXPECTED['primary_median'],5e-7);check('Primary CI low',s['bootstrap_95ci_low_median_delta_q_mmol_g'],EXPECTED['primary_ci_low'],5e-7);check('Primary CI high',s['bootstrap_95ci_high_median_delta_q_mmol_g'],EXPECTED['primary_ci_high'],5e-7);check('Primary positive fraction',s['positive_effect_fraction'],EXPECTED['positive_fraction'],5e-6)
 t=read_csv(modern(root,'results/step3/04_primary_ch4_analysis/primary_ch4_geometry_tier_summary.csv'));td={str(r.tier):int(r.pairs) for r in t.itertuples()};check('20% tier pairs',td['stronger_20pct'],6948);check('30% tier pairs',td['stronger_30pct'],5115)
 d=read_csv(modern(root,'results/step3/04_primary_ch4_analysis/primary_ch4_driver_summary.csv'));dd={str(r.driver_descriptor):float(r.median_delta_q_mmol_g) for r in d.itertuples()};check('ASA median',dd['ASA'],EXPECTED['ASA'],5e-4);check('AVA median',dd['AVA'],EXPECTED['AVA'],5e-4);check('Df median',dd['Df'],EXPECTED['Df'],5e-4);check('Descriptor class pair sum',int(pd.to_numeric(d.pairs).sum()),11072)
 ar=read_csv(modern(root,'results/step3/07_response_archetypes/response_archetype_summary.csv'));ad={str(r.archetype):int(r.pairs) for r in ar.itertuples()};check('Archetype count sum',sum(ad.values()),11072);check('Pressure activated pairs',ad['pressure_activated'],3100);check('Pressure suppressed pairs',ad['pressure_suppressed'],687)
 h3=root/'results/submission_upgrade/H3_uptake_basis_density/basis_primary_summary.csv'
 if h3.is_file():
  q=pd.read_csv(h3);vv=float(q.loc[q.metric=='v/v','median_delta'].iloc[0]);check('H3 v/v median',vv,3.7971925,5e-6)
 passed=all(r['pass'] for r in rows);report={'pinned_commit':'1e81b1961f3853417b4a5b63eee19e3aefbe07a4','all_pass':passed,'checks':rows};text=json.dumps(report,indent=2);print(text);out=a.output or (Path.cwd()/'FIGURE_VALUE_AUDIT.json');out.write_text(text,encoding='utf-8');pd.DataFrame(rows).to_csv(out.with_suffix('.csv'),index=False);return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
