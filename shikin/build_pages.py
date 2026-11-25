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

# ---------- 視覚化（公表レーダー／条件バンド） ----------
import math as _math
import statistics as _stats

def _dep2(lo, hi):
    if lo and hi:
        return 2
    if lo or hi:
        return 1
    return 0

def _dep1(v):
    return 2 if (v or '').strip() else 0

def _svc_axes(s):
    return [('費用', _dep2(s.get('fee_lo'), s.get('fee_hi'))),
            ('金額', _dep2(s.get('amt_lo'), s.get('amt_hi'))),
            ('入金スピード', _dep1(s.get('speed'))),
            ('契約の条件', 2 if ((s.get('recourse') or '').strip() or (s.get('registry') or '').strip()) else 0),
            ('実績', _dep1(s.get('results')))]

def _radar_svg(axes, score, size=264):
    cx = cy = size / 2
    R = size / 2 - 46
    def _pt(i, v):
        ang = -_math.pi / 2 + i * 2 * _math.pi / 5
        r = R * v / 2
        return (cx + r * _math.cos(ang), cy + r * _math.sin(ang))
    rings = ''
    for lv in (1, 2):
        rp = []
        for i in range(5):
            ang = -_math.pi / 2 + i * 2 * _math.pi / 5
            r = R * lv / 2
            rp.append(f'{cx + r * _math.cos(ang):.1f},{cy + r * _math.sin(ang):.1f}')
        rings += f'<polygon points="{" ".join(rp)}" fill="none" stroke="#E0ECE8" stroke-width="1"/>'
    spokes, labels = '', ''
    for i, (label, v) in enumerate(axes):
        ang = -_math.pi / 2 + i * 2 * _math.pi / 5
        x2, y2 = cx + R * _math.cos(ang), cy + R * _math.sin(ang)
        spokes += f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#E0ECE8"/>'
        lx, ly = cx + (R + 22) * _math.cos(ang), cy + (R + 18) * _math.sin(ang)
        anchor = 'middle'
        if _math.cos(ang) > 0.3:
            anchor = 'start'
        elif _math.cos(ang) < -0.3:
            anchor = 'end'
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="11.5" font-weight="700" fill="#182420">{label}<tspan fill="#0F7A68"> {v}/2</tspan></text>'
    pts = [_pt(i, v) for i, (label, v) in enumerate(axes)]
    poly = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#14957F"/>' for x, y in pts)
    return (f'<svg viewBox="0 0 {size} {size}" width="100%" role="img" aria-label="公表レーダーチャート">'
            f'{rings}{spokes}<polygon points="{poly}" fill="rgba(20,149,127,.18)" stroke="#14957F" stroke-width="2"/>'
            f'{dots}{labels}'
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="10.5" fill="#5C6B66">透明性スコア</text>'
            f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="22" font-weight="700" fill="#0F7A68" font-family="Jost">{score}<tspan font-size="12" fill="#5C6B66">/5</tspan></text></svg>')

_DEP_TXT = {2: '下限と上限まで公表', 1: '一部を公表', 0: '公表を確認できていません'}

def _radar_block(axes, score, heading_note):
    arows = ''.join(f'<tr><td>{html.escape(lab)}</td><td>{v}／2（{_DEP_TXT[v]}）</td></tr>' for lab, v in axes)
    return (f'<h2>公表の充実度（レーダー）</h2>'
            f'<p>{heading_note}評価ではなく、公式がどこまで数字を出しているかを数えたものです。公表が薄い項目は、申し込みの前に書面で確認してください。</p>'
            f'<div class="viz"><div class="viz-svg">{_radar_svg(axes, score)}</div>'
            f'<div class="viz-tbl"><table><tr><th>項目</th><th>公表の深さ</th></tr>{arows}</table></div></div>')

def _pctnum(v):
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)', v or '')
    return float(m.group(1)) if m else None

_fee_dist = {}
for _s in services:
    if _s.get('status') in ('廃業・撤退', '重複'):
        continue
    _h = _pctnum(_s.get('fee_hi'))
    if _h is not None and '%' in (_s.get('fee_hi') or ''):
        _fee_dist.setdefault(_s['method'], []).append(_h)
for _k in _fee_dist:
    _fee_dist[_k] = sorted(_fee_dist[_k])

def _fee_band(s):
    dist = _fee_dist.get(s['method'], [])
    flo, fhi = _pctnum(s.get('fee_lo')), _pctnum(s.get('fee_hi'))
    if len(dist) < 5 or flo is None or fhi is None or '%' not in (s.get('fee_hi') or ''):
        return ''
    med = _stats.median(dist)
    lo_all, hi_all = dist[0], dist[-1]
    W = 560
    scale = hi_all * 1.05 or 1
    def X(v):
        return 8 + (W - 16) * v / scale
    ftype = s.get('fee_type') or '費用'
    mname = methods.get(s['method'], {}).get('name', '')
    return (f'<h3>{ftype}の位置（同じ手法の中での幅）</h3>'
            f'<div class="band-wrap"><svg viewBox="0 0 {W} 92" width="100%" role="img" aria-label="{ftype}バンド">'
            f'<rect x="{X(lo_all):.0f}" y="30" width="{max(X(hi_all) - X(lo_all), 4):.0f}" height="16" rx="8" fill="#E9F5F1"/>'
            f'<line x1="{X(med):.0f}" y1="22" x2="{X(med):.0f}" y2="54" stroke="#D97706" stroke-width="2.5"/>'
            f'<text x="{X(med):.0f}" y="14" text-anchor="middle" font-size="12" font-weight="700" fill="#B45309">上限の中央値 {med:g}%</text>'
            f'<rect x="{X(flo):.0f}" y="30" width="{max(X(fhi) - X(flo), 6):.0f}" height="16" rx="8" fill="#14957F"/>'
            f'<text x="{X(flo):.0f}" y="66" font-size="12.5" font-weight="700" fill="#182420">このサービス：{ftype} {html.escape(s.get("fee_lo") or "")}〜{html.escape(s.get("fee_hi") or "")}</text>'
            f'<text x="{X(hi_all):.0f}" y="66" text-anchor="end" font-size="11.5" fill="#5C6B66">{mname}の上限の分布 {lo_all:g}%〜{hi_all:g}%（公表 {len(dist)}件）</text></svg></div>'
            f'<p class="note">帯は、同じ手法の収録サービスのうち上限を公表しているものの幅です。位置は条件の良し悪しではなく、公表値の分布の中での位置です。</p>')


def _log_block(names):
    rows = [x for x in data.get('log', []) if x.get('entity') in names]
    if not rows:
        return ''
    trs = ''.join(
        f"<tr><td>{esc(x['date'])}</td><td>{esc(x['item'])}</td><td>{esc(((x['before'] + ' → ') if x.get('before') else '') + x['after'])}</td></tr>"
        for x in rows)
    return (f'<h2>確認の記録</h2><p>当サイトが公式ページを確認した記録です。'
            f'条件が変われば、ここに日付つきで残ります。</p>'
            f'<div class="tblwrap"><table><tr><th>確認日</th><th>項目</th><th>内容</th></tr>{trs}</table></div>')

def _svc_reading(s):
    if s.get('status') in ('廃業・撤退', '重複'):
        return ''
    parts = []
    mn = methods.get(s['method'], {}).get('name', '')
    pool = [x for x in services if x['method'] == s['method'] and x.get('status') not in ('廃業・撤退', '重複')]
    def _depth(x):
        return sum(v for _, v in _svc_axes(x))
    if len(pool) >= 5:
        d0 = _depth(s)
        rank = 1 + sum(1 for x in pool if _depth(x) > d0)
        parts.append(f'公表の充実度は、同じ「{esc(mn)}」の収録{len(pool)}件の中で{rank}番目の水準です')
    dist = _fee_dist.get(s['method'], [])
    fv = _pctnum(s.get('fee_hi'))
    if len(dist) >= 5 and fv is not None and '%' in (s.get('fee_hi') or ''):
        med = _stats.median(dist)
        rank = 1 + sum(1 for v in dist if v < fv)
        parts.append(f'手数料の上限（{fv:g}%）は、上限を公表している{len(dist)}件の中で低い方から{rank}番目にあり、中央値は{med:g}%です')
    if not parts:
        return ''
    return '<p>' + '。'.join(parts) + '。いずれも当サイトの収録データからの算出で、公式の公表値に基づきます。</p>'

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
        f'<div class="svc"><div><b><a href="../services/{s["id"].lower()}.html">{esc(s["name"])}</a></b>{"（終了）" if s.get("status") == "廃業・撤退" else "（統合済み）" if s.get("status") == "重複" else ""}（<a href="../companies/{s["entity_id"].lower()}.html">{esc(s["entity"])}</a>）<br>'
        f'手数料 {fee_text(s["fee_lo"], s["fee_hi"])}／入金 {esc(s["speed"]) or "―"}／金額 {amt_text(s["amt_lo"], s["amt_hi"])}<br>{svc_chips(s)}</div>{badge_score(s.get("score", ""))}</div>'
        for s in svcs)
    compare_link = f'<p><a href="../compare/{build.mslug(mid)}.html">{esc(m["name"])}のサービス比較（手数料・速さ・透明性）→</a></p>' if mid in compare_methods else ''
    agg = ''
    if len(svcs) >= 5:
        _n = len(svcs)
        def _pct(x):
            return f'{x * 100 // _n}%'
        _fb = sum(1 for s in svcs if s['fee_lo'] and s['fee_hi'])
        _ab = sum(1 for s in svcs if s['amt_lo'] and s['amt_hi'])
        _sp = sum(1 for s in svcs if s['speed'])
        _on = sum(1 for s in svcs if s['online'])
        _arows = [('手数料の下限と上限の両方を公表', f'{_fb}件（{_pct(_fb)}）'),
                  ('金額の下限と上限の両方を公表', f'{_ab}件（{_pct(_ab)}）'),
                  ('入金スピードを公表', f'{_sp}件（{_pct(_sp)}）')]
        if mid in ('M13', 'M14', 'M15', 'M16', 'M17'):
            _rc = sum(1 for s in svcs if s['recourse'])
            _arows.append(('償還請求権の有無を公表', f'{_rc}件（{_pct(_rc)}）'))
        _arows.append(('オンラインで完結するかを公表', f'{_on}件（{_pct(_on)}）'))
        agg = (f'<h2>収録サービスから見える公表の状況</h2>'
               f'<p>当サイトが収録しているこの手法のサービス{_n}件について、公式の公表の状況を数えました（2026年11月24日時点）。</p>'
               + kv_table(_arows)
               + '<p class="note">公表の有無は、条件の良し悪しとは関係ありません。公表されていない項目は、申し込みの前に書面で確認してください。</p>')
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
{agg}
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
    _ent_radar = ''
    if svcs:
        _labels = ['費用', '金額', '入金スピード', '契約の条件', '実績']
        _agg = []
        for _i, _lab in enumerate(_labels):
            _agg.append((_lab, max(_svc_axes(_s)[_i][1] for _s in svcs)))
        _ent_radar = _radar_block(_agg, esc(e['score']) if e['score'] else '―',
                                  'この会社が提供するサービスのうち、最も公表が厚いものの深さです。')
    _facts = []
    if e['location']:
        _facts.append(f"所在地は{e['location']}です")
    if e['founded']:
        _facts.append(f"設立は{e['founded']}です")
    if e['capital']:
        _facts.append(f"資本金は{e['capital']}です")
    if e['rep']:
        _facts.append(f"代表者は{e['rep']}です")
    _mnames = []
    for _s in svcs:
        _mn2 = methods.get(_s['method'], {}).get('name', '')
        if _mn2 and _mn2 not in _mnames:
            _mnames.append(_mn2)
    _dtxt = '。'.join(esc(x) for x in _facts)
    if _mnames:
        _dtxt += ('。' if _dtxt else '') + f"提供しているのは{'、'.join(esc(x) for x in _mnames)}のサービス{len(svcs)}件です"
    if _rv and _rv.get('count'):
        _dtxt += f"。Googleマップの口コミは{_rv['count']}件、評価は★{_rv['rating']}です（{_rv.get('checked', '')}集計）"
    digest = f'<p>{_dtxt}。</p>' if _dtxt else ''
    _ent_log = _log_block({e['name']} | {x['name'] for x in svcs})
    biz_block = (f'<h2>事業内容</h2><p>{esc(e["_business"])}</p>' if e.get('_business')
                 else '<h2>事業内容</h2><p>事業内容の詳しい公表は確認できていません。提供しているサービスは、このページの下の一覧のとおりです。</p>')
    body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ <a href="index.html">運営会社</a> ／ {esc(e['name'])}</p>
<h1>{esc(e['name'])}</h1>
<p>{esc(e['name'])}の会社情報と、提供しているサービスの条件です。数値は各社の公式の公表と当サイトの観測に基づきます。公表されていない項目は推定で埋めず、その旨を書いています。</p>
{digest}
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
{_ent_radar}
<p><a href="https://www.google.com/maps/search/?api=1&query={gmap_q}" rel="nofollow noopener" target="_blank">Googleマップでこの会社と口コミを見る</a></p>
{_ent_log}
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

# ---------- companies index ----------
PREFS = ['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県', '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県', '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']

def _pref_of(loc):
    best, bestpos = '', 10 ** 9
    for p in PREFS:
        i = (loc or '').find(p)
        if i >= 0 and i < bestpos:
            best, bestpos = p, i
    return best

_by_pref = {}
_unknown_loc = []
_ended_ents = []
for _e0 in entities:
    _e = prof(_e0)
    if _e['status'] == '廃業・撤退':
        _ended_ents.append(_e)
        continue
    _p = _pref_of(_e.get('location', ''))
    if _p:
        _by_pref.setdefault(_p, []).append(_e)
    else:
        _unknown_loc.append(_e)

def _ent_li(_e):
    _mn = methods.get(_e['method'], {}).get('name', '')
    _sc = f'／透明性スコア {esc(_e.get("score", ""))} / 5' if _e.get('score') else ''
    return f'<li><a href="{_e["id"].lower()}.html">{esc(_e["name"])}</a>（{_mn}{_sc}）</li>'

def _short_loc(loc, pref):
    rest = loc or ''
    if pref and rest.startswith(pref):
        rest = rest[len(pref):]
    m = re.search(r'^.*?[市区町村]', rest)
    if m and len(m.group(0)) <= 12:
        return pref + m.group(0)
    return (loc or '')[:16]

def _score_dots(score):
    if score in ('', None) or not str(score).isdigit():
        return ''
    n = int(score)
    return (f'<span class="sd"><span class="sd-on">{"●" * n}</span><span class="sd-off">{"●" * (5 - n)}</span></span>'
            f'<span class="ent-score">透明性 {n}/5</span>')

def _ent_card(_e):
    _mn = methods.get(_e['method'], {}).get('name', '')
    _p = _pref_of(_e.get('location', ''))
    _bits = []
    if _e.get('location'):
        _bits.append(esc(_short_loc(_e['location'], _p)))
    _nsvc = len(svc_by_entity.get(_e['id'], []))
    if _nsvc:
        _bits.append(f'サービス{_nsvc}件')
    _rv = REVIEWS.get(_e['id'])
    _rvh = f'<div class="ent-sub">Google口コミ ★{_rv["rating"]}（{_rv["count"]}件）</div>' if _rv and _rv.get('count') else ''
    return (f'<div class="ent-card"><a class="ent-name" href="{_e["id"].lower()}.html">{esc(_e["name"])}</a>'
            f'<div class="ent-meta"><span class="ent-chip">{esc(_mn)}</span>{_score_dots(_e.get("score", ""))}</div>'
            f'<div class="ent-sub">{"／".join(_bits)}</div>{_rvh}</div>')

_pref_toc = ''.join(f'<a href="#pref-{i}">{p}（{len(_by_pref[p])}）</a>' for i, p in enumerate(PREFS) if p in _by_pref)
_pref_secs = ''.join(
    f'<h2 class="sec" id="pref-{i}">{p}<span class="cnt">{len(_by_pref[p])}社</span></h2><div class="ent-grid">'
    + ''.join(_ent_card(_e) for _e in sorted(_by_pref[p], key=lambda x: x['name'])) + '</div>'
    for i, p in enumerate(PREFS) if p in _by_pref)
_ended_li = ''.join(f'<li><a href="{_e["id"].lower()}.html">{esc(_e["name"])}</a>（{_e["status"]}、確認日 {esc(_e["status_date"])}）</li>' for _e in _ended_ents)
_unknown_li = ''.join(_ent_li(_e) for _e in sorted(_unknown_loc, key=lambda x: x['name']))
_all_li = ''.join(_ent_li(_e) for _e in sorted(entities, key=lambda x: x['name']))
_idx_body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ 運営会社</p>
<h1>運営会社の一覧</h1>
<p>当サイトが収録している運営会社{len(entities)}社の一覧です。都道府県別と、全社の一覧（会社名順）で引けます。各カードには、主な手法、透明性スコア（確認できた公表項目の数）、所在地、サービスの件数と、集計できた会社にはGoogleマップの口コミの評価と件数を表示しています。サービスを終了した会社は、分けて表示しています。</p>
<h2 class="sec">都道府県から探す</h2>
<div class="pref-nav">{_pref_toc}</div>
{_pref_secs}
<h2 class="sec">サービスを終了した会社</h2>
<ul>{_ended_li}</ul>
<h2 class="sec">所在地を確認できていない会社</h2>
<ul>{_unknown_li}</ul>
<h2 class="sec">全社の一覧（会社名順）</h2>
<ul class="all-list">{_all_li}</ul>
{build.CTA_BOX}
"""
with open(f'{OUT}/companies/index.html', 'w') as f:
    f.write(build.page('運営会社の一覧', _idx_body, desc='資金調達サービスの運営会社の一覧。都道府県別と会社名順で引けます。終了した会社も分けて表示しています。', path='companies/index.html', sub=True))
urls.append('companies/index.html')

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
    ended = s.get('status') == '廃業・撤退'
    if ended:
        official = ''
        pr = ''
    ended_banner = '<div class="panel" style="border-left:4px solid #D9480F;margin:14px 0"><b>このサービスは終了しています</b><p style="margin:6px 0 0">当サイトが確認した時点で、このサービスは終了・撤退しています。申し込みはできません。記録として掲載を残しています。</p></div>' if ended else ''
    dup = s.get('status') == '重複'
    _twin = next((x for x in services if x['id'] != sid and x['name'] == s['name'] and x['entity_id'] == s['entity_id'] and x.get('status') != '重複'), None) if dup else None
    if dup:
        official = ''
        pr = ''
    dup_banner = f'<div class="panel" style="border-left:4px solid #D9480F;margin:14px 0"><b>このページは統合しました</b><p style="margin:6px 0 0">このサービスは<a href="{_twin["id"].lower()}.html">{esc(s["name"])}（{esc(s["entity"])}）</a>と同一のため、そちらに統合しました。</p></div>' if _twin else ''
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
    _rel = [x for x in services if x['method'] == s['method'] and x['id'] != sid and x.get('status') not in ('廃業・撤退', '重複') and (x.get('fee_lo') or '').strip()][:6]
    if not _rel:
        _rel = [x for x in services if x['method'] == s['method'] and x['id'] != sid and x.get('status') not in ('廃業・撤退', '重複')][:6]
    if not _rel:
        _grp_mids = [mid for mid, g in MID_GROUP.items() if g == MID_GROUP.get(s['method'])]
        _rel = [x for x in services if x['method'] in _grp_mids and x['id'] != sid and x.get('status') not in ('廃業・撤退', '重複')][:6]
    _same_ent = [x for x in services if x['entity_id'] == s['entity_id'] and x['id'] != sid and x.get('status') not in ('廃業・撤退', '重複')][:4]
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
{ended_banner}
{dup_banner}
{pr}
<h2>条件</h2>
{rows}
{_radar_block(_svc_axes(s), esc(s.get('score', '') or e.get('score', '') or '―'), 'このサービスが公式に公表している項目の深さを、5つの軸で見たものです。')}
{_fee_band(s)}
{_svc_reading(s)}
{features}
{ent_block}
{rel_svcs}
{official}
{source}
{_log_block({s['name']})}
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
        f.write(build.page(f'{s["name"]}（{s["entity"]}）｜手数料・入金スピード・金額の条件' + ('（統合済み）' if _twin else ''), body, article=True, desc=desc, ld=ld, path=f'services/{_twin["id"].lower()}.html' if _twin else slug))
    urls.append(slug)

# ---------- compare pages ----------
for mid in sorted(compare_methods):
    m = methods[mid]
    svcs = svc_by_method.get(mid, [])
    direct = sorted([s for s in svcs if s.get('form') not in ('仲介・紹介', '比較メディア・送客') and s.get('status') not in ('廃業・撤退', '重複')], key=fee_num)
    inter = [s for s in svcs if s.get('form') in ('仲介・紹介', '比較メディア・送客') and s.get('status') not in ('廃業・撤退', '重複')]
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
    _fees = sorted(float(s['fee_hi']) for s in direct if (s.get('fee_hi') or '').replace('.', '', 1).isdigit())
    _med = _fees[len(_fees) // 2] if _fees else None
    _fb2 = sum(1 for s in direct if s['fee_lo'] and s['fee_hi'])
    def _sc(s):
        try:
            return int(s.get('score') or 0)
        except (TypeError, ValueError):
            return 0
    _sc4 = sum(1 for s in direct if _sc(s) >= 4)
    _cguide = (f'<h2>比べるときの見方</h2>'
               f'<p><b>仕組み：</b>{esc(m["how"])}</p>'
               f'<p><b>費用の決まり方：</b>{esc(m["cost"])}</p>'
               f'<p><b>注意点：</b>{esc(m["legal"])}</p>'
               + kv_table([('直接の事業者', f'{len(direct)}件'),
                           ('手数料の下限と上限の両方を公表', f'{_fb2}件'),
                           ('手数料・費用の上限の中央値', f'{_med:g}%' if _med is not None else '公表が少なく、算出していません'),
                           ('透明性スコア4以上', f'{_sc4}件')])
               + f'<p class="note">上限が非公表の会社は、申し込みの前に総額の見積もりを書面で確認してください。仕組みと向く状態は<a href="../methods/{build.mslug(mid)}.html">{esc(m["name"])}のページ</a>にまとめています。</p>')
    body = f"""
<p class="note"><a href="../index.html">トップ</a> ／ <a href="../methods/{build.mslug(mid)}.html">{esc(m['name'])}</a> ／ サービス比較</p>
<h1>{esc(m['name'])}のサービス比較</h1>
{_cpr}
<p>並びは、手数料の下限が小さい順という機械的な並びです。順位ではありません。比べた項目は手数料、入金スピード、金額、事業形態、透明性スコアです。手数料の上限が「非公表」の会社は、見積もりで幅の確認が必要です。数字は各社の公式の公表に基づき、確認日は各サービスのページに付けています。透明性スコアは確認できた公表項目の数で、定義は<a href="../about.html">運営者情報</a>に書いています。</p>
<h2>条件の一覧</h2>
<div class="tblwrap"><table class="wide"><tr><th>サービス</th><th>運営会社</th><th>手数料</th><th>入金スピード</th><th>金額</th><th>事業形態</th><th>透明性</th></tr>{trs}</table></div>
{_cb}
{_cguide}
<p><a href="../compare-tool.html">比較ツールで、気になるサービスを最大4社まで並べて比べる</a>（手法をまたいだ比較もできます）</p>
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

# ---------- cost index & compare tool ----------
_active = [s for s in services if s.get('status') not in ('廃業・撤退', '重複')]
_checked_max = max((s.get('checked') or '') for s in services)

def _share2(pred, pool):
    return round(100 * sum(1 for x in pool if pred(x)) / len(pool)) if pool else 0

def _score_of(x):
    v = x.get('score') or ent_by_id.get(x['entity_id'], {}).get('score') or ''
    return int(v) if str(v).isdigit() else 0

_ci_rows = ''
_ci_medians = []
for _mid, _m in methods.items():
    _pool = [s for s in _active if s['method'] == _mid]
    if not _pool:
        continue
    _dist = _fee_dist.get(_mid, [])
    _med = _stats.median(_dist) if len(_dist) >= 5 else None
    if _med is not None:
        _ci_medians.append((_m['name'], _med))
    _ci_rows += (f'<tr><td><a href="methods/{build.mslug(_mid)}.html">{esc(_m["name"])}</a></td>'
                 f'<td>{len(_pool)}件</td><td>{("%g%%" % _med) if _med is not None else "―"}</td>'
                 f'<td>{_share2(lambda x: x.get("fee_lo") and x.get("fee_hi"), _pool)}%</td>'
                 f'<td>{_share2(lambda x: x.get("amt_lo") and x.get("amt_hi"), _pool)}%</td>'
                 f'<td>{_share2(lambda x: x.get("speed"), _pool)}%</td>'
                 f'<td>{sum(1 for x in _pool if _score_of(x) >= 4)}件</td></tr>')
_m13 = [s for s in _active if s['method'] == 'M13']
_m13_fb = _share2(lambda x: x.get('fee_lo') and x.get('fee_hi'), _m13)
_m13_rec_none = sum(1 for x in _m13 if 'なし' in (x.get('recourse') or ''))
_m13_rec_unpub = sum(1 for x in _m13 if not x.get('recourse'))
_all_fb = _share2(lambda x: x.get('fee_lo') and x.get('fee_hi'), _active)
_lo_m = min(_ci_medians, key=lambda t: t[1])
_hi_m = max(_ci_medians, key=lambda t: t[1])
_rv_total = sum(v.get('count', 0) for v in REVIEWS.values())

def _amt_man(v):
    if not v:
        return None
    total = 0.0
    found = False
    m = re.search(r'([0-9,]+(?:\.[0-9]+)?)億', v)
    if m:
        total += float(m.group(1).replace(',', '')) * 10000
        found = True
    m = re.search(r'([0-9,]+(?:\.[0-9]+)?)万', v)
    if m:
        total += float(m.group(1).replace(',', ''))
        found = True
    return total if found else None

def _man_fmt(x):
    if x >= 10000:
        return f'{x / 10000:g}億円'
    return f'{x:g}万円'

def _amt_med(mid):
    vals = [_amt_man(s.get('amt_hi')) for s in _active if s['method'] == mid]
    vals = [v for v in vals if v]
    return _stats.median(vals) if len(vals) >= 3 else None

_sell = [s for s in _active if s['method'] in ('M13', 'M14', 'M15', 'M16', 'M17')]
_sell_rec = sum(1 for s in _sell if s.get('recourse'))
_sell_reg = sum(1 for s in _sell if s.get('registry'))
_onl_n = sum(1 for s in _active if s.get('online'))
_res_n = sum(1 for s in _active if s.get('results'))
_med13 = _stats.median(_fee_dist['M13'])
_am13 = _amt_med('M13')
_am16 = _amt_med('M16')
_am07 = _amt_med('M07')
_am09 = _amt_med('M09')
_onl24 = _share2(lambda x: x.get('online'), [s for s in _active if s['method'] == 'M24'])
_onl09 = _share2(lambda x: x.get('online'), [s for s in _active if s['method'] == 'M09'])
_onl13 = _share2(lambda x: x.get('online'), _m13)
_fb16 = _share2(lambda x: x.get('fee_lo') and x.get('fee_hi'), [s for s in _active if s['method'] == 'M16'])
_med24 = _stats.median(_fee_dist['M24'])
_ci_extra = f"""
<h2 class="sec">全体の数字</h2>
<p>収録しているのは、現在利用できる{len(_active)}のサービスと、その運営会社{len(entities)}社です。手数料の下限と上限がそろって公表されているのは全体の{_all_fb}%、オンラインで完結すると公表しているのは{_onl_n}件（{_share2(lambda x: x.get('online'), _active)}%）、実績の数字を公表しているのは{_res_n}件（{_share2(lambda x: x.get('results'), _active)}%）です。売掛金を扱う手法（ファクタリングと電子記録債権の売却、計{len(_sell)}件）では、償還請求権の扱いを公表しているのが{_sell_rec}件、債権譲渡登記の扱いを公表しているのが{_sell_reg}件にとどまります。Googleマップの口コミは、所在地まで確認できた会社を中心に{_rv_total:,}件を集計しています。</p>
<h2 class="sec">手法別の読み取り</h2>
<p><b>ファクタリング（2社間）</b>：収録{len(_m13)}件と、手法の中で最も厚い層です。手数料の上限の中央値は{_med13:g}%（公表{len(_fee_dist['M13'])}件）、金額の上限の中央値は{_man_fmt(_am13)}です。オンライン完結の公表は{_onl13}%で、償還請求権は「なし」と公表しているのが{_m13_rec_none}件あります。</p>
<p><b>診療報酬・介護報酬ファクタリング</b>：収録{len([s for s in _active if s['method'] == 'M16'])}件。手数料の下限と上限がそろって公表されているのは{_fb16}%で、主要な手法の中で最も低い水準です。金額の上限の中央値は{_man_fmt(_am16)}です。</p>
<p><b>請求書カード払い・B2B掛け払い</b>：収録{len([s for s in _active if s['method'] == 'M24'])}件。手数料の上限の中央値は{_med24:g}%と低く、オンライン完結の公表は{_onl24}%です。申し込みから支払いまでをオンラインで完結させる設計のサービスが集まっています。</p>
<p><b>ビジネスローン</b>：収録{len([s for s in _active if s['method'] == 'M07'])}件。費用は手数料ではなく金利で決まります。金額の上限の中央値は{_man_fmt(_am07)}です。</p>
<p><b>不動産担保ローン</b>：収録{len([s for s in _active if s['method'] == 'M09'])}件。金額の上限の中央値は{_man_fmt(_am09)}と大きい一方、オンライン完結の公表は{_onl09}%で、対面と書類の手続きが前提の手法です。</p>
<h2 class="sec">よくある質問</h2>
<h3>ファクタリングの手数料の相場はいくらですか</h3>
<p>2社間ファクタリングの収録{len(_m13)}件で、手数料の上限を公表している{len(_fee_dist['M13'])}件の中央値は{_med13:g}%です。ただし、下限と上限の両方を公表しているのは{_m13_fb}%で、残りは見積もりを取るまで幅が分かりません。相場の数字だけで判断せず、幅の見える会社から比べるのが安全です。</p>
<h3>費用が妥当かどうかは、どこで判断できますか</h3>
<p>手数料の上限だけでなく、下限と上限の幅、償還請求権の有無、債権譲渡登記の費用が別にかかるか、の3点で判断できます。このサイトの各サービスのページには、同じ手法の中での位置を文章と図で出しています。最大4社を並べる<a href="compare-tool.html">比較ツール</a>も使えます。</p>
<h3>公表が特に少ない項目は何ですか</h3>
<p>債権譲渡登記の扱い（売掛金を扱う{len(_sell)}件中{_sell_reg}件）と、償還請求権の扱い（同じく{_sell_rec}件）です。どちらも契約の条件を左右する項目ですが、公式サイトに書いていない会社が大半です。申し込みの前に、書面で確認してください。</p>
<h3>この集計の数字は、どこから来ていますか</h3>
<p>各社が公式サイトで公表している値を、当サイトが記録して集計したものです。公表されていない項目は推定で埋めていません。確認の方法と日付は、各サービスのページと<a href="about.html">運営者情報</a>に書いています。</p>
"""
_ci_faq_ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
    {'@type': 'Question', 'name': 'ファクタリングの手数料の相場はいくらですか',
     'acceptedAnswer': {'@type': 'Answer', 'text': f'2社間ファクタリングの収録{len(_m13)}件で、手数料の上限を公表している{len(_fee_dist["M13"])}件の中央値は{_med13:g}%です。下限と上限の両方を公表しているのは{_m13_fb}%です。'}},
    {'@type': 'Question', 'name': '公表が特に少ない項目は何ですか',
     'acceptedAnswer': {'@type': 'Answer', 'text': f'債権譲渡登記の扱い（売掛金を扱う{len(_sell)}件中{_sell_reg}件）と、償還請求権の扱い（同じく{_sell_rec}件）です。'}},
    {'@type': 'Question', 'name': 'この集計の数字は、どこから来ていますか',
     'acceptedAnswer': {'@type': 'Answer', 'text': '各社が公式サイトで公表している値を、当サイトが記録して集計したものです。公表されていない項目は推定で埋めていません。'}}]}

_ci_body = f"""
<p class="note"><a href="index.html">トップ</a> ／ 資金調達コスト・インデックス</p>
<h1>資金調達コスト・インデックス</h1>
<p>このサイトが収録している{len(_active)}のサービスについて、各社が公式に公表している費用と条件を手法ごとに集計したものです。数字は{_checked_max}時点の公表値に基づきます。「相場」を知りたいときの出発点として、また、公表がどこまで進んでいるかを見る物差しとして公開します。</p>
<h2 class="sec">集計で見えること</h2>
<ul>
<li>ファクタリング（2社間）の収録{len(_m13)}件で、手数料の下限と上限がそろって公表されているのは{_m13_fb}%です。償還請求権は「なし」と公表しているのが{_m13_rec_none}件で、公表自体がない会社が{_m13_rec_unpub}件あります。</li>
<li>手数料・費用の上限の中央値（公表が5件以上ある手法どうしの比較）では、最も低いのが「{_lo_m[0]}」の{_lo_m[1]:g}%、最も高いのが「{_hi_m[0]}」の{_hi_m[1]:g}%です。</li>
<li>収録サービス全体では、手数料の下限と上限がそろって公表されているのは{_all_fb}%にとどまります。費用の幅が見えないまま申し込む構造が、数字のうえでも確認できます。</li>
</ul>
<h2 class="sec">手法ごとの集計</h2>
<div class="tblwrap"><table class="wide"><tr><th>手法</th><th>収録</th><th>手数料・費用の上限の中央値</th><th>手数料の両方を公表</th><th>金額の両方を公表</th><th>入金スピードを公表</th><th>透明性スコア4以上</th></tr>{_ci_rows}</table></div>
<p class="note">中央値は、その手法の収録サービスのうち上限を公表しているものの中央値です。公表が5件未満の手法は算出していません。中央値や公表率は条件の良し悪しを示すものではありません。個別のサービスの条件は、各手法の比較ページとサービスのページで確認できます。</p>
{_ci_extra}
<h2 class="sec">集計の方法</h2>
<p>対象は、このサイトが収録しているサービスのうち、現在利用できる{len(_active)}件です。各社が公式サイトで公表している値を当サイトが記録し、手法ごとに集計しました。公表されていない項目は推定で埋めていません。あわせて、Googleマップの口コミは{_rv_total:,}件を集計し、各会社ページに評価と件数を表示しています。集計の前提は<a href="about.html">運営者情報</a>にも書いています。</p>
{build.CTA_BOX}
"""
_ci_ld = json.dumps({'@context': 'https://schema.org', '@type': 'Dataset', 'name': '資金調達コスト・インデックス',
                     'description': '資金調達の手法ごとに、各社の公式公表値から費用の中央値と公表率を集計したデータ。',
                     'dateModified': _checked_max, 'publisher': {'@type': 'Organization', 'name': '合同会社MELSY'}}, ensure_ascii=False)
_ci_ld = json.dumps([json.loads(_ci_ld), _ci_faq_ld], ensure_ascii=False)
with open(f'{OUT}/cost-index.html', 'w') as f:
    f.write(build.page('資金調達コスト・インデックス｜手法ごとの費用の中央値と公表率', _ci_body, desc='資金調達の手法ごとに、各社の公式公表値から手数料の中央値と公表率を集計したインデックス。相場と公表の進み具合を見る物差しです。', ld=_ci_ld, path='cost-index.html'))
urls.append('cost-index.html')

def _rng(lo, hi):
    if lo and hi:
        return f'{lo}〜{hi}'
    return lo or hi or '公表なし'

_tool = []
for _s in _active:
    _e = ent_by_id.get(_s['entity_id'], {})
    _aff = AFF.get(_s['id'])
    _rv = REVIEWS.get(_s['entity_id'])
    _fee = _rng(_s.get('fee_lo', ''), _s.get('fee_hi', ''))
    if _fee != '公表なし' and _s.get('fee_type'):
        _fee += f'（{_s["fee_type"]}）'
    _scv = _s.get('score') or _e.get('score') or ''
    _tool.append({'id': _s['id'], 'name': _s['name'], 'ent': _s['entity'],
                  'mid': methods.get(_s['method'], {}).get('name', ''),
                  'fee': _fee, 'spd': _s.get('speed') or '公表なし',
                  'amt': _rng(_s.get('amt_lo', ''), _s.get('amt_hi', '')),
                  'con': _s.get('contract') or '公表なし', 'rec': _s.get('recourse') or '公表なし',
                  'reg': _s.get('registry') or '公表なし', 'onl': _s.get('online') or '公表なし',
                  'sc': (f'{_scv} / 5' if _scv != '' else '―'),
                  'rv': (f'★{_rv["rating"]}（{_rv["count"]}件）' if _rv and _rv.get('count') else '集計なし'),
                  'url': (_aff or {}).get('url') or _s.get('url') or '',
                  'aff': 1 if _aff else 0,
                  'page': f'services/{_s["id"].lower()}.html'})
_tool_js = """
<p class="note"><a href="index.html">トップ</a> ／ 比較ツール</p>
<h1>サービス比較ツール</h1>
<p>気になるサービスを最大4つまで選ぶと、条件を横並びで比べられます。手法をまたいだ比較もできます。数字は各社の公式の公表に基づきます。</p>
__PR__
<input class="tool-search" id="tq" type="search" placeholder="サービス名・会社名・手法で探す" autocomplete="off">
<div class="tool-results" id="tres"></div>
<div class="tool-sel" id="tsel"></div>
<div class="tblwrap"><table class="wide" id="ttbl"></table></div>
<p class="note">「公表なし」は、その項目の公表を確認できていないという意味で、条件の良し悪しではありません。詳しい条件と確認日は、各サービスのページにあります。</p>
__CTA__
<script>
var DATA = __DATA__;
var sel = [];
var ROWS = [['運営会社','ent'],['手法','mid'],['費用','fee'],['入金スピード','spd'],['金額','amt'],['契約方式','con'],['償還請求権','rec'],['債権譲渡登記','reg'],['オンライン完結','onl'],['透明性スコア','sc'],['Google口コミ','rv']];
function byId(id){ for (var i=0;i<DATA.length;i++) if (DATA[i].id===id) return DATA[i]; return null; }
function render(){
  var chips = document.getElementById('tsel');
  chips.innerHTML = sel.map(function(id){ var d=byId(id); return '<span class="tool-chip">'+d.name+'<button data-rm="'+id+'" aria-label="外す">×</button></span>'; }).join('');
  var tbl = document.getElementById('ttbl');
  if (!sel.length){ tbl.innerHTML=''; return; }
  var h = '<tr><th>項目</th>' + sel.map(function(id){ var d=byId(id); return '<th><a href="'+d.page+'">'+d.name+'</a></th>'; }).join('') + '</tr>';
  ROWS.forEach(function(r){ h += '<tr><th>'+r[0]+'</th>' + sel.map(function(id){ return '<td>'+byId(id)[r[1]]+'</td>'; }).join('') + '</tr>'; });
  h += '<tr><th>公式サイト</th>' + sel.map(function(id){ var d=byId(id); return '<td>'+(d.url?'<a href="'+d.url+'" rel="'+(d.aff?'sponsored nofollow noopener':'nofollow noopener')+'" target="_blank">公式サイトをチェック</a>':'―')+'</td>'; }).join('') + '</tr>';
  tbl.innerHTML = h;
  chips.querySelectorAll('button').forEach(function(b){ b.onclick = function(){ sel = sel.filter(function(x){ return x !== b.getAttribute('data-rm'); }); render(); }; });
}
var q = document.getElementById('tq');
q.addEventListener('input', function(){
  var v = q.value.trim().toLowerCase(); var box = document.getElementById('tres');
  if (!v){ box.innerHTML=''; return; }
  var hits = DATA.filter(function(d){ return (d.name+' '+d.ent+' '+d.mid).toLowerCase().indexOf(v) >= 0 && sel.indexOf(d.id) < 0; }).slice(0, 12);
  box.innerHTML = hits.map(function(d){ return '<button class="tool-hit" data-add="'+d.id+'"><span>'+d.name+'<small>（'+d.ent+'／'+d.mid+'）</small></span><span class="tool-add">＋ 追加</span></button>'; }).join('') || '<p class="note">見つかりませんでした。</p>';
  box.querySelectorAll('button').forEach(function(b){ b.onclick = function(){ if (sel.length >= 4){ alert('比べられるのは4つまでです'); return; } sel.push(b.getAttribute('data-add')); q.value=''; box.innerHTML=''; render(); }; });
});
var pre = new URLSearchParams(location.search).get('s');
if (pre){ sel = pre.split(',').filter(function(id){ return byId(id); }).slice(0,4); }
render();
</script>
"""
_tool_body = _tool_js.replace('__DATA__', json.dumps(_tool, ensure_ascii=False)).replace('__PR__', PR_NOTICE).replace('__CTA__', build.CTA_BOX)
with open(f'{OUT}/compare-tool.html', 'w') as f:
    f.write(build.page('サービス比較ツール｜最大4社を並べて比べる', _tool_body, desc='資金調達サービスを最大4社まで選んで、費用、入金スピード、金額、契約の条件を横並びで比べられるツールです。', path='compare-tool.html'))
urls.append('compare-tool.html')


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
    _pairs = []
    for _ln in lines:
        _p = _ln.split(' ')
        if len(_p) >= 3:
            _pairs.append((_p[0], _p[1], _p[2]))
    _rmap = {s: t for s, t, _st in _pairs}
    def _final(t):
        _seen = set()
        while t in _rmap and t not in _seen:
            _seen.add(t)
            t = _rmap[t]
        return t
    lines = [f'{s} {_final(t)} {st}' for s, t, st in _pairs]
    with open(f'{OUT}/_redirects', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('redirects:', len(lines))
with open(f'{OUT}/robots.txt', 'w') as f:
    f.write('User-agent: *\nAllow: /\nSitemap: https://kensetusikinnavi.net/sitemap.xml\n')
