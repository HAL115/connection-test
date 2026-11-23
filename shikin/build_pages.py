# Generates method / company / service / compare pages + sitemap from data.json.
# Importing build regenerates TOP + sample articles and exposes page()/CTA_BOX.
import json, re, html, os, urllib.parse
import build

BASE = '/home/hatch/workspace/affiliate-site-automation'
OUT = build.OUT

# アフィリエイトリンク（affiliates.json：サービスID → {url, banner, program, asp}）
try:
    AFF = json.load(open('affiliates.json'))
except Exception:
    AFF = {}
# Googleマップの口コミ集計（reviews.json：事業体ID → {rating, count, checked}）
try:
    REVIEWS = json.load(open('reviews.json'))
except Exception:
    REVIEWS = {}
PR_NOTICE = '<p class="note">このページには広告（アフィリエイトリンク）が含まれます。</p>'
data = json.load(open(BASE + '/site/data.json'))
methods = {m['id']: m for m in data['methods']}
services = data['services']
entities = data['entities']
ent_by_id = {e['id']: e for e in entities}
svc_by_id = {s['id']: s for s in services}
svc_by_entity = {}
svc_by_method = {}
for s in services:
    svc_by_entity.setdefault(s['entity_id'], []).append(s)
    svc_by_method.setdefault(s['method'], []).append(s)

METHOD_GROUPS = [
    ('借りる（公的・銀行系）', ['M01', 'M02', 'M03', 'M04', 'M05', 'M06']),
    ('借りる（民間の融資）', ['M07', 'M08', 'M09', 'M10', 'M11', 'M12']),
    ('売掛金を現金化する', ['M13', 'M14', 'M15', 'M16', 'M17']),
    ('公的な支援', ['M18', 'M19', 'M20']),
    ('その他の調達', ['M21', 'M22', 'M23', 'M24']),
]
MID_GROUP = {mid: g for g, mids in METHOD_GROUPS for mid in mids}

import os as _os
PROFILES = {}
if _os.path.exists(BASE + '/site/profiles.json'):
    PROFILES = json.load(open(BASE + '/site/profiles.json'))
GEOCACHE = {}
if _os.path.exists(BASE + '/site/geocache.json'):
    GEOCACHE = json.load(open(BASE + '/site/geocache.json'))

def prof(e):
    p = PROFILES.get(e['id'], {})
    out = dict(e)
    for k in ('location', 'rep', 'founded', 'capital', 'license'):
        if not (out.get(k) or '').strip() and (p.get(k) or '').strip():
            out[k] = p[k]
    out['_branches'] = p.get('branches') or []
    out['_business'] = p.get('business') or ''
    out['_psource'] = p.get('source') or ''
    return out

for d in ('methods', 'companies', 'services', 'compare'):
    os.makedirs(f'{OUT}/{d}', exist_ok=True)


def svc_chips(s):
    out = []
    if (s.get('target') or '').strip():
        out.append(s['target'].strip())
    if (s.get('online') or '').strip() == '1':
        out.append('オンライン完結')
    if (s.get('form') or '').strip() == '仲介・紹介':
        out.append('仲介・紹介')
    return ''.join(f'<span class="chip">{esc(c)}</span>' for c in out)

def esc(v):
    return html.escape(v or '')

def val(v, fallback='公表を確認できていません'):
    v = (v or '').strip()
    return esc(v) if v else fallback

def fee_text(lo, hi):
    lo, hi = (lo or '').strip(), (hi or '').strip()
    if lo and hi:
        return esc(lo if lo == hi else f'{lo}〜{hi}')
    if hi:
        return esc(hi)
    if lo:
        return esc(lo + '〜')
    return '非公表'

def amt_text(lo, hi):
    bad = lambda v: not v or v.strip() in ('―', '—', '-')
    if not bad(lo) and not bad(hi):
        return esc(f'{lo}〜{hi}')
    if not bad(hi):
        return esc(hi)
    if not bad(lo):
        return esc(lo + '〜')
    return '―'

def fee_num(s):
    m = re.search(r'([\d.]+)', s.get('fee_lo') or '')
    return float(m.group(1)) if m else 999.0

def badge_score(score):
    v = int(score) if (score or '').isdigit() else 0
    cls = '' if v >= 3 else ' low'
    return f'<span class="badge{cls}">透明性 {esc(score) if score else "―"} / 5</span>'

def kv_table(rows):
    trs = ''.join(f'<tr><th style="white-space:nowrap">{esc(k)}</th><td>{v}</td></tr>' for k, v in rows)
    return f'<div class="tblwrap"><table>{trs}</table></div>'


def crumbs(*items):
    return json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList',
                       'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': build.BASE_URL + p} for i, (n, p) in enumerate(items)]}, ensure_ascii=False)

urls = ['index.html'] + [f'articles/{f}' for f in sorted(os.listdir(f'{OUT}/articles')) if f.endswith('.html')]


# ---------- article links for method pages ----------
import glob as _glob
PILLAR_TEXTS = {}
for _p in _glob.glob(f'{BASE}/files/pillar/*.md'):
    PILLAR_TEXTS[os.path.basename(_p)[:-3] + '.html'] = open(_p).read()
PILLAR_TEXTS['guide-payment-gap.html'] = open(f'{BASE}/files/samples/サンプル_型1_状態別アドバイス.md').read()
PILLAR_TITLES = {}
for _slug, _text in PILLAR_TEXTS.items():
    _m = re.search(r'^# (.+)$', _text, flags=re.M)
    PILLAR_TITLES[_slug] = _m.group(1) if _m else _slug
_BASICS_FILES = {'basics-factoring.html': '基礎知識_ファクタリングとは.md', 'basics-2sha.html': 'サンプル_型5_基礎知識と手続き.md',
                 'basics-recourse.html': '基礎知識_償還請求権とは.md', 'basics-registry.html': '基礎知識_債権譲渡登記とは.md',
                 'basics-guarantee.html': '基礎知識_信用保証協会とは.md', 'basics-safety-net.html': '基礎知識_セーフティネット保証の認定.md'}
BASICS_TITLES = {}
for _slug, _f in _BASICS_FILES.items():
    _text = open(f'{BASE}/files/samples/{_f}').read()
    _m = re.search(r'^# (.+)$', _text, flags=re.M)
    BASICS_TITLES[_slug] = _m.group(1) if _m else _slug
MID_BASICS = {'M13': ['basics-factoring.html', 'basics-2sha.html', 'basics-recourse.html', 'basics-registry.html'],
              'M14': ['basics-factoring.html', 'basics-2sha.html', 'basics-recourse.html', 'basics-registry.html'],
              'M15': ['basics-factoring.html', 'basics-2sha.html'],
              'M16': ['basics-factoring.html'],
              'M17': ['basics-factoring.html', 'basics-registry.html'],
              'M02': ['basics-guarantee.html'],
              'M06': ['basics-safety-net.html', 'basics-guarantee.html'],
              'M04': ['basics-guarantee.html', 'basics-safety-net.html']}

def method_articles(mid, mname):
    links = []
    for bs in MID_BASICS.get(mid, []):
        links.append((f'../articles/{bs}', BASICS_TITLES[bs]))
    rel = [(slug, t) for slug, t in PILLAR_TITLES.items() if mname in PILLAR_TEXTS[slug]][:3]
    for slug, t in rel:
        links.append((f'../articles/{slug}', t))
    if not links:
        return ''
    return '<div class="rel-box"><h2>この手法を深く知る（記事）</h2><ul>' + ''.join(f'<li><a href="{u}">{esc(t)}</a></li>' for u, t in links) + '</ul></div>'

# ---------- method pages ----------
compare_methods = set()
for m in data['methods']:
    mid = m['id']
    svcs = svc_by_method.get(mid, [])
    direct = [s for s in svcs if s.get('form') != '仲介・紹介' and s.get('form') != '比較メディア・送客']
    if len([s for s in direct if (s.get('fee_lo') or '').strip()]) >= 4:
        compare_methods.add(mid)
    rows = ''.join(
        f'<div class="svc"><div><b><a href="../services/{s["id"].lower()}.html">{esc(s["name"])}</a></b>（<a href="../companies/{s["entity_id"].lower()}.html">{esc(s["entity"])}</a>）<br>'
        f'手数料 {fee_text(s["fee_lo"], s["fee_hi"])}／入金 {esc(s["speed"]) or "―"}／金額 {amt_text(s["amt_lo"], s["amt_hi"])}<br>{svc_chips(s)}</div>{badge_score(s.get("score", ""))}</div>'
        for s in svcs)
    compare_link = f'<p><a href="../compare/{build.mslug(mid)}.html">{esc(m["name"])}のサービス比較（手数料・速さ・透明性）→</a></p>' if mid in compare_methods else ''
    body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ <a href="index.html">手法ガイド</a>（{esc(MID_GROUP.get(mid, ""))}） ／ {esc(m['name'])}</p>
<h1>{esc(m['name'])}とは</h1>
<p style="font-size:17px">{esc(m['def'])}</p>
<h2>仕組み</h2><p>{esc(m['how'])}</p>
<h2>対象と向く状態</h2>
<p><b>対象：</b>{esc(m['target'])}</p>
<p><b>向く状態：</b>{esc(m['fit'])}</p>
<p><b>向かない状態：</b>{esc(m['unfit'])}</p>
<h2>費用と期間</h2>
<p><b>費用の目安と決まり方：</b>{esc(m['cost'])}</p>
<p><b>入金までの期間：</b>{esc(m['period'])}</p>
<p><b>担保・保証：</b>{esc(m['collateral'])}</p>
<h2>必要書類</h2><p>{esc(m['docs'])}</p>
<h2>注意点</h2><p>{esc(m['legal'])}</p>
<p class="note">根拠：{esc(m['basis'])}（最終確認日 {esc(m['checked'])}）</p>
<h2>この手法のサービス（{len(svcs)}件）</h2>
{compare_link}
{rows if rows else '<p>現在、収録しているサービスはありません。</p>'}
{method_articles(mid, m['name'])}
{build.CTA_BOX}
<p><a href="../index.html#methods">手法ガイドの一覧へ戻る</a></p>
"""
    slug = f'methods/{build.mslug(mid)}.html'
    faq = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': f'{m["name"]}とは何ですか', 'acceptedAnswer': {'@type': 'Answer', 'text': m['def']}},
        {'@type': 'Question', 'name': f'{m["name"]}の費用はどれくらいですか', 'acceptedAnswer': {'@type': 'Answer', 'text': m['cost']}},
        {'@type': 'Question', 'name': f'{m["name"]}は入金までどれくらいかかりますか', 'acceptedAnswer': {'@type': 'Answer', 'text': m['period']}},
        {'@type': 'Question', 'name': f'{m["name"]}に必要な書類は何ですか', 'acceptedAnswer': {'@type': 'Answer', 'text': m['docs']}},
        {'@type': 'Question', 'name': f'{m["name"]}が向かないのはどんな場合ですか', 'acceptedAnswer': {'@type': 'Answer', 'text': m['unfit']}},
    ]}
    ld = json.dumps([faq, json.loads(crumbs(('トップ', ''), ('手法ガイド', 'index.html#methods'), (m['name'], slug)))], ensure_ascii=False)
    with open(f'{OUT}/{slug}', 'w') as f:
        f.write(build.page(f'{m["name"]}とは｜仕組み・費用・期間とサービス一覧', body, article=True, desc=m['def'][:120], ld=ld, path=slug))
    urls.append(slug)

# ---------- company pages ----------
for e0 in entities:
    e = prof(e0)
    cid = e['id']
    svcs = svc_by_entity.get(cid, [])
    m = methods.get(e['method'], {})
    basic = kv_table([
        ('運営会社', esc(e['name']) + (f'（{esc(e["alias"])}）' if e['alias'] else '')),
        ('所在地', val(e['location'])),
        ('代表者', val(e['rep'])),
        ('公式サイト', f'<a href="{esc(e["url"])}" rel="nofollow noopener" target="_blank">{esc(e["url"])}</a>' if e['url'] else '公表を確認できていません'),
        ('状態', esc(e['status']) + (f'（確認日 {esc(e["status_date"])}）' if e['status_date'] else '')),
        ('設立', val(e['founded'])),
        ('資本金', val(e['capital'])),
        ('登録・許認可', val(e['license'])),
        ('親会社・グループ', val(e['parent'])),
        ('主な手法', f'<a href="../methods/{build.mslug(e["method"])}.html">{esc(m.get("name", e["method"]))}</a>' if e['method'] else '―'),
        ('事業形態', val(e['form'], '未確認')),
        ('透明性スコア', f'{esc(e["score"]) if e["score"] else "―"} / 5（確認できた公表項目の数）'),
    ])
    summary = kv_table([
        ('手数料', fee_text(e['fee_lo'], e['fee_hi'])),
        ('入金スピード', val(e['speed'], '―')),
        ('金額', val(e['amount'], '―')),
        ('契約方式', val(e['contract'], '―')),
        ('対象', val(e['target'], '―')),
        ('必要書類', val(e['docs'], '―')),
        ('債権譲渡登記', val(e['registry'], '―')),
        ('償還請求権', val(e['recourse'], '―')),
        ('オンライン完結', val(e['online'], '―')),
    ])
    svc_rows = ''.join(
        f'<div class="svc"><div><b><a href="../services/{s["id"].lower()}.html">{esc(s["name"])}</a></b><br>'
        f'手数料 {fee_text(s["fee_lo"], s["fee_hi"])}／入金 {esc(s["speed"]) or "―"}／金額 {amt_text(s["amt_lo"], s["amt_hi"])}</div></div>'
        for s in svcs)
    import urllib.parse as _up
    gmap_q = _up.quote(e['name'] + (' ' + e['location'] if e['location'] else ''))
    if e['location']:
        coords = GEOCACHE.get(e['location'])
        if coords:
            lat, lon = coords
            bbox = f'{lon - 0.012},{lat - 0.006},{lon + 0.012},{lat + 0.006}'
            map_block = (f'<h2>所在地</h2><p>{esc(e["location"])}</p>'
                         f'<div class="mapwrap"><iframe title="{esc(e["name"])}の所在地の地図" loading="lazy" '
                         f'src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik&marker={lat},{lon}"></iframe></div>'
                         f'<p class="note">地図はOpenStreetMapの表示です。訪問前に公式サイトで所在地を確認してください。</p>')
        else:
            map_block = (f'<h2>所在地</h2><p>{esc(e["location"])}</p>'
                         f'<p><a href="https://www.google.com/maps/search/?api=1&query={gmap_q}" rel="nofollow noopener" target="_blank">Googleマップで所在地を見る</a></p>')
    else:
        map_block = ('<h2>所在地</h2><p>本社所在地の公表を、当サイトでは確認できていません。'
                     '所在地を確認したい場合は、公式サイトの会社概要をご覧ください。</p>')
    if e.get('_branches'):
        blis = ''.join(f'<li><b>{esc(b.get("name", ""))}</b>{esc(b.get("area", ""))}</li>' for b in e['_branches'])
        branch_block = f'<h2>支店・営業所</h2><ul class="pub">{blis}</ul><p class="note">公式サイトの公表に基づきます。</p>'
    else:
        branch_block = ('<h2>支店・営業所</h2><p>支店・営業所の公表を、当サイトでは確認できていません。'
                        '本社以外の拠点があるかどうかは、公式サイトでご確認ください。</p>')
    _svc_recourse = any((s.get('recourse') or '').strip() for s in svcs)
    _svc_results = [s for s in svcs if (s.get('results') or '').strip()]
    _pub_items = [
        ('費用の下限と上限', bool(e['fee_lo'] and e['fee_hi'])),
        ('金額の目安', bool(e['amount'])),
        ('償還請求権の扱い', _svc_recourse),
        ('実績', bool(_svc_results)),
        ('所在地と代表者', bool(e['location'] and e['rep'])),
    ]
    pub_block = '<ul class="pub">' + ''.join(
        f'<li><b>{"公表あり" if ok else "―"}</b>{esc(label)}{"" if ok else "（公表を確認できていません）"}</li>' for label, ok in _pub_items) + '</ul>'
    _rv = REVIEWS.get(e['id'])
    review_block = ''
    if _rv and _rv.get('count'):
        review_block = (f'<p>Googleマップの口コミ：★{_rv["rating"]}（{_rv["count"]}件）'
                        f'<span class="note">（{_rv.get("checked", "")}に集計）</span></p>')
    results_block = ''
    if _svc_results:
        rlis = ''.join(f'<li>{esc(s["name"])}：{esc(s["results"])}</li>' for s in _svc_results)
        results_block = f'<h3>実績（公式の公表値）</h3><ul>{rlis}</ul>'
    biz_block = (f'<h2>事業内容</h2><p>{esc(e["_business"])}</p>' if e.get('_business')
                 else '<h2>事業内容</h2><p>事業内容の詳しい公表は確認できていません。提供しているサービスは、このページの下の一覧のとおりです。</p>')
    body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ 運営会社 ／ {esc(e['name'])}</p>
<h1>{esc(e['name'])}</h1>
<p>{esc(e['name'])}の会社情報と、提供しているサービスの条件です。数値は各社の公式の公表と当サイトの観測に基づきます。公表されていない項目は推定で埋めず、その旨を書いています。</p>
{biz_block}
<h2>会社情報</h2>
{basic}
<h2>条件の要約（主な手法の集計）</h2>
<p class="note">この要約は、サービスごとの公表値を当サイトが集計したものです。個別のサービスの条件は下の一覧から確認してください。</p>
{summary}
{map_block}
{branch_block}
<h2>評判と、確認できること</h2>
<p>当サイトは口コミの投稿を受け付けていないため、利用者の声は掲載していません。評判を判断する材料として、公式が公表している事実と、当サイトが確認できた公表の状況をまとめます。</p>
{pub_block}
{results_block}
{review_block}
<p><a href="https://www.google.com/maps/search/?api=1&query={gmap_q}" rel="nofollow noopener" target="_blank">Googleマップでこの会社と口コミを見る</a></p>
<h2>提供しているサービス（{len(svcs)}件）</h2>
{svc_rows if svc_rows else '<p>現在、収録しているサービスはありません。</p>'}
<p class="note">最終観測日：{esc(e['observed']) or '―'}</p>
{build.CTA_BOX}
"""
    slug = f'companies/{cid.lower()}.html'
    org = {'@context': 'https://schema.org', '@type': 'Organization', 'name': e['name']}
    if e['url']:
        org['url'] = e['url']
    if e['location']:
        org['address'] = e['location']
    if e['founded'] and re.match(r'^\d{4}', e['founded']):
        org['foundingDate'] = e['founded'][:4]
    if e['url']:
        org['sameAs'] = [e['url']]
    ld = json.dumps([org, json.loads(crumbs(('トップ', ''), (e['name'], slug)))], ensure_ascii=False)
    desc = f'{e["name"]}の会社情報と、提供しているサービスの条件です。手数料、入金スピード、金額を、公式の公表と当サイトの観測に基づいて掲載しています。'
    with open(f'{OUT}/{slug}', 'w') as f:
        f.write(build.page(f'{e["name"]}｜会社情報とサービスの条件', body, article=True, desc=desc, ld=ld, path=slug))
    urls.append(slug)

# ---------- service pages ----------
for s in services:
    sid = s['id']
    e = ent_by_id.get(s['entity_id'], {})
    m = methods.get(s['method'], {})
    rows = kv_table([
        ('運営会社', f'<a href="../companies/{s["entity_id"].lower()}.html">{esc(s["entity"])}</a>'),
        ('手法', f'<a href="../methods/{build.mslug(s["method"])}.html">{esc(m.get("name", s["method"]))}</a>'),
        ('事業形態', val(s['form'], '未確認')),
        ('手数料', fee_text(s['fee_lo'], s['fee_hi']) + (f'（{esc(s["fee_type"])}）' if s['fee_type'] else '')),
        ('入金スピード', val(s['speed'], '―')),
        ('金額', amt_text(s['amt_lo'], s['amt_hi'])),
        ('契約方式', val(s['contract'], '―')),
        ('対象', val(s['target'], '―')),
        ('対象業種', val(s['industries'], '―')),
        ('必要書類', val(s['docs'], '―')),
        ('債権譲渡登記', val(s['registry'], '―')),
        ('償還請求権', val(s['recourse'], '―')),
        ('オンライン完結', val(s['online'], '―')),
        ('審査の目安', val(s['review'], '―')),
        ('実績（公表値）', val(s['results'], '―')),
        ('状態', val(s['status'], '―')),
        ('最終確認日', val(s['checked'], '―')),
        ('透明性スコア', f'{esc(s.get("score", "")) or "―"} / 5（運営会社）'),
    ])
    if s['features']:
        features = f'<h2>特徴</h2><p>{esc(s["features"])}</p>'
    else:
        _auto = (f'{esc(s["entity"])}が提供する{esc(m.get("name", ""))}のサービスです。'
                 f'費用は{fee_text(s["fee_lo"], s["fee_hi"])}、入金スピードは{esc(s["speed"]) or "公表を確認できていません"}、'
                 f'金額は{amt_text(s["amt_lo"], s["amt_hi"])}です。対象は{esc(s["target"]) or "公表を確認できていません"}。'
                 f'詳しい条件は下の表のとおりで、最終確認日を付けています。')
        features = f'<h2>特徴</h2><p>{_auto}</p>'
    source = f'<p class="note">出典：<a href="{esc(s["source"])}" rel="nofollow noopener" target="_blank">{esc(s["source"])}</a></p>' if s['source'] else ''
    _aff = AFF.get(s['id'])
    if _aff and _aff.get('url'):
        official = f'<p><a class="btn btn-sub btn-sm" href="{esc(_aff["url"])}" rel="sponsored nofollow noopener" target="_blank">公式サイトをチェック</a></p>'
    elif s['url']:
        official = f'<p><a class="btn btn-sub btn-sm" href="{esc(s["url"])}" rel="nofollow noopener" target="_blank">公式サイトを見る</a></p>'
    else:
        official = ''
    pr = PR_NOTICE if (_aff and _aff.get('url')) else ''
    _ee = prof(e) if e else {}
    ent_block = ''
    if _ee:
        ent_rows = kv_table([
            ('所在地', val(_ee.get('location', ''))),
            ('代表者', val(_ee.get('rep', ''))),
            ('設立', val(_ee.get('founded', ''))),
            ('資本金', val(_ee.get('capital', ''))),
            ('透明性スコア', f'{esc(_ee.get("score", "")) or "―"} / 5（確認できた公表項目の数）'),
        ])
        ent_block = (f'<h2>運営会社について</h2>{ent_rows}'
                     f'<p><a href="../companies/{s["entity_id"].lower()}.html">{esc(s["entity"])}の会社情報と評判</a></p>')
    _rel = [x for x in services if x['method'] == s['method'] and x['id'] != sid and (x.get('fee_lo') or '').strip()][:6]
    if not _rel:
        _rel = [x for x in services if x['method'] == s['method'] and x['id'] != sid][:6]
    if not _rel:
        _grp_mids = [mid for mid, g in MID_GROUP.items() if g == MID_GROUP.get(s['method'])]
        _rel = [x for x in services if x['method'] in _grp_mids and x['id'] != sid][:6]
    _same_ent = [x for x in services if x['entity_id'] == s['entity_id'] and x['id'] != sid][:4]
    rel_svcs = ''
    if _rel or _same_ent:
        parts = ''
        if _same_ent:
            parts += '<p><b>同じ会社のサービス</b></p><ul>' + ''.join(f'<li><a href="{x["id"].lower()}.html">{esc(x["name"])}</a></li>' for x in _same_ent) + '</ul>'
        if _rel:
            parts += '<p><b>同じ手法のサービス</b></p><ul>' + ''.join(f'<li><a href="{x["id"].lower()}.html">{esc(x["name"])}</a>（{esc(x["entity"])}）</li>' for x in _rel) + '</ul>'
        rel_svcs = f'<h2>関連するサービス</h2>{parts}'
    body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ サービス ／ {esc(s['name'])}</p>
<h1>{esc(s['name'])}</h1>
<p>{esc(s['entity'])}が提供する{esc(m.get('name', ''))}のサービスです。条件は公式の公表に基づき、確認日を付けています。</p>
{pr}
<h2>条件</h2>
{rows}
{features}
{ent_block}
{rel_svcs}
{official}
{source}
{build.CTA_BOX}
"""
    slug = f'services/{sid.lower()}.html'
    svc_ld = {'@context': 'https://schema.org', '@type': 'Service', 'name': s['name'],
              'serviceType': m.get('name', ''), 'provider': {'@type': 'Organization', 'name': s['entity'], 'url': build.BASE_URL + f'companies/{s["entity_id"].lower()}.html'}}
    if s['features']:
        svc_ld['description'] = s['features'][:200]
    ld = json.dumps([svc_ld, json.loads(crumbs(('トップ', ''), (s['name'], slug)))], ensure_ascii=False)
    desc = f'{s["name"]}（{s["entity"]}）の条件です。手数料 {fee_text(s["fee_lo"], s["fee_hi"])}、入金スピード、金額、必要書類を公式の公表に基づいて掲載しています。'
    with open(f'{OUT}/{slug}', 'w') as f:
        f.write(build.page(f'{s["name"]}｜手数料・入金スピード・金額の条件', body, article=True, desc=desc, ld=ld, path=slug))
    urls.append(slug)

# ---------- compare pages ----------
for mid in sorted(compare_methods):
    m = methods[mid]
    svcs = svc_by_method.get(mid, [])
    direct = sorted([s for s in svcs if s.get('form') not in ('仲介・紹介', '比較メディア・送客')], key=fee_num)
    inter = [s for s in svcs if s.get('form') in ('仲介・紹介', '比較メディア・送客')]
    trs = ''.join(
        f'<tr><td><b><a href="../services/{s["id"].lower()}.html">{esc(s["name"])}</a></b></td>'
        f'<td><a href="../companies/{s["entity_id"].lower()}.html">{esc(s["entity"])}</a></td>'
        f'<td>{fee_text(s["fee_lo"], s["fee_hi"])}</td><td>{esc(s["speed"]) or "―"}</td>'
        f'<td>{amt_text(s["amt_lo"], s["amt_hi"])}</td><td>{esc(s["form"]) or "未確認"}</td>'
        f'<td>{badge_score(s.get("score", ""))}</td></tr>'
        for s in direct)
    inter_rows = ''.join(
        f'<div class="svc"><div><b><a href="../services/{s["id"].lower()}.html">{esc(s["name"])}</a></b>（{esc(s["entity"])}）<br>形態：{esc(s["form"])}。自社で買取や貸付を行う事業者ではないため、条件の数字では並べていません。</div></div>'
        for s in inter)
    _cb = ''
    for _s in direct:
        _a = AFF.get(_s['id'])
        if _a and _a.get('banner'):
            _cb = f'<div class="aff-banner">{_a["banner"]}</div>'
            break
    _cpr = PR_NOTICE if _cb else ''
    body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ <a href="../methods/{build.mslug(mid)}.html">{esc(m['name'])}</a> ／ サービス比較</p>
<h1>{esc(m['name'])}のサービス比較</h1>
{_cpr}
<p>並びは、手数料の下限が小さい順という機械的な並びです。順位ではありません。比べた項目は手数料、入金スピード、金額、事業形態、透明性スコアです。手数料の上限が「非公表」の会社は、見積もりで幅の確認が必要です。数字は各社の公式の公表に基づき、確認日は各サービスのページに付けています。透明性スコアは確認できた公表項目の数で、定義は<a href="../about.html">運営者情報</a>に書いています。</p>
<div class="tblwrap"><table class="wide"><tr><th>サービス</th><th>運営会社</th><th>手数料</th><th>入金スピード</th><th>金額</th><th>事業形態</th><th>透明性</th></tr>{trs}</table></div>
{_cb}
{f'<h2>仲介・紹介のサービス（{len(inter)}件）</h2>' + inter_rows if inter else ''}
{build.CTA_BOX}
"""
    slug = f'compare/{build.mslug(mid)}.html'
    itemlist = {'@context': 'https://schema.org', '@type': 'ItemList',
                'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': s['name'], 'url': build.BASE_URL + f'services/{s["id"].lower()}.html'} for i, s in enumerate(direct)]}
    ld = json.dumps([itemlist, json.loads(crumbs(('トップ', ''), (m['name'], f'methods/{build.mslug(mid)}.html'), ('サービス比較', slug)))], ensure_ascii=False)
    desc = f'{m["name"]}のサービスを、手数料、入金スピード、金額、透明性スコアで比べる比較ページです。並びは手数料の下限が小さい順で、順位ではありません。'
    with open(f'{OUT}/{slug}', 'w') as f:
        f.write(build.page(f'{m["name"]}のサービス比較｜手数料・速さ・透明性', body, article=True, desc=desc, ld=ld, path=slug))
    urls.append(slug)


# ---------- index pages (articles / methods) ----------
def _trunc(t, n):
    return t if len(t) <= n else t[:n] + '…'

def _fcard(url, title, desc):
    d = f'<span>{esc(desc)}</span>' if desc else ''
    return f'<a class="fcard" href="{url}"><b>{esc(title)}</b>{d}</a>'

_basics = ''.join(_fcard(f'{b}', build.ART_TITLES[b], _trunc(build.ART_DESCS.get(b, ''), 58)) for b in build.BASICS_SLUGS)
_guides = ''.join(_fcard(f'{g}', build.ART_TITLES[g], _trunc(build.ART_DESCS.get(g, ''), 58)) for g in build.PILLAR_SLUGS)
_abody = f"""
<p class="note"><a href="../index.html">トップ</a> ／ 記事一覧</p>
<h1>記事一覧</h1>
<p>仕組みを先に知るための基礎知識と、いまの状況に近い進め方を書いた状態別の記事をまとめています。</p>
<h2 id="basics">基礎知識（仕組みの根幹）</h2>
<div class="fgrid">{_basics}</div>
<h2 id="guides">状態別の進め方</h2>
<div class="fgrid">{_guides}</div>
{build.CTA_BOX}
"""
with open(f'{OUT}/articles/index.html', 'w') as f:
    _art_items = [{'@type': 'ListItem', 'position': i + 1, 'name': build.ART_TITLES[s], 'url': build.BASE_URL + f'articles/{s}'} for i, s in enumerate(build.BASICS_SLUGS + build.PILLAR_SLUGS)]
    _art_ld = json.dumps([{'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': _art_items},
                          json.loads(crumbs(('トップ', ''), ('記事一覧', 'articles/index.html')))], ensure_ascii=False)
    f.write(build.page('記事一覧｜基礎知識と状態別の進め方', _abody, article=True, desc='基礎知識と状態別の進め方の記事一覧。仕組みの根幹から、いまの状況に近い記事まで。', ld=_art_ld, path='articles/index.html'))
if 'articles/index.html' not in urls:
    urls.append('articles/index.html')

GROUP_DESCS = {
    '借りる（公的・銀行系）': '費用が低い代わりに、決算と審査の確認が中心になります。状態チェックでは、この系統から先に確認します。',
    '借りる（民間の融資）': '銀行系で合わない場合の受け皿です。担保があるかどうかで分かれます。',
    '売掛金を現金化する': '決算ではなく、売掛先と請求書の状態で決まる系統です。入金までの速さが要ります。',
    '公的な支援': '返す必要のないお金と、借入の負担を下げる仕組みです。期限と要件の確認が先に要ります。',
    'その他の調達': '出資や債券など、上記に入らない形です。',
}
_mgroups = ''
for _gname, _gmids in METHOD_GROUPS:
    _gdesc = GROUP_DESCS[_gname]
    _cards = ''
    for _mid in _gmids:
        m = methods[_mid]
        cnt = len(svc_by_method.get(_mid, []))
        comp = f'／<a href="../compare/{build.mslug(_mid)}.html">比較</a>' if _mid in compare_methods else ''
        _cards += (f'<div class="fcard"><b><a href="{build.mslug(_mid)}.html">{esc(m["name"])}</a></b>'
                   f'<span>{esc(_trunc(m["def"], 58))}</span><span>収録サービス {cnt}件{comp}</span></div>')
    _mgroups += f'<h2>{esc(_gname)}</h2><p>{esc(_gdesc)}</p><div class="fgrid">{_cards}</div>'
_mbody = f"""
<p class="note"><a href="../index.html">トップ</a> ／ 手法ガイド</p>
<h1>手法ガイド（全24手法）</h1>
<p>資金調達の手法を、性質で5つに分けて並べています。借りる、売掛金を現金化する、公的な支援、その他の調達。各手法の仕組み、費用、期間、向く状態を書いています。</p>
{_mgroups}
{build.CTA_BOX}
"""
with open(f'{OUT}/methods/index.html', 'w') as f:
    _m_items = [{'@type': 'ListItem', 'position': i + 1, 'name': methods[mid]['name'], 'url': build.BASE_URL + f'methods/{build.mslug(mid)}.html'} for i, mid in enumerate(sorted(methods))]
    _m_ld = json.dumps([{'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': _m_items},
                        json.loads(crumbs(('トップ', ''), ('手法ガイド', 'methods/index.html')))], ensure_ascii=False)
    f.write(build.page('手法ガイド（全24手法）｜仕組み・費用・期間の一覧', _mbody, article=True, desc='資金調達の全24手法の一覧。各手法の仕組み、費用、期間と収録サービス件数。', ld=_m_ld, path='methods/index.html'))
if 'observation.html' not in urls:
    urls.append('observation.html')
if 'methods/index.html' not in urls:
    urls.append('methods/index.html')

# ---------- sitemap ----------
BASE_URL = 'https://kensetusikinnavi.net/'
urls += ['', 'about.html', 'privacy.html']
BUILD_DATE = '2026-11-23'
def _lm(u):
    if u.startswith('companies/'):
        e = ent_by_id.get(u.split('/')[1].split('.')[0].upper(), {})
        v = (e.get('observed') or '').strip()
        return v if re.match(r'^\d{4}-\d{2}-\d{2}$', v) else BUILD_DATE
    if u.startswith('services/'):
        sv = svc_by_id.get(u.split('/')[1].split('.')[0].upper(), {})
        v = (sv.get('checked') or '').strip()
        return v if re.match(r'^\d{4}-\d{2}-\d{2}$', v) else BUILD_DATE
    return BUILD_DATE
items = ''.join(f'<url><loc>{BASE_URL}{u}</loc><lastmod>{_lm(u)}</lastmod></url>' for u in urls)
with open(f'{OUT}/sitemap.xml', 'w') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + items + '</urlset>')
print('pages: methods', len(data['methods']), '/ companies', len(entities), '/ services', len(services), '/ compare', len(compare_methods), '/ total urls', len(urls))

# ---------- _redirects / robots (公開切り替え用) ----------
import csv as _csv
_map_path = os.path.join(build.BASE, 'files', 'リダイレクト対応表_切替用_20261117.csv')
if os.path.exists(_map_path):
    lines = []
    with open(_map_path, encoding='utf-8-sig') as f:
        for r in _csv.DictReader(f):
            lines.append(f"{r['旧URLパス']} {r['リダイレクト先']} {r['ステータス']}")
    for _mid in sorted(build.MSLUG):
        lines.append(f'/methods/{_mid.lower()}.html /methods/{urllib.parse.quote(build.MSLUG[_mid])}.html 301')
        lines.append(f'/compare/{_mid.lower()}.html /compare/{urllib.parse.quote(build.MSLUG[_mid])}.html 301')
    lines.append('/articles/company-beatreding.html /companies/c002.html 301')
    lines.append('/articles/service-ququmo.html /services/s094.html 301')
    lines.append(f'/articles/compare-2sha.html /compare/{urllib.parse.quote(build.MSLUG["M13"])}.html 301')
    with open(f'{OUT}/_redirects', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('redirects:', len(lines))
with open(f'{OUT}/robots.txt', 'w') as f:
    f.write('User-agent: *\nAllow: /\nSitemap: https://kensetusikinnavi.net/sitemap.xml\n')
