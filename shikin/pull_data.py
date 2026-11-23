import json, subprocess

SID = '15eDFIvgvhEjyzcs5j-g-ZEZAldHz7Xa8iKu2vLryNpo'
CLI = '/opt/hatch/bin/hatch_gws_cli'

def get(rng, width):
    r = subprocess.run([CLI, 'sheets', 'spreadsheets', 'values', 'get', '--params', json.dumps({'spreadsheetId': SID, 'range': rng})], capture_output=True, text=True)
    rows = json.loads(r.stdout).get('values', [])
    return [(x + [''] * width)[:width] for x in rows if x and x[0]]

methods = get('手法DB!A2:P25', 16)
services = get('サービスDB!A2:AB326', 28)
entities = get('事業体DB!A2:AD263', 30)
log = get('観測ログ!A2:G200', 7)

data = {
    'methods': [
        {'id': r[0], 'cat': r[1], 'name': r[2], 'def': r[3], 'how': r[4], 'target': r[5],
         'fit': r[6], 'unfit': r[7], 'cost': r[8], 'docs': r[9], 'period': r[10],
         'collateral': r[11], 'basis': r[12], 'legal': r[13], 'checked': r[15]}
        for r in methods],
    'services': [
        {'id': r[0], 'name': r[1], 'entity': r[2], 'method': r[3], 'url': r[4],
         'fee_lo': r[5], 'fee_hi': r[6], 'fee_type': r[7], 'speed': r[8], 'amt_lo': r[9], 'amt_hi': r[10],
         'contract': r[11], 'target': r[12], 'industries': r[13], 'docs': r[14], 'registry': r[15],
         'recourse': r[16], 'online': r[17], 'review': r[18], 'results': r[19], 'features': r[20],
         'status': r[21], 'checked': r[22], 'source': r[23], 'form': r[26], 'entity_id': r[27]}
        for r in services if r[21] != '廃業'],
    'entities': [
        {'id': r[0], 'name': r[1], 'alias': r[2], 'method': r[3], 'products': r[4], 'url': r[5],
         'location': r[6], 'rep': r[7], 'status': r[8], 'status_date': r[9],
         'fee_lo': r[11], 'fee_hi': r[12], 'speed': r[13], 'amount': r[14], 'contract': r[15],
         'target': r[16], 'docs': r[17], 'registry': r[18], 'recourse': r[19], 'online': r[20],
         'observed': r[23], 'founded': r[24], 'capital': r[25], 'license': r[26], 'parent': r[27],
         'form': r[28], 'score': r[29]}
        for r in entities],
    'scores': {r[0]: r[29] for r in entities},
    'entity_names': {r[0]: r[1] for r in entities},
    'log': [{'date': r[0], 'entity': r[1], 'item': r[2], 'before': r[3], 'after': r[4]} for r in log],
}
with open('/home/hatch/workspace/affiliate-site-automation/site/data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)
print('methods', len(data['methods']), 'services', len(data['services']), 'entities', len(data['entities']), 'log', len(data['log']))
