#!/usr/bin/env python3
"""Generates the SVG assets used by the profile README from live GitHub data.

Usage: GITHUB_TOKEN=... python3 scripts/generate.py
Only the Python standard library is required.
"""

import json
import os
import subprocess
import textwrap
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("PROFILE_USER", "berkcangumusisik")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = "#0D1117"
CARD = "#111823"
BORDER = "#253041"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
CYAN = "#00D4FF"
VIOLET = "#8B5CF6"

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
MONO = "'SF Mono', 'JetBrains Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Notebook repos are Python work; counting them separately would split Python in two.
LANGUAGE_ALIASES = {"Jupyter Notebook": ("Python", "#3572A5")}

FEATURED = {
    "agent-hub": (
        "One AI engineering team for Claude Code. Install once and every project "
        "gets specialist agents that adapt to its stack.",
        ["Claude Code", "Agents", "CLI"],
    ),
    "repo-seatbelt": (
        "Safety layer for AI coding agents: CLAUDE.md / AGENTS.md generator, MCP "
        "runtime guardrail, pre-commit hook and GitHub Action.",
        ["MCP", "Guardrails", "DevTools"],
    ),
    "mac-screen-recorder": (
        "Open-source macOS capture tool with screenshots, screen recording, "
        "annotation and on-device OCR. Nothing leaves your Mac.",
        ["macOS", "OCR", "Privacy"],
    ),
    "voleykocai-llm-finetuning": (
        "End-to-end LLM fine-tuning pipeline: dataset, tokenizer, fine-tune, "
        "identity and benchmark stages, published to Hugging Face.",
        ["Transformers", "Fine-tuning", "HF Hub"],
    ),
    "turkish-medical-vector-search": (
        "Semantic search over Turkish medical text using sentence-transformers "
        "embeddings and a ChromaDB vector store.",
        ["Embeddings", "ChromaDB", "RAG"],
    ),
    "countries-bpe-tokenizer": (
        "A BPE tokenizer written from scratch, plus four tiny transformer "
        "architectures trained and compared on top of it.",
        ["Tokenizers", "PyTorch", "From scratch"],
    ),
}

TOOLBOX = [
    ("AI &amp; MACHINE LEARNING", [
        ("PyTorch", "#EE4C2C"), ("Hugging Face", "#FFD21E"), ("Transformers", "#FF9D00"),
        ("Ollama", "#FFFFFF"), ("ChromaDB", "#FF6446"), ("Gradio", "#F97316"),
        ("RAG", CYAN), ("Fine-tuning", VIOLET),
    ]),
    ("AI-POWERED DEVELOPMENT", [
        ("Cursor", "#FFFFFF"), ("Claude Code", "#D97757"), ("Windsurf", "#58E5BB"),
        ("GitHub Copilot", "#8957E5"), ("OpenAI API", "#10A37F"), ("Gemini", "#4285F4"),
        ("Lovable", "#FF4F8B"), ("MCP", CYAN),
    ]),
]

# Source: LinkedIn profile export. (company, role, period, location, highlight)
EXPERIENCE = [
    ("Arya Investment Platform", "Software Engineer", "Mar 2026 – Present", "İstanbul", ""),
    ("Pazaryeri Converter", "Full Stack Developer", "Jan 2025 – Jun 2025", "Ankara",
     "Re-engineered the platform with React, .NET Core & MUI; integrated 10+ marketplace APIs "
     "(Trendyol, Hepsiburada, İkas)"),
    ("TrendPiyasa", "Full Stack Developer", "Jan 2025 – Jun 2025", "Ankara",
     "Mobile-first seller & buyer panels with Next.js, Tailwind and Ant Design on top of .NET REST APIs"),
    ("Priente Group", "Frontend Developer", "Nov 2024 – Dec 2024", "Ankara",
     "Shipped 5 responsive web platforms and a real-time Three.js cyberattack dashboard for Guardpot"),
    ("Yetkin Gençler (YetGen)", "IT Co-Chief Leader · Python Trainer", "Feb 2022 – Nov 2024", "İstanbul",
     "Ran IT operations for 150+ members; taught Python to 120 students with a 95% completion rate"),
    ("VBT Yazılım", "Software Developer Intern", "Jul 2022 – Aug 2022", "Remote",
     "Full-stack development on live projects"),
]

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER,
                 isFork: false, privacy: PUBLIC) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage { name color }
      }
    }
  }
}
"""

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def graphql(query, variables, auth):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {auth}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        payload = json.load(res)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def fetch():
    auth = token()
    repos, cursor, user = [], None, None
    while True:
        user = graphql(QUERY, {"login": USER, "cursor": cursor}, auth)
        page = user["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    languages = {}
    for repo in repos:
        lang = repo["primaryLanguage"]
        if not lang:
            continue
        name, color = LANGUAGE_ALIASES.get(lang["name"], (lang["name"], lang["color"] or MUTED))
        languages.setdefault(name, {"size": 0, "color": color})["size"] += 1

    calendar = user["contributionsCollection"]["contributionCalendar"]
    return {
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": user["followers"]["totalCount"],
        "repos": user["repositories"]["totalCount"],
        "contributions": calendar["totalContributions"],
        "weeks": [w["contributionDays"] for w in calendar["weeks"]],
        "days": all_days(user["createdAt"], auth),
        "languages": sorted(languages.items(), key=lambda kv: kv[1]["size"], reverse=True),
        "repo_map": {r["name"]: r for r in repos},
    }


def all_days(created_at, auth):
    """Daily contribution counts from account creation until today, oldest first."""
    start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    days = {}
    for year in range(start.year, now.year + 1):
        window_from = max(start, datetime(year, 1, 1, tzinfo=timezone.utc))
        window_to = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        variables = {"login": USER, "from": window_from.isoformat(), "to": window_to.isoformat()}
        weeks = graphql(YEAR_QUERY, variables, auth)["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
    return sorted(days.items())


def compact(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def svg(width, height, body, style="", title=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
<style>
  .sans {{ font-family: {SANS}; }}
  .mono {{ font-family: {MONO}; }}
  @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  .fade {{ animation: fadeUp .7s ease-out both; }}
  {style}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
{body}
</svg>
"""


def card_frame(width, height, gradient_id):
    return f"""<defs>
  <linearGradient id="{gradient_id}" x1="0" y1="0" x2="{width}" y2="0" gradientUnits="userSpaceOnUse">
    <stop stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
</defs>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="{CARD}" stroke="{BORDER}"/>
<rect x="24" y="0.5" width="{width - 48}" height="2" rx="1" fill="url(#{gradient_id})"/>"""


def header():
    code = [
        [("const ", VIOLET), ("berkcan", CYAN), (" = {", TEXT)],
        [("  role", "#7EE787"), (": ", TEXT), ('"Software Engineer @ Arya"', "#A5D6FF"), (",", TEXT)],
        [("  stack", "#7EE787"), (": [", TEXT), ('"React"', "#A5D6FF"), (", ", TEXT), ('"Next.js"', "#A5D6FF"),
         (", ", TEXT), ('"React Native"', "#A5D6FF"), (", ", TEXT), ('"Python"', "#A5D6FF"), ("],", TEXT)],
        [("  ai", "#7EE787"), (": [", TEXT), ('"Fine-tuning"', "#A5D6FF"), (", ", TEXT), ('"RAG"', "#A5D6FF"),
         (", ", TEXT), ('"Agents"', "#A5D6FF"), ("],", TEXT)],
        [("  education", "#7EE787"), (": ", TEXT), ('"Gazi Univ. (BSc 1st, MSc)"', "#A5D6FF"), (",", TEXT)],
        [("  location", "#7EE787"), (": ", TEXT), ('"Ankara, TR"', "#A5D6FF"), (",", TEXT)],
        [("};", TEXT)],
    ]
    lines = []
    for i, tokens in enumerate(code):
        spans = "".join(f'<tspan fill="{color}">{escape(text)}</tspan>' for text, color in tokens)
        lines.append(
            f'<text class="mono fade" x="692" y="{136 + i * 24}" font-size="13" xml:space="preserve" '
            f'style="animation-delay:{0.6 + i * 0.18:.2f}s">{spans}</text>'
        )

    style = """
  @keyframes float1 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(60px, 30px); } }
  @keyframes float2 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-70px, -25px); } }
  @keyframes blink { 50% { opacity: 0; } }
  .orb1 { animation: float1 14s ease-in-out infinite; }
  .orb2 { animation: float2 16s ease-in-out infinite; }
  .cursor { animation: blink 1s step-end infinite; }
"""
    body = f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1200" y2="340" gradientUnits="userSpaceOnUse">
    <stop stop-color="#0A0F1A"/><stop offset="1" stop-color="#0D1424"/>
  </linearGradient>
  <linearGradient id="role" x1="70" y1="0" x2="560" y2="0" gradientUnits="userSpaceOnUse">
    <stop stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" stroke="#FFFFFF" stroke-opacity="0.045"/>
  </pattern>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>
  <clipPath id="frame"><rect width="1200" height="340" rx="20"/></clipPath>
</defs>
<g clip-path="url(#frame)">
  <rect width="1200" height="340" fill="url(#bg)"/>
  <rect width="1200" height="340" fill="url(#grid)"/>
  <circle class="orb1" cx="180" cy="40" r="170" fill="{CYAN}" fill-opacity="0.22" filter="url(#blur)"/>
  <circle class="orb2" cx="1080" cy="320" r="190" fill="{VIOLET}" fill-opacity="0.28" filter="url(#blur)"/>
</g>
<rect x="0.5" y="0.5" width="1199" height="339" rx="20" stroke="{BORDER}"/>

<g class="fade">
  <text class="mono" x="70" y="104" font-size="15" letter-spacing="4" fill="{CYAN}">HI THERE, I'M</text>
</g>
<g class="fade" style="animation-delay:.15s">
  <text class="sans" x="68" y="170" font-size="58" font-weight="800" fill="{TEXT}">Berkcan Gümüşışık</text>
</g>
<g class="fade" style="animation-delay:.3s">
  <text class="sans" x="70" y="214" font-size="25" font-weight="600" fill="url(#role)">Full Stack Developer · AI Builder</text>
</g>
<g class="fade" style="animation-delay:.45s">
  <text class="mono" x="70" y="254" font-size="15" fill="{MUTED}">&gt; React · Next.js · React Native · Python · LLMs<tspan class="cursor" fill="{CYAN}"> ▍</tspan></text>
</g>
<g class="fade" style="animation-delay:.6s">
  <rect x="70" y="276" width="244" height="32" rx="16" fill="#3FB950" fill-opacity="0.12" stroke="#3FB950" stroke-opacity="0.45"/>
  <circle cx="90" cy="292" r="5" fill="#3FB950"/>
  <text class="sans" x="104" y="297" font-size="14" font-weight="600" fill="#7EE787">Software Engineer @ Arya</text>
</g>

<g class="fade" style="animation-delay:.4s">
  <rect x="662" y="58" width="498" height="232" rx="14" fill="#0D1117" fill-opacity="0.85" stroke="{BORDER}"/>
  <path d="M662 72a14 14 0 0 1 14-14h470a14 14 0 0 1 14 14v22H662z" fill="#161B22"/>
  <circle cx="684" cy="76" r="6" fill="#FF5F57"/>
  <circle cx="704" cy="76" r="6" fill="#FEBC2E"/>
  <circle cx="724" cy="76" r="6" fill="#28C840"/>
  <text class="mono" x="911" y="81" font-size="13" fill="{MUTED}" text-anchor="middle">berkcan.ts</text>
</g>
{chr(10).join(lines)}"""
    return svg(1200, 340, body, style, "Berkcan Gümüşışık: Full Stack Developer and AI Builder")


def project_card(name, description, tags, repo):
    width, height = 500, 196
    desc_lines = textwrap.wrap(description, 60)[:3]
    desc = "".join(
        f'<text class="sans" x="28" y="{84 + i * 21}" font-size="14" fill="{MUTED}">{escape(line)}</text>'
        for i, line in enumerate(desc_lines)
    )

    chips, x = [], 28
    for tag in tags:
        w = len(tag) * 7 + 22
        chips.append(
            f'<rect x="{x}" y="146" width="{w}" height="24" rx="12" fill="{CYAN}" fill-opacity="0.08" stroke="{CYAN}" stroke-opacity="0.3"/>'
            f'<text class="sans" x="{x + w / 2}" y="162" font-size="12" font-weight="600" fill="#7DD3FC" text-anchor="middle">{escape(tag)}</text>'
        )
        x += w + 8

    lang = repo["primaryLanguage"] or {"name": "Other", "color": MUTED}
    counts = ""
    if repo["stargazerCount"]:
        counts += f"   ★ {compact(repo['stargazerCount'])}"
    if repo["forkCount"]:
        counts += f"   ⑂ {compact(repo['forkCount'])}"
    meta = f"""<g class="sans" font-size="13" fill="{MUTED}" text-anchor="end">
  <text x="{width - 28}" y="163" xml:space="preserve"><tspan fill="{lang['color']}">●</tspan> {escape(lang['name'])}{counts}</text>
</g>"""

    body = f"""{card_frame(width, height, "accent")}
<g class="fade">
  <path transform="translate(28 31)" fill="{CYAN}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>
  <text class="sans" x="54" y="45" font-size="19" font-weight="700" fill="{TEXT}">{escape(name)}</text>
  {desc}
  {"".join(chips)}
  {meta}
</g>"""
    return svg(width, height, body, title=f"{name}: {description}")


def stats_card(data):
    width, height = 500, 230
    icons = {
        "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
        "people": "M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 0 1 1-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 0 0 1 3.102 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 5.018 5.01 5.01 0 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 1-.549-.514 3.507 3.507 0 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a.75.75 0 0 1 .416-.672A1.5 1.5 0 0 0 11 5.5.75.75 0 0 1 11 4Zm-5.5-.5a2 2 0 1 0-.001 3.999A2 2 0 0 0 5.5 3.5Z",
        "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z",
        "pulse": "M6 2c.306 0 .582.187.696.471L10 10.731l1.304-3.26A.751.751 0 0 1 12 7h3.25a.75.75 0 0 1 0 1.5h-2.742l-1.812 4.528a.751.751 0 0 1-1.392 0L6 4.77 4.696 8.03A.75.75 0 0 1 4 8.5H.75a.75.75 0 0 1 0-1.5h2.742l1.812-4.529A.751.751 0 0 1 6 2Z",
    }
    tiles = [
        ("star", compact(data["stars"]), "Total Stars", "#FFD33D"),
        ("people", compact(data["followers"]), "Followers", CYAN),
        ("repo", compact(data["repos"]), "Public Repos", VIOLET),
        ("pulse", compact(data["contributions"]), "Contributions (1y)", "#3FB950"),
    ]
    parts = []
    for i, (icon, value, label, color) in enumerate(tiles):
        x, y = 24 + (i % 2) * 230, 72 + (i // 2) * 74
        parts.append(f"""<g class="fade" style="animation-delay:{0.15 + i * 0.12:.2f}s">
  <rect x="{x}" y="{y}" width="222" height="64" rx="12" fill="#FFFFFF" fill-opacity="0.025" stroke="{BORDER}"/>
  <circle cx="{x + 32}" cy="{y + 32}" r="18" fill="{color}" fill-opacity="0.12"/>
  <path transform="translate({x + 24} {y + 24})" fill="{color}" d="{icons[icon]}"/>
  <text class="sans" x="{x + 62}" y="{y + 31}" font-size="24" font-weight="800" fill="{TEXT}">{value}</text>
  <text class="sans" x="{x + 62}" y="{y + 50}" font-size="12.5" fill="{MUTED}">{label}</text>
</g>""")

    body = f"""{card_frame(width, height, "accent")}
<text class="sans fade" x="24" y="44" font-size="18" font-weight="700" fill="{TEXT}">GitHub Stats</text>
<text class="sans fade" x="{width - 24}" y="44" font-size="12" fill="{MUTED}" text-anchor="end">updated {datetime.now(timezone.utc):%b %d, %Y}</text>
{chr(10).join(parts)}"""
    return svg(width, height, body, title="GitHub stats")


def languages_card(data):
    width, height = 500, 230
    top = data["languages"][:8]
    total = sum(entry["size"] for _, entry in top) or 1

    bar, x = [], 24.0
    bar_width = width - 48
    for name, entry in top:
        w = bar_width * entry["size"] / total
        bar.append(f'<rect x="{x:.2f}" y="66" width="{w + 0.5:.2f}" height="10" fill="{entry["color"]}"/>')
        x += w

    legend = []
    for i, (name, entry) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 230, 112 + row * 28
        pct = 100 * entry["size"] / total
        legend.append(f"""<g class="fade" style="animation-delay:{0.15 + i * 0.07:.2f}s">
  <circle cx="{lx + 6}" cy="{ly - 4}" r="5" fill="{entry['color']}"/>
  <text class="sans" x="{lx + 20}" y="{ly}" font-size="13.5" fill="{TEXT}">{escape(name)}</text>
  <text class="mono" x="{lx + 214}" y="{ly}" font-size="12.5" fill="{MUTED}" text-anchor="end">{pct:.1f}%</text>
</g>""")

    body = f"""{card_frame(width, height, "accent")}
<defs><clipPath id="bar"><rect x="24" y="66" width="{bar_width}" height="10" rx="5"/></clipPath></defs>
<text class="sans fade" x="24" y="44" font-size="18" font-weight="700" fill="{TEXT}">Most Used Languages</text>
<text class="sans fade" x="{width - 24}" y="44" font-size="12" fill="{MUTED}" text-anchor="end">by primary language of repos</text>
<g clip-path="url(#bar)" class="fade">{"".join(bar)}</g>
{chr(10).join(legend)}"""
    return svg(width, height, body, title="Most used languages")


def toolbox():
    width = 1000
    rows, y = [], 40
    for label, tools in TOOLBOX:
        rows.append(f'<text class="mono fade" x="28" y="{y}" font-size="12.5" letter-spacing="2" fill="{CYAN}">{label}</text>')
        x, y = 28, y + 16
        for i, (name, color) in enumerate(tools):
            w = len(name) * 7.6 + 42
            if x + w > width - 28:
                x, y = 28, y + 48
            rows.append(f"""<g class="fade" style="animation-delay:{0.05 * i:.2f}s">
  <rect x="{x}" y="{y}" width="{w}" height="36" rx="10" fill="#FFFFFF" fill-opacity="0.03" stroke="{BORDER}"/>
  <circle cx="{x + 18}" cy="{y + 18}" r="5" fill="{color}"/>
  <text class="sans" x="{x + 32}" y="{y + 23}" font-size="14.5" font-weight="600" fill="{TEXT}">{escape(name)}</text>
</g>""")
            x += w + 8
        y += 76
    height = y - 20
    body = f"""{card_frame(width, height, "accent")}
{chr(10).join(rows)}"""
    return svg(width, height, body, title="AI and machine learning toolbox")


def experience():
    width, top = 1000, 96
    ys, y = [], top
    for *_, highlight in EXPERIENCE:
        ys.append(y)
        y += 78 if highlight else 54
    height = y - 18
    style = """
  @keyframes pulse { from { transform: scale(1); opacity: .7; } to { transform: scale(2.6); opacity: 0; } }
  .pulse { animation: pulse 1.8s ease-out infinite; transform-box: fill-box; transform-origin: center; }
"""
    rows = [f'<line x1="44" y1="{ys[0] - 5}" x2="44" y2="{ys[-1] - 5}" stroke="{BORDER}" stroke-width="2"/>']
    for i, (company, role, period, location, highlight) in enumerate(EXPERIENCE):
        y = ys[i]
        current = period.endswith("Present")
        dot = "#3FB950" if current else CYAN
        pulse = f'<circle class="pulse" cx="44" cy="{y - 5}" r="6" fill="{dot}"/>' if current else ""
        note = (f'<text class="sans" x="72" y="{y + 24}" font-size="13.5" fill="{MUTED}">{escape(highlight)}</text>'
                if highlight else "")
        rows.append(f"""<g class="fade" style="animation-delay:{0.1 + i * 0.1:.2f}s">
  {pulse}
  <circle cx="44" cy="{y - 5}" r="6" fill="{CARD}" stroke="{dot}" stroke-width="3"/>
  <text class="sans" x="72" y="{y}" font-size="16.5"><tspan font-weight="700" fill="{TEXT}">{escape(company)}</tspan><tspan fill="#7DD3FC">  ·  {escape(role)}</tspan></text>
  <text class="mono" x="{width - 28}" y="{y}" font-size="12.5" fill="{'#7EE787' if current else MUTED}" text-anchor="end">{escape(period)} · {escape(location)}</text>
  {note}
</g>""")

    body = f"""{card_frame(width, height, "accent")}
<text class="mono fade" x="28" y="46" font-size="12.5" letter-spacing="2" fill="{CYAN}">EXPERIENCE</text>
{chr(10).join(rows)}"""
    return svg(width, height, body, style, "Work experience")


def streaks(days):
    longest, longest_range, run, run_start = 0, (None, None), 0, None
    for date, count in days:
        if count:
            run_start = date if run == 0 else run_start
            run += 1
            if run > longest:
                longest, longest_range = run, (run_start, date)
        else:
            run = 0

    # Today only breaks the streak once it is over, so an empty today is skipped.
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1
    current_end = days[i][0] if i >= 0 else None
    current = 0
    while i >= 0 and days[i][1]:
        current += 1
        i -= 1
    current_range = (days[i + 1][0], current_end) if current else (None, None)
    return current, current_range, longest, longest_range


def pretty(date):
    return datetime.fromisoformat(date).strftime("%b %-d, %Y") if date else ""


def span(dates):
    start, end = dates
    return f"{pretty(start)} – {pretty(end)}" if start else "Start a new streak today"


def streak_card(data):
    width, height = 1000, 210
    days = data["days"]
    total = sum(count for _, count in days)
    current, current_range, longest, longest_range = streaks(days)
    first = next((date for date, count in days if count), days[0][0])

    flame = "M8 16c3.314 0 6-2 6-5.5 0-1.5-.5-4-2.5-6 .25 1.5-1.25 2-1.25 2C11 4 9 .5 6 0c.357 2 .5 4-2 6-1.25 1-2 2.729-2 4.5C2 14 4.686 16 8 16m0-1c-1.657 0-3-1-3-2.75 0-.75.25-2 1.25-3C6.125 10 7 10.5 7 10.5c-.375-1.25.5-3.25 2-3.5-.179 1-.25 2 1 3 .625.5 1 1.364 1 2.25C11 14 9.657 15 8 15"
    ring_len = 2 * 3.14159 * 46
    style = f"""
  @keyframes draw {{ from {{ stroke-dashoffset: {ring_len:.1f}; }} to {{ stroke-dashoffset: 0; }} }}
  .ring {{ stroke-dasharray: {ring_len:.1f}; animation: draw 1.4s ease-out both .2s; }}
"""
    body = f"""{card_frame(width, height, "accent")}
<defs>
  <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#FFB347"/><stop offset="1" stop-color="#FF5F6D"/>
  </linearGradient>
</defs>
<line x1="{width / 3:.0f}" y1="44" x2="{width / 3:.0f}" y2="{height - 44}" stroke="{BORDER}"/>
<line x1="{2 * width / 3:.0f}" y1="44" x2="{2 * width / 3:.0f}" y2="{height - 44}" stroke="{BORDER}"/>

<g class="fade" style="animation-delay:.1s" text-anchor="middle">
  <text class="sans" x="{width / 6:.0f}" y="96" font-size="40" font-weight="800" fill="{TEXT}">{total:,}</text>
  <text class="sans" x="{width / 6:.0f}" y="132" font-size="15" font-weight="600" fill="{CYAN}">Total Contributions</text>
  <text class="sans" x="{width / 6:.0f}" y="156" font-size="12.5" fill="{MUTED}">{pretty(first)} – Present</text>
</g>

<g class="fade" style="animation-delay:.2s" text-anchor="middle">
  <circle cx="{width / 2:.0f}" cy="86" r="46" stroke="{BORDER}" stroke-width="6"/>
  <circle class="ring" cx="{width / 2:.0f}" cy="86" r="46" stroke="url(#ringGrad)" stroke-width="6" stroke-linecap="round" transform="rotate(-90 {width / 2:.0f} 86)"/>
  <rect x="{width / 2 - 14:.0f}" y="28" width="28" height="28" rx="14" fill="{CARD}"/>
  <path transform="translate({width / 2 - 8:.0f} 33)" fill="#FF8C42" d="{flame}"/>
  <text class="sans" x="{width / 2:.0f}" y="100" font-size="38" font-weight="800" fill="{TEXT}">{current}</text>
  <text class="sans" x="{width / 2:.0f}" y="160" font-size="15" font-weight="600" fill="#FF8C42">Current Streak</text>
  <text class="sans" x="{width / 2:.0f}" y="182" font-size="12.5" fill="{MUTED}">{span(current_range)}</text>
</g>

<g class="fade" style="animation-delay:.3s" text-anchor="middle">
  <text class="sans" x="{5 * width / 6:.0f}" y="96" font-size="40" font-weight="800" fill="{TEXT}">{longest}</text>
  <text class="sans" x="{5 * width / 6:.0f}" y="132" font-size="15" font-weight="600" fill="{VIOLET}">Longest Streak</text>
  <text class="sans" x="{5 * width / 6:.0f}" y="156" font-size="12.5" fill="{MUTED}">{span(longest_range)}</text>
</g>"""
    return svg(width, height, body, style, f"Contribution streak: {current} days current, {longest} days longest")


LEVEL_COLORS = {
    "NONE": "#161B22",
    "FIRST_QUARTILE": "#0B3A4A",
    "SECOND_QUARTILE": "#0A6A85",
    "THIRD_QUARTILE": "#00A3CC",
    "FOURTH_QUARTILE": "#00D4FF",
}


def snake(data):
    pitch, size, left, top = 15, 12, 46, 74
    weeks = data["weeks"]
    width = left + len(weeks) * pitch + 26
    height = top + 7 * pitch + 30
    step, pause = 0.055, 2.5

    cells = []
    for col, week in enumerate(weeks):
        week_cells = []
        for day in week:
            row = (datetime.fromisoformat(day["date"]).weekday() + 1) % 7
            week_cells.append((col, row, day))
        cells.extend(week_cells if col % 2 == 0 else reversed(week_cells))

    travel = step * len(cells)
    total = travel + pause
    segments = 5

    grid, points = [], []
    for i, (col, row, day) in enumerate(cells):
        x, y = left + col * pitch, top + row * pitch
        points.append(f"{x + size / 2} {y + size / 2}")
        grid.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2.5" fill="{LEVEL_COLORS["NONE"]}"/>')
        level = day["contributionLevel"]
        if level != "NONE":
            eaten = (i + 0.5) * step / total
            grid.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2.5" fill="{LEVEL_COLORS[level]}">'
                f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;{eaten:.4f};{eaten + 0.002:.4f};0.97;1" '
                f'dur="{total:.2f}s" repeatCount="indefinite"/></rect>'
            )

    path = "M" + " L".join(points)
    body_parts = []
    for k in reversed(range(segments)):
        lag = k * step * 1.1
        s = size - k * 1.4
        color = CYAN if k == 0 else VIOLET
        opacity = 1 - k * 0.14
        key_times = f"0;{lag / total:.4f};{(lag + travel) / total:.4f};1"
        body_parts.append(
            f'<rect x="{-s / 2:.1f}" y="{-s / 2:.1f}" width="{s:.1f}" height="{s:.1f}" rx="{s / 3:.1f}" fill="{color}" fill-opacity="{opacity:.2f}">'
            f'<animateMotion path="{path}" dur="{total:.2f}s" repeatCount="indefinite" calcMode="linear" '
            f'keyPoints="0;0;1;1" keyTimes="{key_times}"/></rect>'
        )

    months, last_month = [], None
    for col, week in enumerate(weeks):
        month = datetime.fromisoformat(week[0]["date"]).strftime("%b")
        if month != last_month and col < len(weeks) - 2:
            months.append(f'<text class="sans" x="{left + col * pitch}" y="{top - 10}" font-size="11" fill="{MUTED}">{month}</text>')
            last_month = month

    weekdays = "".join(
        f'<text class="sans" x="{left - 10}" y="{top + row * pitch + 10}" font-size="10.5" fill="{MUTED}" text-anchor="end">{name}</text>'
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )
    legend_x = width - 60 - 5 * pitch
    legend = "".join(
        f'<rect x="{legend_x + i * pitch}" y="{height - 24}" width="{size}" height="{size}" rx="2.5" fill="{color}"/>'
        for i, color in enumerate(LEVEL_COLORS.values())
    )

    body = f"""{card_frame(width, height, "accent")}
<text class="sans" x="24" y="38" font-size="15" font-weight="700" fill="{TEXT}">{data['contributions']:,} contributions in the last year</text>
{"".join(months)}
{weekdays}
{"".join(grid)}
{"".join(body_parts)}
<text class="sans" x="{legend_x - 8}" y="{height - 14}" font-size="11" fill="{MUTED}" text-anchor="end">Less</text>
{legend}
<text class="sans" x="{width - 24}" y="{height - 14}" font-size="11" fill="{MUTED}" text-anchor="end">More</text>"""
    return svg(width, height, body, title="Contribution snake eating the contribution graph")


def footer():
    style = """
  @keyframes wave { from { transform: translateX(0); } to { transform: translateX(-1200px); } }
  .w1 { animation: wave 18s linear infinite; }
  .w2 { animation: wave 26s linear infinite reverse; }
"""
    wave = "M0 60 C 150 20 300 100 450 60 S 750 20 900 60 S 1050 100 1200 60 S 1350 20 1500 60 S 1800 100 1950 60 S 2250 20 2400 60 V 140 H 0 Z"
    body = f"""<defs>
  <linearGradient id="wg" x1="0" y1="0" x2="1200" y2="0" gradientUnits="userSpaceOnUse">
    <stop stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
  <clipPath id="clip"><rect width="1200" height="260" rx="20"/></clipPath>
</defs>
<g clip-path="url(#clip)">
  <rect width="1200" height="260" fill="#0A0F1A"/>
  <g transform="translate(0 168)">
    <path class="w2" d="{wave}" fill="{VIOLET}" fill-opacity="0.18"/>
    <path class="w1" d="{wave}" fill="url(#wg)" fill-opacity="0.28" transform="translate(0 14)"/>
  </g>
</g>
<rect x="0.5" y="0.5" width="1199" height="259" rx="20" stroke="{BORDER}"/>
<text class="mono fade" x="600" y="70" font-size="15" letter-spacing="4" fill="{CYAN}" text-anchor="middle">// DON'T REPEAT YOURSELF</text>
<text class="sans fade" x="600" y="122" font-size="34" font-weight="800" fill="{TEXT}" text-anchor="middle" style="animation-delay:.15s">Every new project is a new adventure.</text>
<text class="sans fade" x="600" y="162" font-size="18" fill="{MUTED}" text-anchor="middle" style="animation-delay:.3s">Let's build the next one together.</text>"""
    return svg(1200, 260, body, style, "Don't repeat yourself. Every new project is a new adventure.")


def main():
    data = fetch()
    (ASSETS / "projects").mkdir(parents=True, exist_ok=True)
    (ASSETS / "header.svg").write_text(header())
    (ASSETS / "stats.svg").write_text(stats_card(data))
    (ASSETS / "languages.svg").write_text(languages_card(data))
    (ASSETS / "toolbox.svg").write_text(toolbox())
    (ASSETS / "experience.svg").write_text(experience())
    (ASSETS / "streak.svg").write_text(streak_card(data))
    (ASSETS / "snake.svg").write_text(snake(data))
    (ASSETS / "footer.svg").write_text(footer())
    for name, (description, tags) in FEATURED.items():
        repo = data["repo_map"].get(name)
        if repo is None:
            raise SystemExit(f"Featured repo not found: {name}")
        (ASSETS / "projects" / f"{name}.svg").write_text(project_card(name, description, tags, repo))
    print(f"Generated assets for {USER}: {data['stars']} stars, {data['repos']} repos")


if __name__ == "__main__":
    main()
