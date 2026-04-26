"""Report generator — converts FinalReport into beautiful HTML."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import markdown
from loguru import logger

from src.core.config import settings
from src.models.schemas import FinalReport


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — AI Research Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        
        :root {{
            --bg: #0a0a0f;
            --surface: #12121a;
            --surface-2: #1a1a2e;
            --border: #2a2a3e;
            --text: #e4e4ed;
            --text-muted: #8888a0;
            --accent: #6c63ff;
            --accent-glow: rgba(108, 99, 255, 0.15);
            --green: #4ade80;
            --yellow: #fbbf24;
            --red: #f87171;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
        }}

        .report-container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 3rem 2rem;
        }}

        .report-header {{
            text-align: center;
            padding: 3rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 3rem;
        }}

        .report-header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #6c63ff, #48dbfb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }}

        .report-meta {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 500;
            background: var(--accent-glow);
            color: var(--accent);
            border: 1px solid rgba(108, 99, 255, 0.3);
            margin: 0.5rem 0.25rem;
        }}

        .executive-summary {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 4px solid var(--accent);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 3rem;
        }}

        .executive-summary h2 {{
            color: var(--accent);
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }}

        .section {{
            margin-bottom: 3rem;
        }}

        .section h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--accent);
            display: inline-block;
        }}

        .section-content {{
            color: var(--text);
        }}

        .section-content p {{
            margin-bottom: 1rem;
        }}

        .key-findings {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
        }}

        .key-findings h3 {{
            color: var(--accent);
            margin-bottom: 1rem;
        }}

        .key-findings li {{
            padding: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
            list-style: none;
        }}

        .key-findings li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: var(--accent);
            font-weight: bold;
        }}

        .sources {{
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            margin-top: 3rem;
        }}

        .sources h3 {{
            color: var(--text-muted);
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }}

        .sources a {{
            color: var(--accent);
            text-decoration: none;
            word-break: break-all;
            font-size: 0.85rem;
        }}

        .sources a:hover {{
            text-decoration: underline;
        }}

        .sources li {{
            padding: 0.3rem 0;
            list-style: decimal;
            margin-left: 1.5rem;
            color: var(--text-muted);
        }}

        .footer {{
            text-align: center;
            padding: 3rem 0;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
            margin-top: 3rem;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1>{title}</h1>
            <div class="report-meta">
                <span class="badge">🔬 AI Research Agent</span>
                <span class="badge">📅 {date}</span>
                <span class="badge">📊 {source_count} Sources</span>
            </div>
        </div>

        <div class="executive-summary">
            <h2>📋 Executive Summary</h2>
            <div>{executive_summary}</div>
        </div>

        {key_findings_html}

        {sections_html}

        <div class="sources">
            <h3>📚 Sources & References</h3>
            <ol>{sources_html}</ol>
        </div>

        <div class="footer">
            Generated by AI Research Agent • {date}
        </div>
    </div>
</body>
</html>"""


def generate_html_report(report: FinalReport) -> str:
    """Generate a beautiful HTML report from a FinalReport."""

    md = markdown.Markdown(extensions=["extra"])

    # Sections
    sections_parts = []
    for section in report.sections:
        content_html = md.convert(section.content)
        md.reset()
        sections_parts.append(
            f'<div class="section"><h2>{section.title}</h2>'
            f'<div class="section-content">{content_html}</div></div>'
        )
    sections_html = "\n".join(sections_parts)

    # Key findings
    kf_html = ""
    if report.key_findings:
        items = "".join(f"<li>{f}</li>" for f in report.key_findings)
        kf_html = f'<div class="key-findings"><h3>🔑 Key Findings</h3><ul>{items}</ul></div>'

    # Sources
    sources_items = ""
    for s in report.sources:
        sources_items += f'<li><a href="{s}" target="_blank">{s}</a></li>'

    # Executive summary
    exec_html = md.convert(report.executive_summary)
    md.reset()

    html = REPORT_TEMPLATE.format(
        title=report.topic,
        date=datetime.now().strftime("%B %d, %Y"),
        source_count=len(report.sources),
        executive_summary=exec_html,
        key_findings_html=kf_html,
        sections_html=sections_html,
        sources_html=sources_items,
    )

    return html


def save_report(report: FinalReport) -> str:
    """Save report as HTML file and return the file path."""
    output_dir = Path(settings.REPORT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in report.topic)
    safe_name = safe_name[:60].strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_{timestamp}.html"

    filepath = output_dir / filename
    html = generate_html_report(report)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"📄 Report saved to: {filepath}")
    return str(filepath)
