# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools", "brotli"]
# ///
"""Genera el README de perfil de André y su tarjeta de terminal (claro y oscuro) desde datos reales.

Uso:  uv run build.py        # escribe README.md + assets/week-{light,dark}.svg
Datos: `gh api` local, o el GITHUB_TOKEN por defecto en la Action (no hace falta PAT: todo es público).
Los números de la tarjeta son medidos; las líneas de humor están escritas para leerse como chiste, no como dato.
"""

import base64
import io
import json
import os
import subprocess
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).parent
FONTS = ROOT / "fonts"
ASSETS = ROOT / "assets"
LOGIN = "A-PachecoT"
TEAM = ["Melissa1221", "lepaccio", "JuanSilva2000"]

# Repos públicos que vale la pena mostrar; el orden lo decide el último push.
LATELY = {
    "cofoundy/brand-skills": "turn an idea into a brand (name, identity, voice) without leaving your agent",
    "cofoundy/dagyard": "a live DAG of your coding agents' plan; the tasks that need you turn amber",
    "cofoundy/mailglow": "vibe-code HTML emails that survive Gmail, Outlook and Apple Mail",
    "cofoundy/basalt-plugin": "publish docs straight from Claude Code, Codex or Cursor",
    "A-PachecoT/aurora": "a CBT thought record that never leaves your device",
    "A-PachecoT/uni-beamer-claude": "LaTeX Beamer slides with the UNI brand, made by Claude",
}

THEMES = {
    "dark": {"bg": "#0B1622", "bar": "#0F1E2D", "line": "#1D3346", "text": "#E7E8DE", "muted": "#8A9399",
             "accent": "#46A0D0", "ok": "#6FCF97", "dots": ["#F96A53", "#F5B83D", "#4CC38A"]},
    "light": {"bg": "#FBFCFD", "bar": "#F0F4F7", "line": "#DBE5EB", "text": "#0D3A59", "muted": "#66727A",
              "accent": "#1F77A8", "ok": "#1E8E5A", "dots": ["#F96A53", "#F5B83D", "#4CC38A"]},
}
BARS = "▁▂▃▄▅▆▇█"
FONT_URLS = {"JetBrainsMono-Regular.ttf": "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf"}


def gh(path: str, **params) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        url = f"https://api.github.com/{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"bearer {token}"})
        return json.load(urllib.request.urlopen(req))
    args = ["gh", "api", "-X", "GET", path] + [a for k, v in params.items() for a in ("-f", f"{k}={v}")]
    return json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)


def graphql(q: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q}).encode(),
                                     headers={"Authorization": f"bearer {token}"})
        return json.load(urllib.request.urlopen(req))["data"]
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["data"]


def week() -> dict:
    """Últimos 7 días del calendario de contribuciones: incluye las privadas como conteo y lo lee cualquier token."""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=6)).date()
    cal = graphql('{user(login:"%s"){contributionsCollection(from:"%sT00:00:00Z",to:"%s"){contributionCalendar{'
                  'weeks{contributionDays{date contributionCount}}}}}}' % (LOGIN, since, now.strftime("%Y-%m-%dT%H:%M:%SZ")))
    days = [d for w in cal["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            for d in w["contributionDays"]][-7:]
    return {"days": days, "total": sum(d["contributionCount"] for d in days)}


def fonts() -> None:
    FONTS.mkdir(exist_ok=True)
    for name, url in FONT_URLS.items():
        if not (FONTS / name).exists():
            urllib.request.urlretrieve(url, FONTS / name)


def font_face(family: str, file: str, text: str) -> str:
    font = TTFont(FONTS / file)
    sub = subset.Subsetter(subset.Options(flavor="woff2"))
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return (f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,"
            f"{base64.b64encode(buf.getvalue()).decode()}) format('woff2');}}")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(theme: str, wk: dict) -> str:
    t = THEMES[theme]
    counts = [d["contributionCount"] for d in wk["days"]]
    spark = "".join(BARS[min(7, round(c / max(counts) * 7))] if c else " " for c in counts)
    first = date.fromisoformat(wk["days"][0]["date"]).strftime("%a").lower()
    rows = [
        ("contributions", f"{wk['total']:,}", "· 7 days", "num"),
        ("per day", spark, f"{first} → today", "spark"),
        ("written by me", "fewer than you'd think", "", "joke"),
        ("diffs I read", "0", "(the evals do)", "joke"),
        ("agents running", "too many", "", "joke"),
        ("coffee", "not instrumented yet", "", "joke"),
    ]
    W, LH, X0, X1 = 560, 38, 28, 226
    y0 = 140
    body = []
    for i, (k, v, note, kind) in enumerate(rows):
        y = y0 + i * LH
        delay = 0.35 + i * 0.12
        fill = t["accent"] if kind in ("num", "spark") else t["text"]
        body.append(
            f'<g class="ln" style="animation-delay:{delay:.2f}s">'
            f'<text x="{X0 + 16}" y="{y}" fill="{t["muted"]}">{esc(k)}</text>'
            f'<text x="{X1}" y="{y}" fill="{fill}">{esc(v)}'
            + (f'<tspan fill="{t["muted"]}"> {esc(note)}</tspan>' if note else "")
            + "</text></g>")
    yp = y0 + len(rows) * LH + 18  # baseline del prompt final
    H = yp + 34
    text = "".join(r[0] + r[1] + r[2] for r in rows) + "andre@lima~$week--me whoami" + BARS + "→ "
    dots = "".join(f'<circle cx="{28 + k * 20}" cy="26" r="6" fill="{c}"/>' for k, c in enumerate(t["dots"]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
 aria-label="Terminal: {wk['total']:,} contributions in the last 7 days. Written by me: fewer than you'd think. Diffs I read: zero, the evals do.">
<style>{font_face("cf-mono", "JetBrainsMono-Regular.ttf", text)}
text{{font-family:'cf-mono',ui-monospace,monospace;font-size:20px}}
.ln{{opacity:0;animation:in .35s ease-out forwards}}
.cur{{animation:blink 1.1s steps(1) 2.5s infinite}}
@keyframes in{{from{{opacity:0;transform:translateX(-4px)}}to{{opacity:1;transform:none}}}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.ln{{animation:none;opacity:1}}.cur{{animation:none}}}}
</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{t["bg"]}" stroke="{t["line"]}" stroke-width="2"/>
<path d="M1 15a14 14 0 0 1 14-14h{W - 30}a14 14 0 0 1 14 14v37H1z" fill="{t["bar"]}"/>
<line x1="1" y1="52" x2="{W - 1}" y2="52" stroke="{t["line"]}" stroke-width="2"/>
{dots}
<text x="{W / 2}" y="33" text-anchor="middle" fill="{t["muted"]}" style="font-size:15px">andre@lima — zsh</text>
<text x="{X0}" y="98"><tspan fill="{t["ok"]}">andre@lima</tspan><tspan fill="{t["muted"]}"> ~ $ </tspan><tspan fill="{t["text"]}">week --me</tspan></text>
{"".join(body)}
<g class="ln" style="animation-delay:{0.35 + len(rows) * 0.12:.2f}s"><text x="{X0}" y="{yp}"><tspan fill="{t["ok"]}">andre@lima</tspan><tspan fill="{t["muted"]}"> ~ $ </tspan></text>
<rect class="cur" x="{X0 + 178}" y="{yp - 18}" width="12" height="23" fill="{t["accent"]}"/></g>
</svg>'''


def lately() -> list[str]:
    rows = []
    for full, blurb in LATELY.items():
        r = gh(f"repos/{full}")
        rows.append((r["pushed_at"], full, blurb, r["html_url"]))
    rows.sort(reverse=True)
    today = datetime.now(timezone.utc).date()
    out = []
    for pushed, full, blurb, url in rows[:5]:
        ago = (today - date.fromisoformat(pushed[:10])).days
        when = "today" if ago == 0 else f"{ago}d&nbsp;ago"
        out.append(f"- [**{full.split('/')[1]}**]({url}) — {blurb} · {when}")
    return out


def readme(wk: dict, items: list[str]) -> str:
    team = ", ".join(f"[@{u}](https://github.com/{u})" for u in TEAM[:-1]) + f" and [@{TEAM[-1]}](https://github.com/{TEAM[-1]})"
    return f'''### Hey, I'm André 👋

I build software with AI agents in Lima, Peru 🇵🇪. I run [Cofoundy](https://cofoundy.dev), a small software studio, with {team}. Agents write and review our code; we decide what's worth building and check that it works in production. That explains my contribution graph.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/week-dark.svg">
  <img src="assets/week-light.svg" alt="{wk['total']:,} contributions in the last 7 days. Written by me: fewer than you'd think. Diffs I read: zero, the evals do." width="560">
</picture>
</p>

**Lately**

{chr(10).join(items)}

Yes, that's me at #1 on [committers.top for Peru](https://committers.top/peru_private). Mostly the agents' fault. If you follow anyone here, follow my teammates too: the agents answer to them.

[andre@cofoundy.dev](mailto:andre@cofoundy.dev) · [LinkedIn](https://www.linkedin.com/in/andrepachecot/) · [cofoundy.dev](https://cofoundy.dev)

<!-- generado por build.py · {date.today()} -->
'''


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.svg"):
        old.unlink()
    fonts()
    wk = week()
    for theme in THEMES:
        (ASSETS / f"week-{theme}.svg").write_text(card(theme, wk))
    (ROOT / "README.md").write_text(readme(wk, lately()))
    print(f"ok {date.today()} · {wk['total']:,} contribuciones en 7 días · {[d['contributionCount'] for d in wk['days']]}")


if __name__ == "__main__":
    main()
