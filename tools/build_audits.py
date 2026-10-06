#!/usr/bin/env python3
"""Render ScoutAI Design website-teardown report pages from the audit raw.json.

Usage: python3 tools/build_audits.py [raw.json] [--pricing standard|intro]
Writes audit/<slug>/index.html (noindex) for every site except those in SKIP.
"""
import html
import json
import re
import sys
from pathlib import Path

RAW = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path.home() / "Downloads/HonoluluResumes/services/audits/raw.json"
PRICING = "intro" if "--pricing" in sys.argv and sys.argv[sys.argv.index("--pricing") + 1] == "intro" else "standard"
SKIP = {"smile-solutions"}  # mis-attributed site: not the dental office
ROOT = Path(__file__).resolve().parent.parent
SITE = "https://design.scoutai.site"
PHONE = "413-570-6737"
EMAIL = "sonny@scoutai.site"

PRICES = {
    "standard": {
        "tuneup": "$1,800 one-time",
        "tuneup_note": "schema, analytics, call path, speed fixes, stale content, done in one week",
        "launch": "from $2,900",
        "found": "from $6,900",
        "presence": "$495/month",
        "care": "$79/month, first year included with any build",
    },
    "intro": {
        "tuneup": "$1,200 one-time",
        "tuneup_note": "schema, analytics, call path, speed fixes, stale content, done in one week",
        "launch": "$1,500–3,000",
        "found": "from $4,500",
        "presence": "$300–500/month",
        "care": "included for the first year with any build",
    },
}[PRICING]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def md_inline(s):
    """Backticks to <code>, keep everything else escaped."""
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def score_class(n):
    try:
        n = int(n)
    except Exception:
        return ""
    return "score--ok" if n >= 80 else "score--warn" if n >= 60 else "score--bad"


def first_sentence(t):
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    return (m.group(1) if m else t).strip()


def build(slug, s):
    co = s["company"]
    url = s["url"]
    sc = s["scores"]
    lh = s.get("lighthouse", {}).get("mobile", {}) or {}
    lhd = s.get("lighthouse", {}).get("desktop", {}) or {}
    lh_ok = lh.get("ok")
    perf = lh.get("scores", {}).get("performance") if lh_ok else None
    lcp = lh.get("lcp_s") if lh_ok else None
    fix = sc.get("fixability", "")
    rebuild = fix.lower().startswith("rebuild")
    jsonld = s.get("jsonld", {})
    mk = s.get("marketing_stack", {})
    conv = s.get("conversion", {})
    cr = s.get("copyright", {}).get("matches") or []
    years = sorted({m[0] for m in cr if m and m[0]})
    sitemap = s.get("sitemap", {})
    broken = s.get("internal_link_check", {}).get("broken") or []
    nap = s.get("nap", {})

    # evidence table rows
    ev = [
        ("Platform", s.get("platform_verdict", "")),
        ("Checked", s.get("checked_at", "")),
        ("Mobile Lighthouse performance", f"{perf}/100" if perf is not None else "not measured"),
        ("Largest Contentful Paint (mobile)", f"{lcp} s (Google's good threshold: 2.5 s)" if lcp is not None else "not measured"),
        ("Desktop performance", f"{lhd.get('scores', {}).get('performance')}/100" if lhd.get("ok") else "not measured"),
        ("Page weight (mobile load)", f"{lh.get('total_kb'):,} KB" if lh.get("total_kb") else "n/a"),
        ("Structured data (JSON-LD types)", ", ".join(jsonld.get("types") or []) or "none"),
        ("Address / phone / hours in schema", f"{'yes' if jsonld.get('has_address') else 'no'} / {'yes' if jsonld.get('has_telephone') else 'no'} / {'yes' if jsonld.get('has_openingHours') else 'no'}"),
        ("FAQ schema", "yes" if s.get("faq", {}).get("faq_schema") else "no"),
        ("Analytics / pixels found", ", ".join(k.upper().replace("_"," ") for k, v in mk.items() if v and k not in ("recaptcha","hcaptcha","turnstile")) or "none"),
        ("Tap-to-call link above the fold (mobile)", "yes" if conv.get("tel_in_first_20pct") else "no"),
        ("Phone matches BBB listing", "yes" if nap.get("bbb_phone_found") or (nap.get("bbb_phone") in (nap.get("phones_in_source") or [])) else "no / not found on page"),
        ("Footer copyright", ", ".join(years) or "none found"),
        ("Sitemap URLs", str(sitemap.get("url_count", "none"))),
        ("Broken internal links (sample)", str(len(broken))),
    ]

    issues = s.get("top_issues") or []
    wins = s.get("quick_wins") or []
    band = s.get("budget_estimate", {}).get("band", "")

    def score_card(label, key):
        v = sc.get(key, {})
        n = v.get("score")
        return f'<div class="score {score_class(n)}"><div class="n">{esc(n)}<small>/100</small></div><div class="l">{esc(label)}</div></div>'

    scores_html = "".join([
        score_card("Technical SEO", "technical_seo"),
        score_card("Performance", "performance"),
        score_card("AI-search readiness", "aeo_geo"),
        score_card("Marketing & conversion", "marketing_conversion"),
    ])

    issues_html = "".join(
        f'<div class="issue"><div class="num">{i:02d}</div><div><h3>{esc(first_sentence(t))}</h3>' + (f'<p>{md_inline(t[len(first_sentence(t)):].strip())}</p>' if t[len(first_sentence(t)):].strip() else '') + '</div></div>'
        for i, t in enumerate(issues, 1)
    )
    wins_html = "".join(f"<li>{md_inline(w)}</li>" for w in wins)
    ev_html = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in ev)

    if rebuild:
        rec_title = "Recommended: rebuild on a platform you own"
        rec_body = (f"<p>{esc(s.get('rebuild_note',''))}</p>"
                    f'<p class="price">Launch build {esc(PRICES["launch"])} <small>5–7 hand-built pages, schema, Google Business Profile cleanup, analytics, 90+ mobile Lighthouse target, two-week build</small></p>'
                    f'<p class="price">Found build {esc(PRICES["found"])} <small>Launch plus answer-ready service pages, review pipeline, AI-search baseline report, 30 days of tuning</small></p>')
        alt = f'<p>Prefer to keep the current site? The one-week tune-up below still applies: {esc(PRICES["tuneup"])}.</p>'
    else:
        rec_title = "Recommended: a one-week tune-up, then measure"
        rec_body = (f"<p>{esc(fix)}</p>"
                    f'<p class="price">Tune-up {esc(PRICES["tuneup"])} <small>{esc(PRICES["tuneup_note"])}</small></p>'
                    f'<p class="price">Presence {esc(PRICES["presence"])} <small>Google Business Profile management, monthly posts and review responses, citation hygiene, quarterly AI-search check, hosting and small edits included; cancel any month</small></p>')
        alt = f'<p>{esc(s.get("rebuild_note",""))}</p><p>If you do want a fresh build later: Launch {esc(PRICES["launch"])}, Care {esc(PRICES["care"])}.</p>'

    engine_note = ("Performance numbers come from Lighthouse 13.5, the same engine behind Google's PageSpeed Insights, run on 2026-10-05 in mobile mode with simulated throttling. "
                   "Scores vary about ten points between runs; treat them as a range, not a verdict.")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>Website teardown for {esc(co)} — ScoutAI Design</title>
<meta name="description" content="A measured review of {esc(url)}: speed, search, AI-search readiness and conversion, with fixes and prices.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/tokens.css">
<link rel="stylesheet" href="/assets/css/site.css">
<link rel="stylesheet" href="/assets/css/audit.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230f7a4e'/%3E%3Cpath d='M16 7l7 3v6c0 5-3.5 8-7 9-3.5-1-7-4-7-9v-6l7-3z' fill='none' stroke='%23fff' stroke-width='2' stroke-linejoin='round'/%3E%3C/svg%3E">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="/" aria-label="ScoutAI Design home"><span class="mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6l7-3z"/><path d="M9 12l2 2 4-4"/></svg></span>ScoutAI Design <span class="sub">Honolulu</span></a>
  <nav class="nav" aria-label="Primary"><a class="btn btn--primary" href="tel:+14135706737">{PHONE}</a></nav>
</div></header>
<main class="report">
  <div class="report-head">
    <div class="for">Prepared for {esc(co)} · {esc(s.get('town',''))} · private link, not indexed</div>
    <h1>What your website is costing you, measured.</h1>
    <p class="lede">I ran <a href="{esc(url)}" rel="noopener">{esc(url.replace('https://','').replace('http://','').rstrip('/'))}</a> through the same checks Google and the AI search engines use. Here is what came back, what it costs you in calls, and what I would fix first.</p>
    <div class="meta"><span>Checked {esc(s.get('checked_at',''))}</span><span>Platform: {esc(s.get('platform_verdict',''))}</span></div>
  </div>

  <div class="scores">{scores_html}</div>
  <p class="note">{esc(sc.get('technical_seo',{}).get('why',''))} · {esc(sc.get('aeo_geo',{}).get('why',''))}</p>

  <section>
    <h2>The five findings that matter</h2>
    {issues_html}
    <p class="note">These are measurements, not design opinions. Each one is something your current provider could have run in ten minutes.</p>
  </section>

  <section>
    <h2>What I would do in the first week</h2>
    <ul class="ticks">{wins_html}</ul>
  </section>

  <div class="offer">
    <h2>{esc(rec_title)}</h2>
    {rec_body}
    {alt}
    <p>Fixed prices, no retainer required, you own everything. First call is free and takes fifteen minutes.</p>
    <a class="btn btn--primary" href="sms:+14135706737?body=Hi%20Sonny%2C%20I%20read%20the%20{esc(co.replace(' ','%20'))}%20report.">Text Sonny · {PHONE}</a>
    <p>Or email <a href="mailto:{EMAIL}">{EMAIL}</a> · <a href="tel:+14135706737">{PHONE}</a></p>
  </div>

  <section class="method">
    <h2>Evidence and method</h2>
    <div style="overflow-x:auto"><table class="ev-table">{ev_html}</table></div>
    <p>{esc(engine_note)} Structured data, analytics tags, call links and copyright were read directly from the page source. Facebook and Yelp block automated checks, so social activity was not scored. Budget band is an estimate from public signals only ({esc(band)}).</p>
    <p>Prepared by Sonny Steele, ScoutAI Design, Honolulu. Fifteen years designing products for banks, healthcare and e-commerce companies; founder of <a href="https://scoutai.site/" rel="noopener">ScoutAI</a>. I design and write the code myself.</p>
  </section>
</main>
<footer><div class="wrap"><span>© 2026 ScoutAI Design · Honolulu, Hawaii</span><span><a href="/">design.scoutai.site</a> · <a href="mailto:{EMAIL}">{EMAIL}</a> · <a href="tel:+14135706737">{PHONE}</a></span></div></footer>
</body>
</html>
"""
    out = ROOT / "audit" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out


def main():
    data = json.load(open(RAW))["sites"]
    written = []
    for slug, s in data.items():
        if slug in SKIP:
            continue
        written.append(build(slug, s))
    for w in written:
        print(w.relative_to(ROOT))
    print(f"{len(written)} pages, pricing={PRICING}")


if __name__ == "__main__":
    main()
