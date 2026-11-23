import json, re, html, os, base64, shutil

BASE = '/home/hatch/workspace/affiliate-site-automation'
OUT = '/home/hatch/workspace/web-deploy/connection-test/shikin'
REVIEW = os.environ.get('REVIEW') == '1'
os.makedirs(OUT + '/articles', exist_ok=True)
if not REVIEW:
    os.makedirs(OUT + '/assets', exist_ok=True)
    for f in ('hero-bg.mp4', 'hero-poster.webp', 'section-observation.webp', 'section-owner.webp'):
        shutil.copy(f'{BASE}/site/assets/{f}', f'{OUT}/assets/{f}')

def asset(name):
    if REVIEW:
        mime = 'image/webp' if name.endswith('.webp') else 'video/mp4'
        b = base64.b64encode(open(f'{BASE}/site/assets/{name}', 'rb').read()).decode()
        return f'data:{mime};base64,{b}'
    return f'assets/{name}'

data = json.load(open(BASE + '/site/data.json'))
NSVC = len(data['services'])
NENT = len(data['entities'])
NLOG = len(data['log'])
methods = data['methods']
services = data['services']
scores = data['scores']
log = data['log']

NEEDS_ARV = {'M10', 'M11', 'M13', 'M14', 'M15', 'M16', 'M17'}
TAX_CAUTION = {'M02', 'M03', 'M04', 'M05', 'M06', 'M18', 'M19', 'M20'}

def _days(period, fn):
    vals = []
    for n in re.findall(r'(\d+)\s*か月', period or ''):
        vals.append(int(n) * 30)
    for n in re.findall(r'(\d+)\s*週間', period or ''):
        vals.append(int(n) * 7)
    if '数週間' in (period or ''):
        vals.append(21 if fn == 'max' else 14)
    if '数日' in (period or ''):
        vals.append(3 if fn == 'max' else 2)
    if '即日' in (period or ''):
        vals.append(0)
    return (max(vals) if fn == 'max' else min(vals)) if vals else 999

for m in methods:
    m['maxDays'] = _days(m['period'], 'max')
    m['minDays'] = _days(m['period'], 'min')
    m['needsArv'] = m['id'] in NEEDS_ARV
    m['taxCaution'] = m['id'] in TAX_CAUTION

svc_by_method = {}
for s in services:
    s['score'] = scores.get(s['entity_id'], '')
    svc_by_method.setdefault(s['method'], []).append(s)

CSS = """
:root{
  --primary:#14504C; --primary-deep:#0B3532; --cta:#C2410C; --cta-dark:#9A3412; --gold:#E8B34B;
  --ink:#191919; --sub:#5A564E; --bg:#FAF8F4; --surface:#FFFFFF; --line:#DDD8CE; --chip:#EAF2F1;
  --shadow:0 1px 2px rgba(20,40,38,.05),0 8px 24px rgba(20,40,38,.06);
  --shadow-lg:0 2px 4px rgba(20,40,38,.06),0 16px 40px rgba(20,40,38,.12);
  --radius:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Noto Sans JP',-apple-system,'Hiragino Kaku Gothic ProN',sans-serif;font-size:16px;line-height:1.85;letter-spacing:.02em;color:var(--ink);background:var(--bg);margin:0;padding:0 0 120px;-webkit-font-smoothing:antialiased}
::selection{background:var(--primary);color:#fff}
.wrap{max-width:1024px;margin:0 auto;padding:0 20px}
a{color:var(--primary)}
:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
header.site{background:rgba(255,255,255,.92);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:40;backdrop-filter:blur(6px)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:62px;padding-top:8px;padding-bottom:8px}
.logo{font-weight:900;font-size:17px;color:var(--primary);letter-spacing:.03em;line-height:1.35;min-width:0}
.logo small{display:block;font-size:10px;color:var(--sub);font-weight:500;letter-spacing:.06em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hdr-cta{background:var(--cta);color:#fff;text-decoration:none;font-weight:700;border-radius:8px;padding:10px 16px;font-size:14px;letter-spacing:.04em;min-height:44px;display:inline-flex;align-items:center;transition:background .2s;white-space:nowrap;flex:none}
.hdr-cta:hover{background:var(--cta-dark)}
.hero{position:relative;color:#fff;overflow:hidden;background:var(--primary-deep) center/cover no-repeat}
.hero-media{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hero-shade{position:absolute;inset:0;background:linear-gradient(100deg,rgba(8,38,35,.92) 0%,rgba(8,38,35,.72) 46%,rgba(8,38,35,.30) 100%)}
.hero-in{position:relative;padding:84px 0 72px;max-width:680px}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:var(--gold);margin:0 0 18px}
.eyebrow.dark{color:var(--cta)}
.hero h1{font-size:clamp(30px,5.2vw,52px);line-height:1.32;font-weight:900;letter-spacing:.02em;margin:0 0 20px}
.hero h1 em{font-style:normal;color:var(--gold)}
.hero p.lead{font-size:17px;line-height:1.9;margin:0 0 30px;max-width:600px;color:rgba(255,255,255,.94)}
.hero-cta{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.hero-note{font-size:13px;color:rgba(255,255,255,.82);margin-top:16px;letter-spacing:.03em}
.hero-stats{display:flex;gap:0;flex-wrap:wrap;margin-top:44px;border-top:1px solid rgba(255,255,255,.28);padding-top:22px}
.hstat{padding-right:30px;margin-right:30px;border-right:1px solid rgba(255,255,255,.22)}
.hstat:last-child{border-right:0;margin-right:0;padding-right:0}
.hstat b{display:block;font-size:34px;font-weight:900;line-height:1.1;font-variant-numeric:tabular-nums}
.hstat b i{font-style:normal;font-size:16px;font-weight:700;margin-left:2px}
.hstat span{font-size:12px;color:rgba(255,255,255,.8);letter-spacing:.06em}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border-radius:10px;font-weight:700;letter-spacing:.04em;text-decoration:none;cursor:pointer;border:0;min-height:56px;padding:14px 28px;font-size:16px;transition:transform .18s,box-shadow .18s,background .18s}
.btn-cta{background:var(--cta);color:#fff;box-shadow:0 6px 20px rgba(194,65,12,.35)}
.btn-cta:hover{background:var(--cta-dark);transform:translateY(-2px)}
.btn-hero{font-size:18px;min-height:62px;padding:16px 36px}
.btn-glass{background:rgba(255,255,255,.1);color:#fff;border:1.5px solid rgba(255,255,255,.55)}
.btn-glass:hover{background:rgba(255,255,255,.2)}
.btn-sub{background:var(--surface);color:var(--primary);border:2px solid var(--primary)}
.btn-sub:hover{background:var(--chip)}
.btn-ghost{background:transparent;color:var(--primary);border:2px solid var(--line)}
.btn-sm{min-height:48px;padding:10px 20px;font-size:15px;border-radius:8px}
section{padding:72px 0 4px}
h2.sec{font-size:26px;font-weight:900;letter-spacing:.03em;line-height:1.5;margin:0 0 10px}
.sec-sub{color:var(--sub);margin:0 0 24px;max-width:720px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:30px;box-shadow:var(--shadow)}
.progress{height:8px;background:#ECE9E2;border-radius:4px;overflow:hidden;margin:8px 0 6px}
.progress i{display:block;height:100%;background:var(--cta);border-radius:4px;transition:width .35s cubic-bezier(.22,.61,.36,1)}
.step-label{font-size:12px;color:var(--sub);font-weight:700;letter-spacing:.14em}
.wiz-q{font-size:22px;font-weight:900;letter-spacing:.03em;margin:12px 0 20px;animation:fadeSlide .35s cubic-bezier(.22,.61,.36,1)}
.opts{display:grid;gap:12px;animation:fadeSlide .35s cubic-bezier(.22,.61,.36,1)}
@media(min-width:640px){.opts{grid-template-columns:1fr 1fr}}
@keyframes fadeSlide{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.opt{display:flex;align-items:center;gap:12px;border:2px solid var(--line);border-radius:12px;padding:16px 18px;font-size:16px;font-weight:700;letter-spacing:.03em;cursor:pointer;min-height:64px;background:#fff;text-align:left;width:100%;font-family:inherit;color:var(--ink);transition:border-color .15s,background .15s}
.opt:hover{border-color:var(--primary)}
.opt.sel{border-color:var(--cta);background:#FFF4EC}
.opt .sub{display:block;font-weight:500;font-size:13px;color:var(--sub);letter-spacing:.02em}
.wiz-nav{display:flex;justify-content:space-between;align-items:center;margin-top:22px}
.linkbtn{background:none;border:0;color:var(--primary);font-size:15px;font-weight:700;cursor:pointer;min-height:44px;font-family:inherit}
.steps3{display:grid;gap:12px;margin-top:18px}
@media(min-width:760px){.steps3{grid-template-columns:repeat(3,1fr)}}
.step3{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;box-shadow:var(--shadow)}
.step3 b{display:flex;align-items:center;gap:10px;font-size:15px}
.step3 b i{font-style:normal;background:var(--primary);color:#fff;width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:14px;flex:none}
.step3 p{margin:8px 0 0;font-size:14px;color:var(--sub)}
.result-head{background:var(--chip);border-radius:var(--radius);padding:22px 26px;margin-bottom:20px}
.result-head b{font-size:20px;letter-spacing:.03em}
.mcard{border:1px solid var(--line);border-radius:var(--radius);background:#fff;padding:22px 24px;margin:0 0 16px;box-shadow:var(--shadow)}
.mcard h3{margin:0 0 6px;font-size:19px;letter-spacing:.03em}
.kv{display:grid;grid-template-columns:92px 1fr;gap:5px 14px;font-size:15px;margin:12px 0}
.kv dt{color:var(--sub);font-weight:700}
.kv dd{margin:0}
.svc{display:flex;justify-content:space-between;gap:12px;border-top:1px dashed var(--line);padding:11px 0;font-size:14px}
.svc:first-of-type{border-top:0}
.badge{display:inline-block;background:var(--primary);color:#fff;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:.04em;padding:3px 11px;white-space:nowrap;height:fit-content}
.badge.low{background:#8A8578}
.cta-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}
details.unfit,details.faq{border:1px solid var(--line);border-radius:var(--radius);background:#fff;padding:4px 22px;margin-bottom:10px;box-shadow:var(--shadow)}
details.unfit summary,details.faq summary{cursor:pointer;font-weight:700;min-height:48px;display:flex;align-items:center;letter-spacing:.02em}
details.unfit p,details.faq p{font-size:14.5px;color:#33312D;padding-bottom:10px}
.why-list{margin:0 0 8px;padding-left:20px;font-size:14.5px;line-height:1.8}
.split{display:grid;gap:26px;align-items:stretch}
@media(min-width:860px){.split{grid-template-columns:5fr 7fr}}
.split img.photo{width:100%;height:100%;object-fit:cover;border-radius:var(--radius);box-shadow:var(--shadow-lg);display:block}
.stat-band{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:18px;text-align:center;box-shadow:var(--shadow)}
.stat b{display:block;font-size:32px;color:var(--primary);font-weight:900;font-variant-numeric:tabular-nums;line-height:1.15}
.stat span{font-size:12.5px;color:var(--sub);letter-spacing:.05em}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:14px;background:#fff}
th,td{border-bottom:1px solid var(--line);padding:10px 12px;text-align:left;vertical-align:top}
tr:last-child td{border-bottom:0}
th{background:var(--chip);font-weight:700;letter-spacing:.03em;white-space:nowrap}
tbody tr:hover td{background:#FBF9F4}
.tblwrap table.wide{min-width:640px}
.svc-cards{display:grid;gap:12px}
@media(min-width:760px){.svc-cards{grid-template-columns:1fr 1fr}}
.svc-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow)}
.svc-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.svc-top b{font-size:15.5px;letter-spacing:.02em}
.svc-ent{font-size:13px;color:var(--sub)}
.svc-kv{display:grid;grid-template-columns:1fr 1fr;gap:6px 10px;margin:10px 0 0}
.svc-kv>div:last-child{grid-column:1/-1}
@media(min-width:640px){.svc-kv{grid-template-columns:repeat(3,1fr)}.svc-kv>div:last-child{grid-column:auto}}
.svc-kv dt{font-size:11.5px;color:var(--sub);font-weight:700;letter-spacing:.04em}
.svc-kv dd{margin:0;font-size:13.5px;font-variant-numeric:tabular-nums;line-height:1.55}
.more-row{text-align:center;margin-top:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.state-card{display:block;background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;text-decoration:none;color:var(--ink);box-shadow:var(--shadow);transition:transform .18s,box-shadow .18s}
.state-card:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg)}
.state-card b{font-size:15.5px;letter-spacing:.02em}
.state-card span{display:block;color:var(--cta);font-weight:700;font-size:13.5px;margin-top:6px}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
.filters select{font-size:15px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;min-height:46px;background:#fff;font-family:inherit}
.filters label{font-size:14px;font-weight:700;display:inline-flex;align-items:center;gap:6px;min-height:46px}
.filters input[type=checkbox]{width:18px;height:18px;accent-color:var(--primary)}
.pr{display:inline-block;background:#FFF3D6;border:1px solid #D9A400;color:#6B4E00;font-size:12px;font-weight:700;border-radius:6px;padding:3px 10px;letter-spacing:.03em}
article h1{font-size:28px;line-height:1.55;font-weight:900;letter-spacing:.02em}
article h2{font-size:21px;font-weight:900;letter-spacing:.03em;border-left:6px solid var(--primary);padding-left:12px;margin-top:38px}
article h3{font-size:17px}
.cta-box{background:var(--chip);border-radius:var(--radius);padding:28px;text-align:center;margin:44px 0}
.aff-banner{margin:24px 0;text-align:center}
.aff-banner img{max-width:100%;height:auto}
.cta-box p{font-weight:900;font-size:18px;margin:0 0 16px;letter-spacing:.03em}
.sticky-cta{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.96);border-top:1px solid var(--line);padding:10px 12px calc(10px + env(safe-area-inset-bottom));z-index:50;backdrop-filter:blur(6px);box-sizing:border-box;max-width:100vw;overflow:hidden}
.bar-btn{display:block;width:100%;max-width:640px;margin:0 auto;box-sizing:border-box;min-height:48px;padding:12px 16px;font-size:15px;text-align:center;white-space:normal}
@media(max-width:640px){.hstat{padding-right:18px;margin-right:18px}.hstat b{font-size:26px}section{padding:52px 0 4px}.logo{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.logo small{display:none}.hdr-cta{padding:9px 11px;font-size:13px}header.site .wrap{padding-left:14px;padding-right:14px}}
footer.site{border-top:1px solid var(--line);margin-top:64px;padding:30px 0 10px;color:var(--sub);font-size:13px}
.dnav{display:none}
@media(min-width:1100px){.dnav{display:flex;align-items:center;gap:2px}.dnav a{padding:8px 9px;font-size:13.5px;font-weight:700;color:var(--ink2);white-space:nowrap}.menu-btn{display:none}}
.menu-btn{flex:none;background:#fff;border:1.5px solid var(--primary);color:var(--primary);border-radius:10px;padding:9px 13px;font-size:13.5px;font-weight:800;cursor:pointer;font-family:inherit}
.mpanel{position:fixed;inset:0;background:var(--bg);z-index:90;display:none;padding:18px 20px calc(18px + env(safe-area-inset-bottom));overflow-y:auto}
body.menu-open .mpanel{display:block}
body.menu-open{overflow:hidden}
.mpanel .mp-head{display:flex;justify-content:space-between;align-items:center;max-width:1024px;margin:0 auto 10px}
.mpanel .mp-title{font-weight:900;color:var(--primary);font-size:16px}
.mpanel .mp-close{background:#fff;border:1.5px solid var(--line);border-radius:10px;padding:9px 14px;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit;color:var(--ink)}
.mpanel nav{max-width:1024px;margin:0 auto;display:flex;flex-direction:column}
.mpanel nav a{display:flex;flex-direction:column;align-items:flex-start;justify-content:center;min-height:54px;padding:6px 4px;font-size:17px;font-weight:800;color:var(--ink);border-bottom:1px solid var(--line);text-decoration:none}
.mpanel nav a small{display:block;font-size:12.5px;font-weight:500;color:var(--mut)}

.fcols{display:grid;grid-template-columns:1fr 1fr;gap:18px 22px;margin:8px 0 18px;text-align:left}
@media(min-width:900px){.fcols{grid-template-columns:repeat(4,1fr)}}
.flist .fhead{display:block;font-size:13px;font-weight:900;color:var(--primary);margin-bottom:6px;text-decoration:none}
.flist a.l{display:block;font-size:13.5px;padding:3.5px 0;color:var(--ink2);line-height:1.45}
.sgrid{display:grid;gap:12px;margin-top:6px}
@media(min-width:760px){.sgrid{grid-template-columns:1fr 1fr}}
.scard{border:1px solid var(--line);border-radius:14px;padding:18px;background:#fff;text-align:left}
.scard i{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:var(--primary);color:#fff;font-style:normal;font-weight:900;font-size:14px;margin-bottom:8px}
.scard b{display:block;font-size:16.5px;margin-bottom:5px}
.scard p{margin:0 0 10px;font-size:14px;color:var(--ink2);line-height:1.65}
.scard a{font-size:14px;font-weight:700}
.mapwrap{border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:14px 0;background:#fff}
.mapwrap iframe{width:100%;height:260px;border:0;display:block}
.pub{list-style:none;padding:0;margin:10px 0}
.pub li{padding:7px 0;border-bottom:1px dashed var(--line);font-size:14.5px}
.pub li b{display:inline-block;min-width:52px;color:var(--primary)}
.pub li .no{color:var(--ink2)}
.fig{border:1px solid var(--line);border-radius:14px;background:#fff;padding:16px 14px 10px;margin:18px 0}
.fig svg{display:block;width:100%;height:auto}
.fig figcaption{font-size:12.5px;color:var(--ink2);margin-top:8px;line-height:1.6}
.fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:10px}
.fcard{display:block;border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:#fff;text-decoration:none}
.fcard b{display:block;font-size:14.5px;color:var(--ink);line-height:1.45}
.fcard span{display:block;font-size:12.5px;color:var(--mut);margin-top:3px;line-height:1.55}
.toc{border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin:20px 0;background:#fff}
.toc b{display:block;font-size:14px;margin-bottom:6px;color:var(--primary)}
.toc ol{margin:0;padding-left:20px}
.toc li{margin:4px 0;font-size:14.5px;line-height:1.5}
.cta-mini{border:1.5px solid var(--cta);border-radius:14px;padding:13px 16px;margin:20px 0;background:#FFF7ED;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.cta-mini p{margin:0;font-size:14.5px;font-weight:700;flex:1;min-width:180px}
.cta-mini a{flex:none}
.byline{border-top:1px solid var(--line);margin:30px 0 0;padding:14px 0 0;font-size:13.5px;color:var(--mut);line-height:1.7}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 9px;font-size:12px;color:var(--ink2);margin:3px 4px 0 0;background:#fff}
.rel-box{border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:26px 0;background:#fff;text-align:left}
.rel-box h2{font-size:17px;margin:0 0 6px}
.rel-box p{margin:10px 0 2px}
.rel-box ul{margin:0;padding-left:18px}
.rel-box li{margin:4px 0;font-size:14.5px;line-height:1.55}
footer.site .fname{font-weight:900;color:var(--primary);font-size:15px;letter-spacing:.03em;margin:0 0 4px}
.hscroll{display:flex;gap:14px;overflow-x:auto;padding:6px 2px 18px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch}
.hscroll>.mcard{flex:0 0 292px;scroll-snap-align:start;margin:0}
@media(min-width:760px){.hscroll>.mcard{flex-basis:330px}}
.scroll-hint{font-size:12.5px;color:var(--sub);margin:0 0 8px;letter-spacing:.05em}
.lead-panel{background:var(--primary-deep);color:#fff;border-radius:var(--radius);padding:30px;margin:34px 0 8px;box-shadow:var(--shadow-lg)}
.lead-panel h3{margin:0 0 8px;font-size:21px;letter-spacing:.03em}
.lead-panel p{margin:0 0 16px;color:rgba(255,255,255,.92);font-size:15px}
.lead-form{display:grid;gap:12px}
@media(min-width:640px){.lead-form{grid-template-columns:1fr 1fr}.lead-form .wide{grid-column:1/-1}}
.lead-form label{font-size:13px;font-weight:700;letter-spacing:.04em;display:block}
.lead-form input{width:100%;margin-top:5px;padding:12px 14px;border-radius:8px;border:1.5px solid rgba(255,255,255,.4);background:#fff;color:var(--ink);font-size:16px;font-family:inherit;min-height:50px}
.lead-form .req{color:var(--gold);font-size:11.5px;margin-left:4px}
.lead-note{font-size:12.5px;color:rgba(255,255,255,.75);margin:12px 0 0}
.note{font-size:13px;color:var(--sub)}
.rv{opacity:0;transform:translateY(18px);transition:opacity .7s cubic-bezier(.22,.61,.36,1),transform .7s cubic-bezier(.22,.61,.36,1)}
.rv.on{opacity:1;transform:none}
@media (prefers-reduced-motion: reduce){
  .rv{opacity:1;transform:none;transition:none}
  .wiz-q,.opts{animation:none}
  html{scroll-behavior:auto}
}
"""

REVEAL_JS = "const io = new IntersectionObserver(es => es.forEach(e => { if(e.isIntersecting){ e.target.classList.add('on'); io.unobserve(e.target); } }), {threshold: .12}); document.querySelectorAll('.rv').forEach(el => io.observe(el));"

BASE_URL = 'https://kensetusikinnavi.net/'

MSLUG = {'M01': '銀行融資', 'M02': '信用保証協会付き融資', 'M03': '日本政策金融公庫', 'M04': '制度融資', 'M05': 'マル経融資', 'M06': 'セーフティネット保証', 'M07': 'ビジネスローン', 'M08': 'カードローン', 'M09': '不動産担保ローン', 'M10': 'ABL', 'M11': '手形割引', 'M12': 'リースと割賦', 'M13': 'ファクタリング2社間', 'M14': 'ファクタリング3社間', 'M15': '注文書ファクタリング', 'M16': '診療報酬ファクタリング', 'M17': '電子記録債権', 'M18': '補助金', 'M19': '雇用助成金', 'M20': '利子補給', 'M21': 'クラウドファンディング', 'M22': '出資', 'M23': '私募債', 'M24': '請求書カード払い'}

def mslug(mid):
    return MSLUG.get(mid, (mid or '').lower())


ANALYTICS_TAGS = """<meta name="google-site-verification" content="awXV921gXdL9ZE5oPz-J0BztoyJs1I80R4oJdtl66Cg">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-4LCT3L2TED"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-4LCT3L2TED');</script>"""

def page(title, body, article=False, desc='', ld='', path=None):
    prefix = '../' if article else ''
    main_open = '<article class="wrap">' if article else '<main>'
    main_close = '</article>' if article else '</main>'
    meta = ''
    if desc:
        meta += f'<meta name="description" content="{html.escape(desc, quote=True)}">'
        meta += f'<meta property="og:description" content="{html.escape(desc, quote=True)}">'
    if path is not None:
        meta += f'<link rel="canonical" href="{BASE_URL}{path}">'
    meta += f'<meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:type" content="{"article" if article else "website"}">'
    if ld:
        meta += f'<script type="application/ld+json">{ld}</script>'
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{ANALYTICS_TAGS}
<title>{html.escape(title)}</title>{meta}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&display=swap">
<style>{CSS}</style></head>
<body>
<header class="site"><div class="wrap"><div class="logo">建設的な資金調達を実現するサイト<small>可能性のある資金調達方法を、全ての手法から探し出す</small></div><nav class="dnav"><a href="{prefix}index.html#check">状態チェック</a><a href="{prefix}methods/index.html">手法ガイド</a><a href="{prefix}articles/index.html#basics">基礎知識</a><a href="{prefix}articles/index.html#guides">状態別の記事</a><a href="{prefix}index.html#compare">比較</a><a href="{prefix}index.html#search">サービスを探す</a></nav><a class="hdr-cta" href="{prefix}index.html#check">状態チェック</a><button class="menu-btn" onclick="document.body.classList.add('menu-open')">メニュー</button></div></header>
<div class="mpanel"><div class="mp-head"><span class="mp-title">メニュー</span><button class="mp-close" onclick="document.body.classList.remove('menu-open')">閉じる</button></div><nav><a href="{prefix}index.html#check" onclick="document.body.classList.remove('menu-open')">状態チェック<small>上位の手法から順に確認します</small></a><a href="{prefix}methods/index.html">手法ガイド<small>全24手法の仕組みと条件</small></a><a href="{prefix}articles/index.html#basics">基礎知識<small>仕組みの根幹を先に知る</small></a><a href="{prefix}articles/index.html#guides">状態別の記事<small>状況ごとの進め方</small></a><a href="{prefix}index.html#compare" onclick="document.body.classList.remove('menu-open')">サービスの比較<small>手法ごとの手数料と速さ</small></a><a href="{prefix}index.html#search" onclick="document.body.classList.remove('menu-open')">サービスを探す<small>{NSVC}件から条件で絞る</small></a><a href="{prefix}about.html">運営者情報</a><a href="{prefix}privacy.html">プライバシーポリシー</a></nav></div>
{main_open}{body}{main_close}
<div class="sticky-cta"><a class="btn btn-cta bar-btn" href="{prefix}index.html#check">状態チェックをはじめる</a></div>
<footer class="site"><div class="wrap"><p class="fname">建設的な資金調達を実現するサイト</p>{footer_cols(prefix)}<p>運営：合同会社MELSY（<a href="{prefix}about.html">運営者情報</a>）</p>このサイトは一般的な情報の提供を目的としています。個別の可否は各社の審査で決まります。</div></footer>
<script>{REVEAL_JS}</script>
</body></html>"""

def md2html(md):
    lines = md.split('\n')
    out = []
    i = 0
    def inline(t):
        t = html.escape(t)
        t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', t)
        return t
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == '```raw':
            buf = []
            i += 1
            while i < len(lines) and lines[i].strip() != '```':
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('\n'.join(buf))
            continue
        if ln.startswith('|') and i + 1 < len(lines) and lines[i+1].startswith('|-'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            head, body_rows = rows[0], rows[2:]
            t = '<div class="tblwrap"><table' + (' class="wide"' if len(head) >= 4 else '') + '><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr>'
            for r in body_rows:
                t += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
            out.append(t + '</table></div>')
            continue
        if ln.startswith('### '):
            out.append(f'<h3>{inline(ln[4:])}</h3>')
        elif ln.startswith('## '):
            out.append(f'<h2>{inline(ln[3:])}</h2>')
        elif ln.startswith('# '):
            out.append(f'<h1>{inline(ln[2:])}</h1>')
        elif ln.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append(f'<li>{inline(lines[i][2:])}</li>')
                i += 1
            out.append('<ul>' + ''.join(items) + '</ul>')
            continue
        elif re.match(r'^\d+\. ', ln):
            items = []
            while i < len(lines) and re.match(r'^\d+\. ', lines[i]):
                items.append(f'<li>{inline(re.sub(r"^\d+\. ", "", lines[i]))}</li>')
                i += 1
            out.append('<ol>' + ''.join(items) + '</ol>')
            continue
        elif ln.strip() == '':
            pass
        else:
            out.append(f'<p>{inline(ln)}</p>')
        i += 1
    return '\n'.join(out)

CTA_BOX = """<div class="cta-box"><p>あなたの状態では、どの手法が期限に間に合いますか</p><a class="btn btn-cta" href="../index.html#check">状態チェックで確認する</a></div>"""

SAMPLES = [
    ('../pillar/guide-first-time.md', 'guide-first-time.html', False),
    ('../pillar/guide-rejected.md', 'guide-rejected.html', False),
    ('../pillar/guide-tax-arrears.md', 'guide-tax-arrears.html', False),
    ('../pillar/guide-startup.md', 'guide-startup.html', False),
    ('../pillar/guide-akaji.md', 'guide-akaji.html', False),
    ('../pillar/guide-equipment.md', 'guide-equipment.html', False),
    ('../pillar/guide-subsidy-bridge.md', 'guide-subsidy-bridge.html', False),
    ('../pillar/guide-arv-delay.md', 'guide-arv-delay.html', False),
    ('../pillar/guide-urgent.md', 'guide-urgent.html', False),
    ('../pillar/guide-no-notify.md', 'guide-no-notify.html', False),
    ('../pillar/guide-refinance.md', 'guide-refinance.html', False),
    ('../pillar/guide-order-received.md', 'guide-order-received.html', False),
    ('../pillar/guide-tax-payment.md', 'guide-tax-payment.html', False),
    ('../pillar/guide-sole-proprietor.md', 'guide-sole-proprietor.html', False),
    ('../pillar/guide-medical-care.md', 'guide-medical-care.html', False),
    ('../pillar/guide-notes-receivable.md', 'guide-notes-receivable.html', False),
    ('サンプル_型1_状態別アドバイス.md', 'guide-payment-gap.html', False),

    ('サンプル_型5_基礎知識と手続き.md', 'basics-2sha.html', False),
    ('基礎知識_ファクタリングとは.md', 'basics-factoring.html', False),
    ('基礎知識_償還請求権とは.md', 'basics-recourse.html', False),
    ('基礎知識_債権譲渡登記とは.md', 'basics-registry.html', False),
    ('基礎知識_信用保証協会とは.md', 'basics-guarantee.html', False),
    ('基礎知識_セーフティネット保証の認定.md', 'basics-safety-net.html', False),
]

def _art_file(fname):
    return f'{BASE}/files/samples/{fname}' if not fname.startswith('../') else f'{BASE}/files/{fname[3:]}'

def _art_title(fname):
    md = open(_art_file(fname)).read()
    parts = md.split('\n---\n')
    body_md = '\n---\n'.join(parts[1:]) if len(parts) > 1 else md
    m = re.search(r'^# (.+)$', body_md, flags=re.M)
    return m.group(1) if m else fname

ART_TITLES = {slug: _art_title(f) for f, slug, pr in SAMPLES}

def _art_desc(fname):
    md = open(_art_file(fname)).read()
    parts = md.split('\n---\n')
    m = re.search(r'メタディスクリプション：(.+)', parts[0]) if len(parts) > 1 else None
    return m.group(1).strip() if m else ''

ART_DESCS = {slug: _art_desc(f) for f, slug, pr in SAMPLES}
BASICS_SLUGS = [slug for f, slug, pr in SAMPLES if slug.startswith('basics-')]
PILLAR_SLUGS = [slug for f, slug, pr in SAMPLES if slug.startswith('guide-')]
ART_METHODS = {}
for _f, _slug, _pr in SAMPLES:
    _text = open(_art_file(_f)).read()
    ART_METHODS[_slug] = {m['id'] for m in methods if m['name'] in _text}
from collections import Counter as _Counter
_direct = _Counter()
for _s in services:
    if _s.get('form') not in ('仲介・紹介', '比較メディア・送客') and (_s.get('fee_lo') or '').strip():
        _direct[_s['method']] += 1
COMPARE_MIDS = [m['id'] for m in methods if _direct[m['id']] >= 4]

def footer_cols(prefix):
    def links(items):
        return ''.join(f'<a class="l" href="{u}">{html.escape(t)}</a>' for u, t in items)
    basics = links([(f'{prefix}articles/{sl}', ART_TITLES[sl]) for sl in BASICS_SLUGS])
    pillars = links([(f'{prefix}articles/{sl}', ART_TITLES[sl]) for sl in PILLAR_SLUGS])
    meths = links([(f'{prefix}methods/{mslug(mm["id"])}.html', mm['name']) for mm in methods])
    comps = links([(f'{prefix}compare/{mid.lower()}.html', next(mm['name'] for mm in methods if mm['id'] == mid) + 'のサービス比較') for mid in COMPARE_MIDS])
    return (f'<div class="fcols"><div class="flist"><a class="fhead" href="{prefix}articles/index.html#basics">基礎知識（仕組みの根幹）</a>{basics}</div>'
            f'<div class="flist"><a class="fhead" href="{prefix}articles/index.html#guides">状態別の進め方</a>{pillars}</div>'
            f'<div class="flist"><a class="fhead" href="{prefix}methods/index.html">手法ガイド</a>{meths}</div>'
            f'<div class="flist"><span class="fhead">サービスの比較</span>{comps}</div></div>')

def rel_box(slug):
    basics = ''.join(f'<li><a href="{s2}">{html.escape(ART_TITLES[s2])}</a></li>' for s2 in BASICS_SLUGS if s2 != slug)
    shared = []
    for s2 in PILLAR_SLUGS:
        if s2 == slug:
            continue
        n = len(ART_METHODS.get(slug, set()) & ART_METHODS.get(s2, set()))
        if n:
            shared.append((n, s2))
    shared.sort(key=lambda x: -x[0])
    h = '<div class="rel-box"><h2>次に読む</h2><p><b>基礎知識（仕組みの根幹）</b></p><ul>' + basics + '</ul>'
    if shared:
        h += '<p><b>関連する状態別の記事</b></p><ul>' + ''.join(f'<li><a href="{s2}">{html.escape(ART_TITLES[s2])}</a></li>' for n, s2 in shared[:4]) + '</ul>'
    return h + '</div>'

for fname, slug, pr in SAMPLES:
    md = open(f'{BASE}/files/samples/{fname}').read() if not fname.startswith('../') else open(f'{BASE}/files/{fname[3:]}').read()
    parts = md.split('\n---\n')
    body_md = '\n---\n'.join(parts[1:]) if len(parts) > 1 else md
    body_md = re.sub(r'^この記事には広告（PR）が含まれます。\n', '', body_md, flags=re.M)
    body_md = re.sub(r'^（広告を含む記事ではないため、PR表示は置かない）\n?', '', body_md, flags=re.M)
    title_m = re.search(r'^# (.+)$', body_md, flags=re.M)
    title = title_m.group(1) if title_m else slug
    pr_html = '<p style="margin-top:20px"><span class="pr">広告（PR）を含む記事です</span></p>' if pr else ''
    _h = md2html(body_md)
    _h2s = re.findall(r'<h2>(.*?)</h2>', _h)
    if len(_h2s) >= 3:
        _n = [0]
        def _addid(m):
            _n[0] += 1
            return f'<h2 id="s{_n[0]}">{m.group(1)}</h2>'
        _h = re.sub(r'<h2>(.*?)</h2>', _addid, _h)
        _toc = '<nav class="toc"><b>目次</b><ol>' + ''.join(f'<li><a href="#s{i + 1}">{t}</a></li>' for i, t in enumerate(_h2s)) + '</ol></nav>'
        _h = re.sub(r'(</h1>)', r'\1' + _toc, _h, count=1)
    _mini = '<div class="cta-mini"><p>読む前に、自分の状態で使える手法だけを確認できます。</p><a class="btn btn-cta" href="../index.html#check">状態チェック</a></div>'
    _h = re.sub(r'(</h1>)', r'\1' + _mini, _h, count=1) if '<h1>' in _h else _mini + _h
    _byline = '<div class="byline">運営・編集：合同会社MELSY。この記事の数値と条件は、各社の公式ページで確認した内容に基づきます。掲載の基準と確認の方法は<a href="../about.html">運営者情報</a>に書いています。</div>'
    body = pr_html + _h + CTA_BOX + _byline + rel_box(slug) + '<p><a href="../index.html">トップへ戻る</a></p>'
    desc_m = re.search(r'メタディスクリプション：(.+)', parts[0]) if len(parts) > 1 else None
    desc = desc_m.group(1).strip() if desc_m else title
    _full_md = md
    def _iso(kind):
        m = re.search(kind + r'：(\d{4})年(\d{1,2})月(\d{1,2})日', _full_md)
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}' if m else '2026-11-17'
    _org = {'@type': 'Organization', 'name': '合同会社MELSY', 'url': 'https://melsy.info/'}
    _crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'トップ', 'item': BASE_URL},
        {'@type': 'ListItem', 'position': 2, 'name': '記事一覧', 'item': BASE_URL + 'articles/'},
        {'@type': 'ListItem', 'position': 3, 'name': title, 'item': BASE_URL + 'articles/' + slug}]}
    _lds = [{'@context': 'https://schema.org', '@type': 'Article',
             'headline': title, 'description': desc,
             'datePublished': _iso('公開日'), 'dateModified': _iso('更新日'),
             'author': _org, 'publisher': _org, 'inLanguage': 'ja',
             'mainEntityOfPage': BASE_URL + 'articles/' + slug}, _crumbs]
    _faq_m = re.search(r'## よくある質問\n(.*?)(?=\n## |\Z)', _full_md, re.S)
    if _faq_m:
        _qa = []
        for _qm in re.finditer(r'### (.+?)\n(.*?)(?=\n### |\Z)', _faq_m.group(1), re.S):
            _a = _qm.group(2).strip()
            _a = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', _a)
            _a = _a.replace('**', '')
            _a = re.sub(r'\n+', ' ', _a).strip()
            if _a:
                _qa.append({'@type': 'Question', 'name': _qm.group(1).strip(),
                            'acceptedAnswer': {'@type': 'Answer', 'text': _a}})
        if _qa:
            _lds.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': _qa})
    if slug == 'basics-2sha.html':
        _steps = ['ファクタリング会社へ申し込み、必要書類を提出します。',
                  '審査が行われます。審査の中心は、売掛先の信用と売掛金の内容です。',
                  '手数料と買取額が提示されます。契約前に、償還請求権と買戻しの特約の有無を確かめます。',
                  '契約を結びます。',
                  '買取額から手数料を引いた金額が入金されます。入金までの期間は、最短で即日から数日です。',
                  '売掛金の期日が来たら、売掛先からの入金をファクタリング会社へ支払います。']
        _lds.append({'@context': 'https://schema.org', '@type': 'HowTo',
                     'name': '2社間ファクタリングの申し込みから入金までの手順',
                     'step': [{'@type': 'HowToStep', 'position': i + 1, 'text': t} for i, t in enumerate(_steps)]})
    ld = json.dumps(_lds, ensure_ascii=False)
    with open(f'{OUT}/articles/{slug}', 'w') as f:
        f.write(page(title, body, article=True, desc=desc, ld=ld, path='articles/' + slug))
print('articles done')

last_checked = max((s['checked'] for s in services if s['checked']), default='')
recent_log = log[-5:][::-1]
log_rows = ''.join(f"<tr><td>{html.escape(r['date'])}</td><td>{html.escape(r['entity'])}</td><td>{html.escape(r['item'])}</td><td>{html.escape(r['before'])} → {html.escape(r['after'])}</td></tr>" for r in recent_log)

state_cards = [
    ('入金は来月なのに、今月の支払いが厳しい', '支払いと入金のズレへの進め方を見る', 'articles/guide-payment-gap.html'),
    ('初めての資金調達で全体像を知りたい', '初めての資金調達の進め方を見る', 'articles/guide-first-time.html'),
    ('銀行の審査に落ちた', '理由の切り分けと次の窓口を見る', 'articles/guide-rejected.html'),
    ('税金の滞納がある', '残る選択肢と最初の一手を見る', 'articles/guide-tax-arrears.html'),
    ('創業したばかりで実績が少ない', '創業直後の窓口と順番を見る', 'articles/guide-startup.html'),
    ('赤字・債務超過が続いている', '決算で決まらない系統を見る', 'articles/guide-akaji.html'),
    ('設備投資の資金を考えている', '期間のミスマッチを避ける進め方を見る', 'articles/guide-equipment.html'),
    ('補助金に採択されたが入金が先', 'つなぎ資金の進め方を見る', 'articles/guide-subsidy-bridge.html'),
    ('売掛先の入金が遅れた・倒産した', '使える制度と手当てを見る', 'articles/guide-arv-delay.html'),
    ('支払いまで数日しかない', '間に合う系統と順番を見る', 'articles/guide-urgent.html'),
    ('売掛先に知られずに資金化したい', '2社間の仕組みと条件を見る', 'articles/guide-no-notify.html'),
    ('返済の負担を軽くしたい', '借り換えと条件変更の違いを見る', 'articles/guide-refinance.html'),
    ('大きな受注が決まったが先に費用がかかる', '注文書の段階で使える系統を見る', 'articles/guide-order-received.html'),
    ('納税の期限が近いが資金が足りない', '滞納になる前の手当てを見る', 'articles/guide-tax-payment.html'),
    ('個人事業主で法人との違いを知りたい', '個人事業主の窓口と順番を見る', 'articles/guide-sole-proprietor.html'),
    ('診療報酬・介護報酬の入金が約2か月先', '報酬の債権で使える系統を見る', 'articles/guide-medical-care.html'),
    ('手形・でんさいを受け取った', '現金化の仕組みと注意点を見る', 'articles/guide-notes-receivable.html'),
    ('売掛金を早く現金化したい', 'ファクタリングの仕組みと手順を見る', 'articles/basics-2sha.html'),
    ('ファクタリングの全体像を知りたい', '種類と借入との違いを見る', 'articles/basics-factoring.html'),
    ('償還請求権のある契約を避けたい', '契約書で確かめる箇所を見る', 'articles/basics-recourse.html'),
    ('信用保証協会の仕組みを知りたい', '保証料と責任共有の考え方を見る', 'articles/basics-guarantee.html'),
    ('セーフティネット保証の認定を取りたい', '号ごとの要件と手続きを見る', 'articles/basics-safety-net.html'),
    ('手数料と速さを比べて選びたい', '2社間ファクタリングのサービス比較を見る', 'compare/ファクタリング2社間.html'),
]
cards_html = ''.join(f'<a class="state-card" href="{u}"><b>{html.escape(t)}</b><span>{html.escape(s)} →</span></a>' for t, s, u in state_cards)

method_cards = ''.join(
    f'<div class="mcard"><h3>{html.escape(m["name"])}</h3><p style="margin:0">{html.escape(m["def"])}</p>'
    f'<dl class="kv"><dt>期間</dt><dd>{html.escape(m["period"])}</dd><dt>費用</dt><dd>{html.escape(m["cost"])}</dd></dl>'
    f'<p style="margin:6px 0 0"><a href="methods/{mslug(m["id"])}.html">この手法の詳細とサービス一覧 →</a></p></div>'
    for m in methods)

methods_js = json.dumps([{k: m[k] for k in ('id', 'name', 'def', 'cost', 'docs', 'period', 'fit', 'unfit', 'target', 'maxDays', 'minDays', 'needsArv', 'taxCaution')} for m in methods], ensure_ascii=False)
services_js = json.dumps([{k: s[k] for k in ('id', 'name', 'entity', 'method', 'fee_lo', 'fee_hi', 'speed', 'amt_lo', 'amt_hi', 'target', 'online', 'form', 'score')} for s in services if s.get('status') != '廃業・撤退'], ensure_ascii=False)
method_names = {m['id']: m['name'] for m in methods}
method_options = ''.join(f'<option value="{mid}">{html.escape(n)}</option>' for mid, n in sorted(method_names.items()))

JS = """
const METHODS = __METHODS__;
const SERVICES = __SERVICES__;
const MNAMES = __MNAMES__;
const GUIDE = {'M13':'articles/basics-2sha.html','M14':'articles/basics-2sha.html'};
const COMPARE = {'M13':'compare/ファクタリング2社間.html','M14':'compare/ファクタリング3社間.html'};
const STEPS = [
{key:'ent', q:'事業の形はどちらですか', opts:[['corp','法人'],['sole','個人事業主']]},
{key:'days', q:'資金が要るのは、いつまでですか', opts:[['1','今日〜明日','支払いが目前に迫っている'],['7','今週中'],['30','今月中'],['999','急がない','じっくり比べたい']]},
{key:'amt', q:'希望する金額はどれくらいですか', opts:[['u100','100万円未満'],['u500','100万〜500万円'],['u3000','500万〜3,000万円'],['over','3,000万円を超える']]},
{key:'age', q:'創業からの期間はどれくらいですか', opts:[['new','創業前・開業して1年未満'],['mid','1年〜3年'],['old','3年を超える'],['unknown','分からない']]},
{key:'docs2', q:'決算書（直近2期分）を、今すぐ提出できますか', opts:[['two','2期分とも出せる'],['one','1期分だけ'],['none-yet','まだ決算を迎えていない'],['cannot','出せない']]},
{key:'fin', q:'決算の状態はどれに近いですか', opts:[['stable','黒字で安定している'],['akaji','赤字が続いている'],['over','債務超過がある'],['unknown','分からない']]},
{key:'tax', q:'税金・社会保険料の滞納はありますか', opts:[['none','ない'],['install','あるが、分納している'],['yes','ある']]},
{key:'sales', q:'直近3か月の売上は、前年同期と比べてどうですか', opts:[['down','5%以上減っている'],['same','ほぼ同じ'],['up','増えている'],['unknown','分からない']]},
{key:'biz', q:'業種はどれに近いですか', opts:[['medical','医療・介護・調剤'],['construction','建設'],['transport','運送'],['manufacturing','製造'],['wholesale','卸・小売'],['food','飲食・サービス'],['other','その他']]},
{key:'asset', q:'担保にできる不動産などの資産はありますか', opts:[['yes','ある'],['no','ない']]},
{key:'loan', q:'借入の状況はどれに近いですか', opts:[['first','初めて借りる'],['has','借入がある'],['rejected','審査に落ちたことがある']]},
{key:'cp', q:'売掛金（入金待ちの請求書）の相手は誰ですか', opts:[['corp','法人'],['sole','個人事業主'],['person','個人・一般消費者'],['public','公的機関','国保連・支払基金など'],['none','売掛金はない']]},
{key:'inv', q:'その請求書の状態はどれですか', when:() => hasArv(), opts:[['confirmed','金額と期日が確定し、検収も済んでいる'],['issued','請求はしたが、確定していない部分がある'],['order','注文書・出来高の段階で、まだ請求書がない']]},
{key:'invdays', q:'売掛金の支払期日まで、あとどれくらいですか', when:() => hasArv(), opts:[['d30','30日以内'],['d70','31〜70日'],['d180','71日〜6か月'],['over','6か月を超える']]}
];
const QMAP = {}; for(const s of STEPS) QMAP[s.key] = s;
const TIER = {T1:['M01','M02','M03','M04','M05','M06'], T2:['M07','M08','M09','M12','M18','M19','M20','M21','M22','M23','M24'], T3:['M10','M11','M13','M14','M15','M16','M17']};
const TIER_NAME = {T1:'上位：公的・銀行系（費用は低いが、審査は厳しい）', T2:'中位：担保・ノンバンク系', T3:'下位：売掛金の系統（早いが、費用は高め）'};
const TIER_SHORT = {T1:'上位（公的・銀行系）', T2:'中位（担保・ノンバンク系）', T3:'下位（売掛金の系統）'};
const TAX_NG = ['M02','M03','M04','M05','M06','M18','M19','M20'];
const METHOD_NOTES = {
M05: '要件：商工会議所等の経営指導を原則6か月以上受けていること、同じ地区で1年以上の事業歴、税金の完納などが必要です。',
M06: '市区町村長の認定が必要です（5号は指定業種で最近3か月の売上が前年同期比5%以上減少、4号は災害の地域指定で20%以上減少など）。認定は融資を確約するものではありません。'
};
const FIN_CAUTION = ['M01','M02','M03'];
const BAND_LO = {u100: 0, u500: 100, u3000: 500, over: 3000};
const DOCS_COMMON = ['代表者の本人確認書類', '決算書または確定申告書（直近2期分）', '事業用口座の入出金明細（直近3〜4か月分）', '法人の場合：履歴事項全部証明書・印鑑証明書'];
function amtHiWan(s){
if(!s.amt_hi) return null;
if(s.amt_hi.includes('上限なし')) return Infinity;
let total = 0, found = false;
const oku = s.amt_hi.match(/([\d.]+)\s*億/);
if(oku){ total += parseFloat(oku[1]) * 10000; found = true;}
const man = s.amt_hi.replace(/[\d.]+\s*億/, '').match(/([\d,]+)\s*万/);
if(man){ total += parseFloat(man[1].replace(/,/g, '')); found = true;}
if(found) return total;
const yen = s.amt_hi.match(/([\d,]+)\s*円/);
if(yen) return parseFloat(yen[1].replace(/,/g, '')) / 10000;
return null;
}
const ans = {}; const EVAL = {}; const hist = [];
let stageIdx = 0, qIdx = 0, branchTierNow = null, flowGen = 0;
function hasArv(){ return!!ans.cp && ans.cp!== 'none';}
function bSkipped(){ return parseInt(ans.days || '999', 10) <= 7;}
const STAGE_DEFS = [
{id:'A', label:'入口の確認', tier:null, qs:['ent','days','amt']},
{id:'B', label:'上位の手法（公的・銀行系）の確認', tier:'T1', skipIf:() => bSkipped(), qs:['age','docs2','fin','tax','sales','biz']},
{id:'C', label:'担保とノンバンク系の確認', tier:'T2', qs:['asset','loan','fin','tax']},
{id:'D', label:'売掛金の系統の確認', tier:'T3', qs:['biz','cp','inv','invdays']}
];
function stageQs(st){
return st.qs.map(k => QMAP[k]).filter(q => {
if(st.id === 'C' && (q.key === 'fin' || q.key === 'tax')) return bSkipped();
if(st.id === 'D' && q.key === 'biz') return bSkipped();
if(q.when) return q.when();
return true;
});
}
function askedCount(){ let n = 0; for(let i = 0; i < stageIdx; i++){ if(!(STAGE_DEFS[i].skipIf && STAGE_DEFS[i].skipIf())) n += stageQs(STAGE_DEFS[i]).length;} return n + qIdx;}
function renderStep(){
branchTierNow = null;
const st = STAGE_DEFS[stageIdx];
if(st.skipIf && st.skipIf()){ finishStage(); return;}
const qs = stageQs(st);
if(qIdx >= qs.length){ finishStage(); return;}
const s = qs[qIdx];
document.getElementById('step-label').textContent = st.label + '（質問 ' + (askedCount() + 1) + '）';
document.getElementById('progress-bar').style.width = ((stageIdx + qIdx / Math.max(qs.length, 1)) / STAGE_DEFS.length * 100) + '%';
const q = document.getElementById('wiz-q');
q.textContent = s.q;
const box = document.getElementById('wiz-opts');
box.innerHTML = s.opts.map(o =>
'<button class="opt' + (ans[s.key] === o[0]? ' sel': '') + '" data-val="' + o[0] + '">' + o[1] + (o[2]? '<span class="sub">' + o[2] + '</span>': '') + '</button>').join('');
box.querySelectorAll('.opt').forEach(b => b.addEventListener('click', () => pick(s.key, b.dataset.val)));
document.getElementById('wiz-back').style.visibility = hist.length === 0? 'hidden': 'visible';
}
function pick(key, val){
hist.push([stageIdx, qIdx]);
ans[key] = val;
if(key === 'cp' && val === 'none'){ delete ans.inv; delete ans.invdays;}
renderStep();
const g = flowGen;
setTimeout(() => { if(g !== flowGen) return; qIdx++; renderStep();}, 200);
}
function backStep(){
if(branchTierNow){ branchTierNow = null; renderStep(); return;}
const prev = hist.pop();
if(!prev) return;
stageIdx = prev[0]; qIdx = prev[1];
renderStep();
}
function finishStage(){
const st = STAGE_DEFS[stageIdx];
if(st.tier){
if(st.skipIf && st.skipIf()){
EVAL[st.tier] = {fit: [], maybe: [], unfit1: [], unfit2: METHODS.filter(m => TIER[st.tier].includes(m.id)).map(m => [m, '入金までの期間の目安が「' + m.period + '」で、必要な時期に間に合いません。急ぎの場合は、下位の系統が入口になります。']), skipped: true};
} else {
EVAL[st.tier] = evaluate(TIER[st.tier]);
}
for(let i = stageIdx + 1; i < STAGE_DEFS.length; i++){ const t = STAGE_DEFS[i].tier; if(t) delete EVAL[t];}
const ev = EVAL[st.tier];
if(stageIdx < STAGE_DEFS.length - 1 &&!ev.skipped && (ev.fit.length + ev.maybe.length) > 0){ renderBranch(st.tier); return;}
}
nextStage();
}
function nextStage(){ stageIdx++; qIdx = 0; if(stageIdx >= STAGE_DEFS.length){ showResult(false); return;} renderStep();}
function renderBranch(tier){
branchTierNow = tier;
const ev = EVAL[tier];
const cands = ev.fit.concat(ev.maybe);
document.getElementById('step-label').textContent = TIER_SHORT[tier] + 'の確認が終わりました';
document.getElementById('progress-bar').style.width = ((stageIdx + 1) / STAGE_DEFS.length * 100) + '%';
document.getElementById('wiz-q').textContent = 'ここまでの確認で、' + TIER_SHORT[tier] + 'に候補が ' + cands.length + ' 件あります。';
const box = document.getElementById('wiz-opts');
box.innerHTML = '<div class="panel" style="text-align:left;margin-bottom:14px"><b>候補</b><ul class="why-list">'
+ cands.map(m => '<li>' + m.name + (signals(m) >= 1 &&!m._maybe? '（可能性が高い）': '') + (m._maybe? '（最短では間に合うが確実ではない）': '') + '</li>').join('')
+ '</ul><p class="note" style="margin:0">この候補で結果を見るか、下位の手法まで調べるか選んでください。下位は費用が高くなる代わりに、審査の形が違います。状況に合う手法が下位にしかない場合は、質問に答えるほど絞り込めます。</p></div>'
+ '<button class="opt" data-act="result">この候補で結果を見る</button>'
+ '<button class="opt" data-act="deeper">下位の手法まで調べる（質問が続きます）</button>';
box.querySelectorAll('[data-act]').forEach(b => b.addEventListener('click', () => { if(b.dataset.act === 'result') showResult(true); else { branchTierNow = null; nextStage();}}));
document.getElementById('wiz-back').style.visibility = 'visible';
}
function resumeCascade(){
flowGen++;
for(let i = 0; i < STAGE_DEFS.length; i++){ const t = STAGE_DEFS[i].tier; if(t &&!EVAL[t]){ stageIdx = i; qIdx = 0; break;}}
document.getElementById('wiz').style.display = 'block';
document.getElementById('result').style.display = 'none';
renderStep();
}
function restart(){ flowGen++; stageIdx = 0; qIdx = 0; branchTierNow = null; hist.length = 0; for(const k in ans) delete ans[k]; for(const k in EVAL) delete EVAL[k]; document.getElementById('wiz').style.display = 'block'; document.getElementById('result').style.display = 'none'; renderStep();}
let SHEET_DATA = null;
function saveSheet(){ try{ sessionStorage.setItem('shikin_sheet', JSON.stringify(SHEET_DATA));}catch(e){}}
function submitLead(){ saveSheet(); setTimeout(() => { location.href = 'sheet.html';}, 900); return true;}
function svcOf(mid){
const lo = BAND_LO[ans.amt] || 0;
return SERVICES.filter(s => {
if(s.method!== mid) return false;
if(!lo) return true;
const hi = amtHiWan(s);
return hi === null || hi >= lo;
});
}
function evaluate(ids){
const maxD = parseInt(ans.days, 10);
let fit = [], maybe = [], unfit1 = [], unfit2 = [];
for(const m of METHODS){ m._maybe = false; m._invDemote = false;}
for(const m of METHODS){
if(!ids.includes(m.id)) continue;
if(ans.tax && ans.tax!== 'none' && TAX_NG.includes(m.id)) unfit1.push([m, '税金・社会保険料の滞納がある場合、納税証明書の提出が必要な公的な融資や補助は対象外になります。分納中の場合も、同じ扱いの制度が大半です。']);
else if(m.id === 'M16' &&!(ans.biz === 'medical' || ans.cp === 'public')) unfit1.push([m, '診療・介護・調剤報酬の債権を使う手法です。医療・介護以外の事業では使えません。']);
else if(m.needsArv && ans.cp &&!hasArv()) unfit1.push([m, '売掛金（請求書）が必要な手法です。']);
else if(m.needsArv && ans.cp === 'person' && m.id!== 'M15') unfit1.push([m, '売掛先が個人・一般消費者の請求書は、多くのファクタリング会社で対象外です。']);
else if(m.id === 'M09' && ans.asset === 'no') unfit1.push([m, '不動産などの担保が必要です。']);
else if(m.id === 'M10' && ans.asset === 'no' && ans.cp &&!hasArv()) unfit1.push([m, '担保にできる資産や売掛金が必要です。']);
else if(m.id === 'M01' && ans.age === 'new') unfit1.push([m, '銀行融資（プロパー）は複数期の実績が前提です。創業期は公庫と保証協会の創業向けが入口になります。']);
else if(m.id === 'M23' && ans.age === 'new') unfit1.push([m, '私募債は、発行できる会社の条件（規模と実績）が決まっています。']);
else if(ans.ent === 'sole' &&!m.target.includes('個人事業主')) unfit1.push([m, '対象が法人中心の手法です。']);
else if(['M13','M14','M17'].includes(m.id) && ans.invdays === 'over') unfit2.push([m, '売掛金の支払期日が6か月を超える債権は、対象外とする会社が多いためです。']);
else if(m.maxDays <= maxD) fit.push(m);
else if(m.minDays <= maxD) maybe.push(m);
else unfit2.push([m, '入金までの期間の目安が「' + m.period + '」で、必要な時期に間に合いません。']);
}
for(const m of fit){
if(['M13','M14'].includes(m.id) && hasArv() && ans.inv && ans.inv!== 'confirmed'){ m._maybe = true; m._invDemote = true; maybe.push(m);}
}
fit = fit.filter(m =>!m._invDemote);
for(const m of maybe) m._maybe = true;
return {fit: fit, maybe: maybe, unfit1: unfit1, unfit2: unfit2};
}
const DAYS_LABEL = {'1':'今日〜明日', '7':'今週中', '30':'今月中', '999':'急がない'};
const BAND_LABEL = {u100:'100万円未満', u500:'100万〜500万円', u3000:'500万〜3,000万円', over:'3,000万円超'};
function signals(m){
if(FIN_CAUTION.includes(m.id) && (ans.fin === 'akaji' || ans.fin === 'over')) return 0;
let n = 0;
if(m.needsArv && (ans.cp === 'corp' || ans.cp === 'public') && ans.inv === 'confirmed') n++;
if(m.id === 'M16' && ans.cp === 'public') n++;
if(m.id === 'M06' && ans.sales === 'down') n++;
if(['M01','M02','M03','M04','M07'].includes(m.id) && ans.docs2 === 'two') n++;
if((m.id === 'M09' || m.id === 'M10') && ans.asset === 'yes') n++;
if(m.id === 'M15' && ans.inv === 'order') n++;
if(ans.fin === 'stable' && FIN_CAUTION.includes(m.id)) n++;
return n;
}
function reasons(m, isMaybe){
const rs = [];
if(isMaybe) rs.push('期限：最短では必要な時期（' + DAYS_LABEL[ans.days] + '）に間に合いますが、確実ではありません。期間の目安は「' + m.period + '」です。');
else rs.push('期限：入金までの期間の目安は「' + m.period + '」で、必要な時期（' + DAYS_LABEL[ans.days] + '）に間に合います。');
if(m._invDemote) rs.push('債権の状態：金額と期日が確定した債権を条件とする会社では申し込めません。未確定でも扱う会社に限られます。');
if(m.needsArv && ans.cp === 'corp') rs.push('売掛先：法人宛の請求書は、審査の中心が申込者ではなく売掛先の信用になる系統です。');
if(m.needsArv && ans.cp === 'public') rs.push('売掛先：公的機関宛の債権は未回収のリスクが低く、審査が通りやすい系統です。');
if(m.needsArv && ans.cp === 'sole') rs.push('売掛先：個人事業主宛の請求書でも扱う会社に限られます。');
if(m.needsArv && ans.inv === 'confirmed') rs.push('債権の状態：金額と期日が確定し検収も済んだ請求書は、買い取る側の条件に合いやすい状態です。');
if(m.id === 'M15' && ans.inv === 'order') rs.push('債権の状態：注文書・出来高の段階でも申し込める系統です。請求書の発行を待つ必要がありません。');
if(m.id === 'M06' && ans.sales === 'down') rs.push('売上：直近3か月の売上が前年同期比で5%以上減っている場合、セーフティネット保証5号の認定要件に当たる可能性があります。');
if(['M01','M02','M03','M04','M07'].includes(m.id) && ans.docs2 === 'two') rs.push('書類：決算書2期分をすぐ出せる状態は、審査を早く始められます。');
if(['M13','M14'].includes(m.id) && ans.docs2 && ans.docs2!== 'two') rs.push('書類：決算書がそろっていなくても、通帳の入出金明細で審査する会社があります（使える枠に上限がある場合があります）。');
if((m.id === 'M09' || m.id === 'M10') && ans.asset === 'yes') rs.push('担保：担保にできる資産があるため、金額の枠と条件の幅が広がります。');
if(ans.age === 'new' && (m.id === 'M03' || m.id === 'M02')) rs.push('創業：創業期向けに設計された制度です。実績がなくても、計画と自己資金で判断されます。');
if(ans.fin === 'stable' && FIN_CAUTION.includes(m.id)) rs.push('決算：黒字で安定しており、決算内容の審査が中心の手法でも進められます。');
if((ans.fin === 'akaji' || ans.fin === 'over') && ['M09','M10','M13','M14','M15','M16','M17'].includes(m.id)) rs.push('決算：決算が弱くても、不動産や売掛金という別の裏付けで進める系統です。');
if(ans.loan === 'rejected' && ['M09','M10','M13','M14','M15','M16','M17'].includes(m.id)) rs.push('審査の形：銀行の審査に落ちたことがあっても、審査の中心が決算ではない系統です。');
if(ans.loan === 'first' && (m.id === 'M02' || m.id === 'M03')) rs.push('借入の実績：初めての借入でも、実績づくりの入口として使われる制度です。');
const n = svcOf(m.id).length;
if(n > 0) rs.push('金額：希望の帯（' + BAND_LABEL[ans.amt] + '）に公表条件が合う候補が' + n + '件あります。');
if(m.fit) rs.push('手法の向く状態：' + m.fit);
return rs;
}
function cardHtml(m, isA){
const svcs = svcOf(m.id).slice().sort((a,b) => (parseInt(b.score)||0) - (parseInt(a.score)||0));
let h = '<div class="mcard"><h3>' + m.name + (isA? ' <span class="badge">可能性が高い</span>': '') + (m._maybe? ' <span class="badge low">最短では間に合うが確実ではない</span>': '') + '</h3><p style="margin:0">' + m.def + '</p>';
h += '<dl class="kv"><dt>費用の目安</dt><dd>' + m.cost + '</dd><dt>入金まで</dt><dd>' + m.period + '</dd><dt>必要書類</dt><dd>' + m.docs + '</dd></dl>';
const rs = reasons(m,!!m._maybe);
if(rs.length) h += '<p style="margin:10px 0 2px"><b>おすすめの理由</b></p><ul class="why-list">' + rs.map(r => '<li>' + r + '</li>').join('') + '</ul>';
if((ans.fin === 'akaji' || ans.fin === 'over') && FIN_CAUTION.includes(m.id)){
const finNote = (ans.fin === 'over' && m.id === 'M01')
? '注意：債務超過の場合、決算内容が審査の中心になる銀行融資は特に厳しくなります。不動産担保や売掛金の系統も並行して検討してください。'
: '注意：赤字や債務超過が続いている場合、この手法は決算内容の審査が中心になるため、結果が厳しくなることがあります。';
h += '<p class="note"><b>' + finNote + '</b></p>';
}
if(METHOD_NOTES[m.id]) h += '<p class="note">' + METHOD_NOTES[m.id] + '</p>';
if(ans.age === 'new' && m.id === 'M02') h += '<p class="note">創業の場合は、創業関連保証（限度額3,500万円、100%保証）が入口になります。</p>';
if(ans.age === 'new' && m.id === 'M05') h += '<p class="note">マル経融資は、同じ地区で1年以上事業を続けていることが要件です。</p>';
if(m.id === 'M02' && (ans.docs2 === 'cannot' || ans.docs2 === 'none-yet')) h += '<p class="note">注意：信用保証協会の申し込みでは、受付印のある決算書2期分が原則として必要です。今すぐ出せない場合は、まず用意できるかを確認してください。</p>';
if(m.id === 'M07' && ans.docs2 && ans.docs2!== 'two') h += '<p class="note">注意：決算書2期分を求める会社があります。1期分だけ、または出せない場合は、申し込める会社が絞られます。</p>';
if(m.id === 'M06' && ans.sales && ans.sales!== 'down') h += '<p class="note">セーフティネット保証5号は、指定業種で直近の売上が減っていることが認定の要件です。要件に当たらない場合は、一般の保証枠が入口になります。</p>';
if(m.id === 'M16' && ans.tax && ans.tax!== 'none') h += '<p class="note">報酬債権の専門会社には、税金の滞納があっても審査に影響しないと案内する会社があります。条件は会社ごとに異なるため、見積もりで確認してください。</p>';
for(const s of svcs.slice(0,3)){
h += '<div class="svc"><div><b><a href="services/' + s.id.toLowerCase() + '.html">' + s.name + '</a></b>（' + s.entity + '）<br>手数料 ' + feeText(s) + '／入金 ' + (s.speed || '―') + '／公表している金額 ' + amtText(s) + '</div><span class="badge' + ((parseInt(s.score)||0) >= 3? '': ' low') + '">透明性 ' + (s.score || '―') + ' / 5</span></div>';
}
if(svcs.length) h += '<p class="note">金額は各社が公表している範囲で、調達できる金額の約束ではありません。手数料の上限が「非公表」の会社は、見積もりで確認が必要です。</p>';
h += '<div class="cta-row">';
if(svcs.length) h += '<button class="btn btn-cta btn-sm" data-goto="' + m.id + '">候補 ' + svcs.length + '件を比べる</button>';
if(COMPARE[m.id]) h += '<a class="btn btn-sub btn-sm" href="' + COMPARE[m.id] + '">比較の記事を読む</a>';
if(GUIDE[m.id]) h += '<a class="btn btn-ghost btn-sm" href="' + GUIDE[m.id] + '">仕組みを知る</a>';
h += '</div></div>';
return h;
}
function showResult(partial){
const order = ['T1','T2','T3'];
const shownByTier = {}; let totalShown = 0, totalA = 0;
for(const t of order){
if(!EVAL[t]) continue;
const ev = EVAL[t];
const all = ev.fit.concat(ev.maybe);
for(const m of all) m._sig = signals(m);
const a = all.filter(m =>!m._maybe && m._sig >= 1).sort((x,y) => y._sig - x._sig);
const b = all.filter(m =>!m._maybe && m._sig < 1);
const c = all.filter(m => m._maybe);
shownByTier[t] = a.concat(b, c).map(m => ({m: m, isA: a.includes(m)}));
totalShown += all.length; totalA += a.length;
}
let h = '<div class="result-head"><b>絞り込みの過程（上位から順に確認しました）</b><br>全手法 ' + METHODS.length + '件';
for(const t of order){
if(EVAL[t]){
const ev = EVAL[t];
if(ev.skipped) h += '<br>→ ' + TIER_SHORT[t] + '：期限（' + DAYS_LABEL[ans.days] + '）に間に合わないため、対象外です';
else h += '<br>→ ' + TIER_SHORT[t] + '：候補 ' + (ev.fit.length + ev.maybe.length) + '件／外れた手法 ' + (ev.unfit1.length + ev.unfit2.length) + '件';
} else {
h += '<br>→ ' + TIER_SHORT[t] + '：まだ確認していません';
}
}
h += '<br><b>提示する手法は ' + totalShown + '件、そのうち「可能性が高い」のは ' + totalA + '件です。</b>上位の系統から順に並べました。外れた手法も、段階ごとに理由つきで下に置きました。</div>';
h += '<div class="panel" style="margin-bottom:20px"><b>まず用意する書類（複数社で使い回せます）</b>'
+ '<ul class="why-list">' + DOCS_COMMON.map(d => '<li>' + d + '</li>').join('') + '</ul>'
+ '<p class="note" style="margin:0">申し込み先ごとに違う書類をそろえ直す手間が、締切を逃す原因になります。共通分は先にそろえてください。現状シートにもこの一覧を載せます。</p></div>';
const ENT_LABEL = {corp:'法人', sole:'個人事業主'};
const BIZ_LABEL = {medical:'医療・介護・調剤', construction:'建設', transport:'運送', manufacturing:'製造', wholesale:'卸・小売', food:'飲食・サービス', other:'その他'};
const CP_LABEL = {corp:'法人', sole:'個人事業主', person:'個人・一般消費者', public:'公的機関', none:'売掛金はない'};
const INV_LABEL = {confirmed:'確定し検収済み', issued:'請求済みだが未確定の部分がある', order:'注文書・出来高の段階'};
const INVDAYS_LABEL = {d30:'30日以内', d70:'31〜70日', d180:'71日〜6か月', over:'6か月を超える'};
const DOCS2_LABEL = {two:'2期分とも出せる', one:'1期分だけ', 'none-yet':'まだ決算を迎えていない', cannot:'出せない'};
const SALES_LABEL = {down:'5%以上減っている', same:'ほぼ同じ', up:'増えている', unknown:'分からない'};
const TAX_LABEL = {none:'ない', install:'あるが分納している', yes:'ある'};
const LOAN_LABEL = {first:'初めて借りる', has:'借入がある', rejected:'審査に落ちたことがある'};
const FIN_LABEL = {stable:'黒字で安定している', akaji:'赤字が続いている', over:'債務超過がある', unknown:'分からない'};
const AGE_LABEL = {new:'創業前・開業して1年未満', mid:'1年〜3年', old:'3年を超える', unknown:'分からない'};
const stateRows = [['事業の形', ENT_LABEL[ans.ent] || ''], ['資金が要る時期', DAYS_LABEL[ans.days] || ''], ['希望する金額', BAND_LABEL[ans.amt] || '']];
if(ans.age) stateRows.push(['創業からの期間', AGE_LABEL[ans.age] || '']);
if(ans.docs2) stateRows.push(['決算書2期分', DOCS2_LABEL[ans.docs2] || '']);
if(ans.fin) stateRows.push(['決算の状態', FIN_LABEL[ans.fin] || '']);
if(ans.tax) stateRows.push(['税金・社会保険料の滞納', TAX_LABEL[ans.tax] || '']);
if(ans.sales) stateRows.push(['直近3か月の売上（前年同期比）', SALES_LABEL[ans.sales] || '']);
if(ans.biz) stateRows.push(['業種', BIZ_LABEL[ans.biz] || '']);
if(ans.asset) stateRows.push(['担保にできる資産', ans.asset === 'yes'? 'ある': 'ない']);
if(ans.loan) stateRows.push(['借入の状況', LOAN_LABEL[ans.loan] || '']);
if(ans.cp){ stateRows.push(['売掛先', CP_LABEL[ans.cp] || '']); if(hasArv()){ stateRows.push(['請求書の状態', INV_LABEL[ans.inv] || '']); stateRows.push(['売掛金の支払期日まで', INVDAYS_LABEL[ans.invdays] || '']);}}
const shownFlat = [];
for(const t of order){ if(shownByTier[t]) for(const x of shownByTier[t]) shownFlat.push(x);}
const shownData = shownFlat.map(x => ({name: x.m.name, period: x.m.period, cost: x.m.cost, maybe:!!x.m._maybe, tierA: x.isA, svcs: svcOf(x.m.id).slice(0,3).map(s => s.name + '（' + s.entity + '）')}));
const unfitNames = [];
for(const t of order){ if(EVAL[t]) for(const x of EVAL[t].unfit1.concat(EVAL[t].unfit2)) unfitNames.push(x[0].name);}
const pendingNames = [];
for(const t of order){ if(!EVAL[t]) for(const id of TIER[t]) pendingNames.push((METHODS.find(m => m.id === id) || {}).name);}
SHEET_DATA = {date: new Date().toLocaleDateString('ja-JP'), state: stateRows, shown: shownData, unfit: unfitNames, docs: DOCS_COMMON, pending: pendingNames};
const sumText = '' + stateRows.map(r => r[0] + '：' + r[1]).join('／')
+ ' ' + shownData.map(d => d.name + '：' + (d.svcs.join('、') || '候補なし')).join('／')
+ ' ' + unfitNames.join('、') + (pendingNames.length? ' ' + pendingNames.join('、'): '');
h += '<div class="lead-panel" id="lead"><h3>結果と現状をまとめた「現状シート」を作る</h3>'
+ '<p>この結果に、あなたの現状（期限・希望額・売掛先・決算の状態）と、用意する書類の一覧を整理して1枚にまとめたシートです。提示した手法と候補の会社、外れた手法も載せるので、各社の担当者にそのまま渡せて、相談が早く進みます。作成は無料です。</p>'
+ '<form class="lead-form" action="https://docs.google.com/forms/d/e/1FAIpQLSf48qJWe-muxLveesTBzHgfHhrD5b7jgVHew2RjvRThgWtPuA/formResponse" method="POST" target="gform_sink" onsubmit="return submitLead()">'
+ '<input type="hidden" name="entry.18224998" value="' + sumText.replace(/"/g, '”') + '">'
+ '<label>会社名<span class="req">必須</span><input type="text" name="entry.1873836302" required autocomplete="organization"></label>'
+ '<label>担当者名<span class="req">必須</span><input type="text" name="entry.315891329" required autocomplete="name"></label>'
+ '<label>メールアドレス<span class="req">必須</span><input type="email" name="entry.1306356804" required autocomplete="email"></label>'
+ '<label>電話番号（任意）<input type="tel" name="entry.757213249" autocomplete="tel"></label>'
+ '<div class="wide"><button class="btn btn-cta btn-hero" type="submit" style="width:100%">現状シートを作成する</button>'
+ '<p class="lead-note">送信すると、その場でシートが表示されます（印刷・保存できます）。入力した連絡先は、シートの送付と、資金調達に関する案内にだけ使います。詳しくは<a href="privacy.html" style="color:#fff">プライバシーポリシー</a>をご覧ください。</p></div>'
+ '</form></div>';
for(const t of order){
if(!shownByTier[t]) continue;
h += '<h3 style="margin:26px 0 12px">' + TIER_NAME[t] + '</h3>';
for(const x of shownByTier[t]) h += cardHtml(x.m, x.isA);
}
for(const t of order){
if(!EVAL[t]) continue;
const ev = EVAL[t];
if(ev.unfit1.length){
h += '<h3 style="margin-top:30px">' + TIER_SHORT[t] + 'で外れた手法（絶対条件・' + ev.unfit1.length + '件）</h3>';
for(const [m, r] of ev.unfit1) h += '<details class="unfit"><summary>' + m.name + '</summary><p>' + r + '</p></details>';
}
if(ev.unfit2.length){
h += '<h3 style="margin-top:30px">' + TIER_SHORT[t] + 'で外れた手法（期限・' + ev.unfit2.length + '件）</h3>';
for(const [m, r] of ev.unfit2) h += '<details class="unfit"><summary>' + m.name + '</summary><p>' + r + '</p></details>';
}
}
if(partial && pendingNames.length){
h += '<div class="panel" style="margin-top:26px"><b>まだ確認していない手法（' + pendingNames.length + '件）</b><p style="margin:6px 0">' + pendingNames.join('、') + '</p><p class="note" style="margin:0 0 10px">下位の系統は、上の系統で候補が見つからなかった場合に効きます。続きの質問に答えると、この手法も含めて絞り込めます。</p><button class="btn btn-cta" onclick="resumeCascade()">続きの質問に答える</button></div>';
}
h += '<div class="cta-row"><button class="btn btn-sub" onclick="restart()">条件を変えて見直す</button><a class="btn btn-ghost" href="#search">サービス一覧から探す</a></div>';
h += '<p class="note">この結果は一般的な情報の提示です。個別の可否は各社の審査で決まります。</p>';
document.getElementById('wiz').style.display = 'none';
const r = document.getElementById('result');
r.innerHTML = h; r.style.display = 'block';
r.querySelectorAll('[data-goto]').forEach(b => b.addEventListener('click', () => gotoSearch(b.dataset.goto)));
document.getElementById('check').scrollIntoView({behavior:'smooth'});
}
function gotoSearch(mid){
document.getElementById('f-method').value = mid;
runSearch();
document.getElementById('search').scrollIntoView({behavior:'smooth'});
}
function feeText(s){
  const lo = (s.fee_lo || '').trim(), hi = (s.fee_hi || '').trim();
  if(lo && hi) return lo === hi ? lo : lo + '〜' + hi;
  if(hi) return hi;
  if(lo) return lo + '〜';
  return '非公表';
}
function amtText(s){
  const bad = v => !v || v === '―' || v === '—' || v === '-';
  const lo = (s.amt_lo || '').trim(), hi = (s.amt_hi || '').trim();
  if(!bad(lo) && !bad(hi)) return lo + '〜' + hi;
  if(!bad(hi)) return hi;
  if(!bad(lo)) return lo + '〜';
  return '―';
}
function scoreBadge(s){ const v = parseInt(s) || 0; return '<span class="badge' + (v >= 3 ? '' : ' low') + '">透明性 ' + (s || '―') + '</span>'; }
let lastRows = [], shownCount = 15;
function runSearch(){
  const mid = document.getElementById('f-method').value;
  const tgt = document.getElementById('f-target').value;
  const online = document.getElementById('f-online').checked;
  const hi = document.getElementById('f-score').checked;
  const form = document.getElementById('f-form').value;
  lastRows = SERVICES.filter(s =>
    (!mid || s.method === mid) &&
    (!tgt || s.target.includes(tgt)) &&
    (!online || s.online.includes('あり') || s.online.includes('可')) &&
    (!hi || (parseInt(s.score) || 0) >= 3) &&
    (!form || s.form === form));
  shownCount = 15;
  renderRows();
}
function renderRows(){
  let h = '<p><b>' + lastRows.length + '件</b>が該当します</p>';
  if(lastRows.length){
    h += '<div class="svc-cards">';
    for(const s of lastRows.slice(0, shownCount)){
      h += '<div class="svc-card"><div class="svc-top"><b><a href="services/' + s.id.toLowerCase() + '.html">' + s.name + '</a></b>' + scoreBadge(s.score) + '</div>'
        + '<div class="svc-ent">' + s.entity + '｜' + (MNAMES[s.method] || s.method) + (s.form ? '｜' + s.form : '') + '</div>'
        + '<dl class="svc-kv"><div><dt>手数料</dt><dd>' + feeText(s) + '</dd></div>'
        + '<div><dt>入金の速さ</dt><dd>' + (s.speed || '―') + '</dd></div>'
        + '<div><dt>金額</dt><dd>' + amtText(s) + '</dd></div></dl>'
        + '<div>' + (s.target ? '<span class="chip">' + s.target + '</span>' : '') + (s.online === '1' ? '<span class="chip">オンライン完結</span>' : '') + (s.form === '仲介・紹介' ? '<span class="chip">仲介・紹介</span>' : '') + '</div></div>';
    }
    h += '</div>';
    const rest = lastRows.length - shownCount;
    if(rest > 0) h += '<div class="more-row"><button class="btn btn-sub" onclick="moreRows()">残り ' + rest + ' 件を表示する</button></div>';
  }
  document.getElementById('search-result').innerHTML = h;
}
function moreRows(){ shownCount += 15; renderRows(); }
function animateCount(el){
  const target = parseInt(el.dataset.count, 10);
  if(isNaN(target)) return;
  const t0 = performance.now(), dur = 1200;
  function tick(t){
    const p = Math.min((t - t0) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.firstChild.nodeValue = Math.round(target * eased).toLocaleString('ja-JP');
    if(p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
document.addEventListener('DOMContentLoaded', () => {
  renderStep(); runSearch();
  const cio = new IntersectionObserver(es => es.forEach(e => { if(e.isIntersecting){ animateCount(e.target); cio.unobserve(e.target); } }), {threshold: .4});
  document.querySelectorAll('[data-count]').forEach(el => cio.observe(el));
});
""".replace('__METHODS__', methods_js).replace('__SERVICES__', services_js).replace('__MNAMES__', json.dumps(method_names, ensure_ascii=False))

if REVIEW:
    hero_media = f'<img class="hero-media" src="{asset("hero-poster.webp")}" alt="">'
else:
    hero_media = f'<video class="hero-media" autoplay muted loop playsinline poster="{asset("hero-poster.webp")}"><source src="{asset("hero-bg.mp4")}" type="video/mp4"></video>'

FAQS = [
    ('手数料の上限が書いていない会社があるのはなぜですか', '会社の公式サイトが、手数料の下限だけを公表しているためです。当サイトは公表されていない数字を推測で埋めず、「非公表」と書きます。上限が分からない会社は、見積もりの段階で料率の幅を確認する必要があります。'),
    ('状態チェックで、調達できる金額の目安が出ないのはなぜですか', '当サイトは審査をしていないためです。各社が公表している金額の範囲は事実として並べますが、「あなたは○○万円調達できます」という表示は根拠のない約束になるので出しません。実際に調達できる金額は、各社の審査で決まります。'),
    ('透明性スコアとは何ですか', '当サイトが定義した物差しです。費用の下限と上限、金額の下限と上限、償還請求権の有無、実績、所在地と代表者の5項目のうち、公式の公表で確認できた項目の数を数えています。スコアが低いことは、その会社の条件が悪いことを意味しません。公表されていない項目は、見積もりや契約書で確認する必要がある場所として読んでください。'),
    ('給与ファクタリングの会社は載っていますか', '載せていません。給与ファクタリングは貸金業に当たるとする判断が出ており、金融庁も注意喚起を公表しています。当サイトの掲載基準では対象外です。'),
    ('情報はいつ時点のものですか', '各サービスの行に最終確認日を付けています。会社の条件は変わるため、当サイトは公式の公表を観測し、差分があれば記録して記事に反映します。直近の観測で直した差分は「観測の記録」に載せています。'),
    ('このサイトの利用に料金はかかりますか', 'かかりません。状態チェックの結果表示も、現状シートの作成も無料です。申し込みは各社の公式サイトで行ってください。'),
]
faq_html = ''.join(f'<details class="faq rv"><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q, a in FAQS)

body = f"""
<div class="hero" style="background-image:url('__POSTER__')">
{hero_media}
<div class="hero-shade"></div>
<div class="wrap"><div class="hero-in">
<p class="eyebrow">FUNDING OBSERVATORY — 全ての手法から探し出す</p>
<h1>支払いの期限に<em>間に合う</em><br>資金調達を、状態から<br>見つける</h1>
<p class="lead">費用の低い手法から順に確認します。あなたの状態で使える手法と、貸してくれる候補の会社がその場で分かります。</p>
<div class="hero-cta">
<a class="btn btn-cta btn-hero" href="#check">状態チェックをはじめる →</a>
<a class="btn btn-glass" href="#search">{len(services)}件のサービスから探す</a>
</div>
<p class="hero-note">結果はその場で表示されます。結果と現状をまとめたシートは、各社の担当者への相談にそのまま使えます。</p>
<div class="hero-stats">
<div class="hstat"><b><span data-count="{len(services)}">0</span><i>件</i></b><span>収録サービス</span></div>
<div class="hstat"><b><span data-count="{len(methods)}">0</span><i>件</i></b><span>資金調達の手法</span></div>
<div class="hstat"><b><span data-count="{len(log)}">0</span><i>件</i></b><span>観測で直した条件の差分</span></div>
<div class="hstat"><b style="font-size:22px;padding-top:8px">{html.escape(last_checked)}</b><span>最終確認日</span></div>
</div>
</div></div>
</div>
<main class="wrap">
<section id="check">
<p class="eyebrow dark">01 — CHECK</p>
<h2 class="sec">状態チェック</h2>
<p class="sec-sub">費用の低い上位の手法から順に確認します。条件が合えば少ない質問で終わり、合わない場合は下位の手法へ進むため、質問が増えます。</p>
<div class="panel" id="wiz">
<div class="step-label" id="step-label">STEP 1 / 4</div>
<div class="progress"><i id="progress-bar" style="width:0%"></i></div>
<div class="wiz-q" id="wiz-q"></div>
<div class="opts" id="wiz-opts"></div>
<div class="wiz-nav"><button class="linkbtn" id="wiz-back" onclick="backStep()">← もどる</button><span class="note">選んだ内容は、結果の表示だけに使います</span></div>
</div>
<div id="result" style="display:none"></div>
<iframe name="gform_sink" style="display:none" title="送信先"></iframe>
<div class="steps3">
<div class="step3 rv"><b><i>1</i>質問に答える</b><p>上位の手法から順に、審査で見られる条件を確認します。候補が見つかった段階で止めることもできます。</p></div>
<div class="step3 rv"><b><i>2</i>間に合う手法と候補が出る</b><p>上位の系統から順に出ます。向かない手法も、理由つきで確認できます。</p></div>
<div class="step3 rv"><b><i>3</i>現状シートを担当者へ渡す</b><p>結果と現状を1枚にまとめたシートを作れます。担当者への相談が早く進みます。</p></div>
</div>
</section>

<section>
<p class="eyebrow dark">02 — WHY THIS SITE</p>
<h2 class="sec">このサイトの違い</h2>
<p class="sec-sub">比べる範囲と、数字の扱い方です。どれも、裏づけのページへつながっています。</p>
<div class="sgrid">
<div class="scard"><i>1</i><b>全ての手法を横断して比べる</b><p>24手法・{NSVC}サービス・{NENT}社を、1つの物差しで収録しています。ファクタリングだけ、融資だけのサイトでは出てこない候補まで並びます。</p><a href="methods/index.html">手法の一覧を見る</a></div>
<div class="scard"><i>2</i><b>結果は、その場で全部出す</b><p>状態チェックは、連絡先を聞かずに、使える手法と外れる理由まで表示します。候補が見つかった段階で止めることもできます。</p><a href="#check">状態チェックをする</a></div>
<div class="scard"><i>3</i><b>費用は、下限と上限の両方を書く</b><p>公式が公表していない項目は「公表を確認できていません」と書き、推測で埋めません。透明性スコアは、確認できた公表項目の数です。</p><a href="about.html">掲載の基準と定義を見る</a></div>
<div class="scard"><i>4</i><b>公式ページを観測し、変更を記録する</b><p>会社の条件は変わります。公式の公表を確認し、直した差分は日付つきで公開しています。</p><a href="observation.html">観測の記録を見る</a></div>
</div>
</section>

<section>
<p class="eyebrow dark">03 — BY SITUATION</p>
<h2 class="sec">状態別の入口</h2>
<p class="sec-sub">ピラーの記事は、状態ごとに進め方を書いています。</p>
<div class="split">
<img class="photo rv" src="{asset('section-owner.webp')}" alt="請求書を確認する事業者">
<div class="cards" style="grid-template-columns:1fr">{cards_html}</div>
</div>
</section>

<section>
<p class="eyebrow dark">04 — OBSERVATION</p>
<h2 class="sec">観測の記録</h2>
<p class="sec-sub">会社の条件は変わります。公式の公表を確認し、差分があれば日付つきで記録しています。手数料の上限を公表していない会社は、その事実も含めて記録します。</p>
<div class="split">
<img class="photo rv" src="{asset('section-observation.webp')}" alt="資料とノートで条件を確認する机">
<div>
<div class="stat-band" style="margin-top:0">
<div class="stat"><b>{len(services)}</b><span>収録サービス</span></div>
<div class="stat"><b>{len(methods)}</b><span>収録している手法</span></div>
<div class="stat"><b>{len(log)}件</b><span>公式確認で直した差分</span></div>
<div class="stat"><b style="font-size:19px;padding-top:7px">{html.escape(last_checked)}</b><span>最終確認日</span></div>
</div>
<div class="tblwrap"><table class="wide"><tr><th>観測日</th><th>会社</th><th>項目</th><th>変更</th></tr>{log_rows}</table></div>
<p style="margin-top:10px"><a href="observation.html">観測の記録（全件）と、観測の仕組みを見る</a></p>
</div>
</div>
</section>

<section id="search">
<p class="eyebrow dark">05 — SEARCH</p>
<h2 class="sec">サービスを探す</h2>
<p class="sec-sub">条件で絞れます。透明性スコアは、確認できた公表項目の数です（定義は下にあります）。</p>
<div class="filters">
<select id="f-method" onchange="runSearch()"><option value="">手法：すべて</option>{method_options}</select>
<select id="f-target" onchange="runSearch()"><option value="">対象：すべて</option><option>法人</option><option>個人事業主</option></select>
<select id="f-form" onchange="runSearch()"><option value="">事業形態：すべて</option><option>自社買取・直接</option><option>仲介・紹介</option><option>比較メディア・送客</option></select>
<label><input type="checkbox" id="f-online" onchange="runSearch()"> オンライン完結</label>
<label><input type="checkbox" id="f-score" onchange="runSearch()"> 透明性スコア3以上</label>
</div>
<div id="search-result"></div>
<p class="note">透明性スコア（0〜5）は当サイトの物差しです。費用の下限と上限、金額の下限と上限、償還請求権の有無、実績、所在地と代表者の5項目のうち、確認できた公表の数を数えています。スコアが低いことは、その会社の条件が悪いことを意味しません。公表されていない項目は、見積もりや契約書で確認する必要がある場所として読んでください。</p>
</section>

<section id="methods">
<p class="eyebrow dark">06 — METHODS</p>
<h2 class="sec">手法ガイド</h2>
<p class="sec-sub">全24手法の定義と、入金までの期間、費用の目安です。</p>
<p class="scroll-hint">横にスクロールできます →</p>
<div class="hscroll">{method_cards}</div>
</section>

<section>
<p class="eyebrow dark">07 — FAQ</p>
<h2 class="sec">よくある質問</h2>
<p class="sec-sub">当サイトの数字の出し方と、掲載の基準について答えます。</p>
{faq_html}
<div class="panel rv" style="margin-top:22px">
<h3 style="margin-top:0">掲載の基準</h3>
<p>掲載する会社は、公式の公表で条件を確認できた会社です。広告を含むページには冒頭にPR表示を置きます。順位を付ける場合は、比べた項目と順位の付け方を同じページで開示します。給与ファクタリングを行う会社は掲載しません。</p>
<p style="margin-bottom:0">悪質な業者の見分け方は、<a href="articles/basics-2sha.html">2社間ファクタリングの仕組みと申し込みの流れ</a>に書いています。</p>
</div>
</section>
</main>
<script>{JS}</script>
"""
body = body.replace('__POSTER__', asset('hero-poster.webp'))
top_ld = json.dumps({'@context': 'https://schema.org', '@graph': [
    {'@type': 'WebSite', 'name': '建設的な資金調達を実現するサイト', 'url': BASE_URL},
    {'@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FAQS]},
]}, ensure_ascii=False)
top_desc = f'資金調達の手法24件とサービス{NSVC}件の条件を記録したデータベース。質問に答えると、期限に間に合う手法と、貸してくれる候補の会社がその場で分かります。'
with open(OUT + '/index.html', 'w') as f:
    f.write(page('建設的な資金調達を実現するサイト', body, desc=top_desc, ld=top_ld, path=''))
print('TOP v3 done, review =', REVIEW)

ABOUT_BODY = f"""
<div class="wrap">
<p class="eyebrow">ABOUT</p>
<h1>運営者情報</h1>
<p>このサイトは、事業の資金調達に関する手法とサービスの条件を、各社の公式サイトと公的機関の公表に基づいて収集し、定期的に観測して記録する情報サイトです。運営は合同会社MELSYが行います。</p>
<h2 class="sec">このサイトの目的</h2>
<p>資金調達の手法は24種類に整理し、サービスごとの条件（費用、入金までの期間、対象、必要書類）は、公式に公表されている記載だけを載せます。公表されていない項目は、推測で埋めず、その旨を明記します。このサイトの内容は一般的な情報の提供であり、個別の融資や買取の可否を判断するものではありません。契約の前には、各社の公式の説明と契約書を必ず確認してください。</p>
<h2 class="sec">掲載の基準</h2>
<p>公式サイトで事業の実在と条件を確認できたサービスを掲載します。給与ファクタリングを行う事業者は掲載しません。償還請求権のある契約は、推奨の形では紹介しません。掲載している各ページには、情報の確認日を表示します。</p>
<h2 class="sec">順位と並びの決め方</h2>
<p>このサイトは、サービスの総合順位を付けていません。比較ページの並びは、手数料の下限など、比べる項目ごとの機械的な並びで、並びの根拠は各ページの冒頭に書いています。広告リンクの有無が、並びや条件の記載に影響することはありません。状態チェックの結果は、期限と目的と絶対条件から機械的に絞り込むもので、広告の有無では変わりません。</p>
<h2 class="sec">情報の集め方と観測</h2>
<p>条件は各社の公式サイトの公表から集め、公的機関の公表資料で裏づけを取ります。集めた条件は週に1回、公式ページの変更がないかを観測し、変更があれば記録を残します。観測の記録は<a href="observation.html">観測の記録</a>のページで全件を公開しています。公式の公表と当サイトの記録が食い違う場合は、公式の公表が正です。</p>
<h2 class="sec">数字の出し方</h2>
<p>透明性スコアは、費用の下限と上限、金額の下限と上限、償還請求権の有無、実績、所在地と代表者の5項目のうち、公式に公表されている項目の数です。公表が多いことは条件の良し悪しとは関係ありません。記事や手法のページに出す集計の数字は、収録しているサービスの公式の公表値を当サイトが数えたもので、数えた範囲と確認日を併記します。</p>
<h2 class="sec">収録と観測の数字</h2>
<p>2026年11月24日時点で、収録しているサービスは{NSVC}件、会社は{NENT}社、手法は24種類です。公式ページの変更の観測記録は{NLOG}件を公開しています。</p>
<h2 class="sec">広告について</h2>
<p>一部のページには、アフィリエイト広告のリンクを含む場合があります。その場合は、ページの冒頭に「広告」「PR」の表示を置きます。広告の有無で、条件の記載や並び順を変えることはしません。</p>
<h2 class="sec">お問い合わせ</h2>
<p>掲載内容の誤りのご指摘などは、運営会社のサイト（<a href="https://melsy.info">melsy.info</a>）の窓口からご連絡ください。個別の資金調達の相談は、このサイトでは受け付けていません。</p>
</div>
"""
with open(OUT + '/about.html', 'w') as f:
    _org_ld = json.dumps({'@context': 'https://schema.org', '@type': 'Organization', 'name': '合同会社MELSY', 'url': 'https://melsy.info/', 'brand': '建設的な資金調達を実現するサイト'}, ensure_ascii=False)
    f.write(page('運営者情報', ABOUT_BODY, desc='このサイトの運営者、目的、掲載の基準、広告についての説明です。', ld=_org_ld, path='about.html'))

PRIVACY_BODY = """
<div class="wrap">
<p class="eyebrow">PRIVACY</p>
<h1>プライバシーポリシー</h1>
<p>このサイトにおける、利用者の情報の扱いを説明します。</p>
<h2 class="sec">状態チェックの入力について</h2>
<p>状態チェックで選んだ内容は、結果を表示するためだけにブラウザの中で処理します。結果を見るだけの場合、選んだ内容がサーバーへ送信されたり保存されたりすることはありません。</p>
<h2 class="sec">現状シートの作成で取得する情報</h2>
<p>現状シートの作成を申し込んだ場合に限り、会社名、担当者名、メールアドレス、電話番号（任意）と、状態チェックの結果の要約を取得します。申し込みはGoogleフォームで受け付け、回答はGoogleスプレッドシートに記録して管理します。利用の目的は、シートの送付と、資金調達に関する情報の案内です。取得した情報を第三者へ販売したり、目的外に提供したりすることはしません。削除の希望は、運営者情報に記載の窓口へご連絡ください。</p>
<h2 class="sec">アクセス解析とクッキー</h2>
<p>このサイトでは、利用状況を把握するためにアクセス解析を導入する場合があります。アクセス解析はクッキーを使い、個人を特定しない形で情報を収集します。ブラウザの設定でクッキーを無効にできます。</p>
<h2 class="sec">広告について</h2>
<p>一部のページにはアフィリエイト広告のリンクがあります。リンク先の事業者のサイトにおける情報の扱いは、各事業者のプライバシーポリシーに従います。</p>
<h2 class="sec">個人情報の扱い</h2>
<p>個人情報を取得するのは、現状シートの作成を申し込んだ場合だけです（上の項目をご覧ください）。運営者へ直接ご連絡いただいた場合に得た情報は、返信と対応のためだけに使い、第三者へ提供しません。</p>
<h2 class="sec">改定</h2>
<p>このポリシーを改定した場合は、このページで公表します。</p>
</div>
"""
with open(OUT + '/privacy.html', 'w') as f:
    f.write(page('プライバシーポリシー', PRIVACY_BODY, desc='このサイトにおける利用者の情報の扱い（状態チェックの入力、アクセス解析、広告）について説明します。', path='privacy.html'))

NOTFOUND_BODY = """
<div class="wrap">
<p class="eyebrow">NOT FOUND</p>
<h1>ページが見つかりません</h1>
<p>指定されたページは、移転したか、現在は公開していません。お探しの内容は、次の入口から探せます。</p>
<p><a href="index.html#check">状態チェックで、使える資金調達の方法を探す</a></p>
<p><a href="index.html">トップページへ戻る</a></p>
</div>
"""
with open(OUT + '/404.html', 'w') as f:
    f.write(page('ページが見つかりません', NOTFOUND_BODY, desc='指定されたページは見つかりませんでした。', path='404.html'))

SHEET_BODY = """
<div class="wrap">
<p class="eyebrow">SHEET</p>
<h1>資金調達 現状シート</h1>
<p>状態チェックの結果と、あなたの現状をまとめたシートです。各社の担当者への相談に、そのままお使いください。</p>
<div id="sheet-body"><p>シートの情報を読み込んでいます。</p></div>
<div class="cta-row"><button class="btn btn-cta" onclick="window.print()">このシートを印刷する</button><a class="btn btn-ghost" href="index.html#check">状態チェックへ戻る</a></div>
<p class="note">このシートは一般的な情報の整理です。個別の可否や金額は、各社の審査で決まります。</p>
</div>
<style>@media print{header.site,footer.site,.sticky-cta,.cta-row{display:none}body{padding:0}}</style>
<script>
(function(){
  var box = document.getElementById('sheet-body');
  var d = null;
  try{ d = JSON.parse(sessionStorage.getItem('shikin_sheet') || 'null'); }catch(e){}
  if(!d){ box.innerHTML = '<p>シートの情報が見つかりませんでした。状態チェックを済ませてから、結果の画面で「現状シートを作成する」を押してください。</p>'; return; }
  var h = '<p class="note">作成日：' + d.date + '</p>';
  h += '<h2 class="sec">現状</h2><div class="tblwrap"><table>' + d.state.map(function(r){ return '<tr><th style="width:34%">' + r[0] + '</th><td>' + r[1] + '</td></tr>'; }).join('') + '</table></div>';
  h += '<h2 class="sec">候補の手法と会社</h2>';
  h += d.shown.map(function(m){
    var s = '<div class="mcard"><h3>' + m.name + (m.maybe ? ' <span class="badge low">最短では間に合うが確実ではない</span>' : '') + '</h3>'
      + '<dl class="kv"><dt>入金まで</dt><dd>' + m.period + '</dd><dt>費用の目安</dt><dd>' + m.cost + '</dd></dl>';
    if(m.svcs.length) s += '<p style="margin:6px 0 0">候補：' + m.svcs.join('／') + '</p>';
    return s + '</div>';
  }).join('');
  if(d.docs && d.docs.length) h += '<h2 class="sec">まず用意する書類（複数社で使い回せます）</h2><ul class="why-list">' + d.docs.map(function(x){ return '<li>' + x + '</li>'; }).join('') + '</ul>';
  if(d.pending && d.pending.length) h += '<h2 class="sec">まだ確認していない手法</h2><p>' + d.pending.join('、') + '</p>';
  if(d.unfit && d.unfit.length) h += '<h2 class="sec">今回の状態では外れた手法</h2><p>' + d.unfit.join('、') + '</p>';
  h += '<h2 class="sec">担当者へのメモ</h2><p style="border:1px solid var(--line);border-radius:8px;min-height:110px;background:#fff"></p>';
  box.innerHTML = h;
})();
</script>
"""
_sheet = page('資金調達 現状シート', SHEET_BODY, desc='状態チェックの結果と現状をまとめたシートです。', path='sheet.html')
_sheet = _sheet.replace('</title>', '</title><meta name="robots" content="noindex">', 1)
with open(OUT + '/sheet.html', 'w') as f:
    f.write(_sheet)
print('about/privacy done')
# ---------- observation page ----------
all_log_rows = ''.join(f"<tr><td>{html.escape(r['date'])}</td><td>{html.escape(r['entity'])}</td><td>{html.escape(r['item'])}</td><td>{html.escape(r['before'])} → {html.escape(r['after'])}</td></tr>" for r in log[::-1])
OBS_BODY = f"""
<article class="wrap">
<p class="eyebrow dark">OBSERVATION</p>
<h1>観測の記録</h1>
<p>会社の条件は変わります。このサイトでは、収録したサービスの公式ページを定期的に確認し、公表の内容と当サイトの記録に差分があれば、ここに日付つきで残します。</p>
<h2>観測の仕組み</h2>
<p>公式ページを取得し、前回の記録と比べて変わったページを拾います。手数料や入金スピードなど、数字の項目については、記録した値が公式ページ上で確認できるかも合わせて見ます。記録は自動では書き換えません。差分は確認のうえで反映し、確認できなかった項目は「公表を確認できていません」として残します。</p>
<h2>記録（全{len(log)}件）</h2>
<div class="tblwrap"><table class="wide"><tr><th>観測日</th><th>会社</th><th>項目</th><th>変更</th></tr>{all_log_rows}</table></div>
<p><a href="index.html">トップへ戻る</a></p>
</article>
"""
with open(OUT + '/observation.html', 'w') as f:
    f.write(page('観測の記録｜公式ページの変更を確認した記録', OBS_BODY, desc='収録サービスの公式ページを定期的に確認し、条件の変更を日付つきで記録したページです。観測の仕組みも書いています。', path='observation.html'))
print('observation done')

