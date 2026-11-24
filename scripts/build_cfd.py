"""Build data/cfd.json: current CfD strike prices by BM unit, from the Low Carbon Contracts Company data portal.

Uses the latest daily settlement record per contract in 'Actual CfD Generation and avoided GHG emissions'
(strike prices there are already CPI-indexed to current money) and the 'CfD to BM Unit Mapping'.
Only contracts with a settlement record in the last 60 days are included, i.e. contracts that have started.
Re-run when new contracts start (a few times a year) and after the April CPI indexation.
A BM unit can carry several contracts (project phases); its output is then shared equally between them.
"""
import json, urllib.request, urllib.parse, datetime
from pathlib import Path

API = 'https://dp.lowcarboncontracts.uk/api/3/action/datastore_search'
ACTUALS = '37d1bef4-55d7-4b8e-8a47-1d24b123a20e'
MAPPING = 'c16f141d-2db9-4160-ade1-d0d19d224dc9'


def fetch(resource, **params):
    q = urllib.parse.urlencode({'resource_id': resource, **params})
    with urllib.request.urlopen(f'{API}?{q}', timeout=120) as r:
        return json.load(r)['result']['records']


recs = fetch(ACTUALS, limit=8000, sort='Settlement_Date desc',
             fields='CfD_ID,Name_of_CfD_Unit,Technology,Allocation_round,Reference_Type,Strike_Price_GBP_Per_MWh,Market_Reference_Price_GBP_Per_MWh,Settlement_Date')
newest = max(r['Settlement_Date'][:10] for r in recs)
cutoff = (datetime.date.fromisoformat(newest) - datetime.timedelta(days=60)).isoformat()
latest = {}
for r in recs:
    if r['Settlement_Date'][:10] >= cutoff:
        latest.setdefault(r['CfD_ID'], r)

out = {'_source': 'Low Carbon Contracts Company data portal (dp.lowcarboncontracts.uk)', '_asof': newest}
n = 0
for m in fetch(MAPPING, limit=2000):
    if m['Effective_date_to'] or m['CFD_Id'] not in latest:
        continue
    r = latest[m['CFD_Id']]
    rnd = r['Allocation_round']
    out.setdefault(m['BMU_Id'], []).append({
        'id': m['CFD_Id'],
        'n': r['Name_of_CfD_Unit'],
        's': round(float(r['Strike_Price_GBP_Per_MWh']), 2),
        # IMRP = intermittent (day-ahead price); BMRP = baseload (seasonal reference, fixed for six months)
        'ref': r['Reference_Type'],
        'b': round(float(r['Market_Reference_Price_GBP_Per_MWh']), 2) if r['Reference_Type'] != 'IMRP' else None,
        # From AR4 on, no difference payment is made in any hour with a negative day-ahead price
        'neg0': rnd.startswith('Allocation Round') and rnd.split()[-1].isdigit() and int(rnd.split()[-1]) >= 4,
    })
    n += 1
Path(__file__).resolve().parent.parent.joinpath('data', 'cfd.json').write_text(json.dumps(out, indent=0, ensure_ascii=False))
print(f'{n} contract-unit pairs, {len(out)-2} BM units on {len(latest)} live contracts, strike prices as of {newest}')
