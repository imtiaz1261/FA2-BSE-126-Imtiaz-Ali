"""
Reusable UI Components — Premium Design System.
All components use the theme.py color tokens and render via st.markdown HTML.
"""
from __future__ import annotations
import streamlit as st
from typing import Any, Optional
from theme import COLORS, PLAN_COLORS, PLAN_GRADIENTS


# ── KPI / Stat Card ───────────────────────────────────────────────────────────

def kpi_card(
    label: str,
    value: Any,
    sub: str = "",
    icon: str = "",
    trend: str = "",          # "up" | "down" | ""
    accent: str = "#4f8ef7",
    col=None,
) -> None:
    trend_html = ""
    if trend == "up":
        trend_html = f'<span style="color:#22c55e;font-size:0.75rem">▲ {sub}</span>'
        sub = ""
    elif trend == "down":
        trend_html = f'<span style="color:#ef4444;font-size:0.75rem">▼ {sub}</span>'
        sub = ""

    html = f"""
    <div style="background:linear-gradient(145deg,#131d32,#0f1629);
                border:1px solid #1e2d47;border-radius:14px;
                padding:20px 22px;position:relative;overflow:hidden;
                transition:all 0.2s ease;">
      <div style="position:absolute;top:0;right:0;width:3px;height:100%;
                  background:{accent};border-radius:0 14px 14px 0;"></div>
      <div style="color:#64748b;font-size:0.75rem;font-weight:600;
                  text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
        {icon} {label}
      </div>
      <div style="color:#f0f4ff;font-size:1.9rem;font-weight:700;
                  line-height:1;margin-bottom:6px;">{value}</div>
      {trend_html}
      {f'<div style="color:#4a5568;font-size:0.76rem;margin-top:2px;">{sub}</div>' if sub else ''}
    </div>"""
    (col or st).markdown(html, unsafe_allow_html=True)


# ── Plan Badge ────────────────────────────────────────────────────────────────

def plan_badge(plan: str, size: str = "sm") -> str:
    icons  = {"free": "🆓", "pro": "⚡", "enterprise": "🏢"}
    labels = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
    grad   = PLAN_GRADIENTS.get(plan.lower(), PLAN_GRADIENTS["free"])
    icon   = icons.get(plan.lower(), "🆓")
    label  = labels.get(plan.lower(), plan.title())
    pad    = "3px 10px" if size == "sm" else "6px 16px"
    fs     = "0.75rem"  if size == "sm" else "0.9rem"
    return (
        f'<span style="background:{grad};color:#fff;font-size:{fs};'
        f'font-weight:700;padding:{pad};border-radius:20px;'
        f'display:inline-block;letter-spacing:0.04em;">'
        f'{icon} {label}</span>'
    )


# ── Status Badge ──────────────────────────────────────────────────────────────

def status_badge(status: str) -> str:
    cfg = {
        "ready":      ("#22c55e", "rgba(34,197,94,0.1)",  "● Ready"),
        "processing": ("#f59e0b", "rgba(245,158,11,0.1)", "⟳ Indexing"),
        "uploaded":   ("#4f8ef7", "rgba(79,142,247,0.1)", "↑ Queued"),
        "failed":     ("#ef4444", "rgba(239,68,68,0.1)",  "✕ Failed"),
        "safe":       ("#22c55e", "rgba(34,197,94,0.1)",  "✓ Safe"),
        "blocked":    ("#ef4444", "rgba(239,68,68,0.1)",  "✕ Blocked"),
        "sanitised":  ("#f59e0b", "rgba(245,158,11,0.1)", "⚠ Sanitised"),
    }
    col, bg, label = cfg.get(status.lower(), ("#94a3b8", "rgba(148,163,184,0.1)", status.title()))
    return (
        f'<span style="background:{bg};color:{col};border:1px solid {col}33;'
        f'font-size:0.75rem;font-weight:600;padding:3px 10px;border-radius:20px;'
        f'display:inline-block;">{label}</span>'
    )


# ── Source Card ───────────────────────────────────────────────────────────────

def source_card(src: dict, idx: int, expanded: bool = False) -> None:
    title    = src.get("title", "Untitled")[:90]
    url      = src.get("url", "#")
    domain   = src.get("domain", url)[:40]
    snippet  = src.get("snippet", "")[:250]
    score    = src.get("score", 0.0)
    findings = src.get("key_findings", "")
    pub      = src.get("published", "")

    score_col = "#22c55e" if score > 0.7 else ("#f59e0b" if score > 0.4 else "#ef4444")
    score_bar = int(score * 100)

    header = (
        f'<span style="color:#4f8ef7;font-weight:700;font-size:0.85rem;">[{idx}]</span> '
        f'<span style="color:#f0f4ff;font-weight:600;">{title}</span> '
        f'<span style="color:#4a5568;font-size:0.78rem;"> · {domain}</span>'
        f'<span style="float:right;color:{score_col};font-size:0.78rem;font-weight:600;">'
        f'{score:.0%}</span>'
    )

    with st.expander(header, expanded=expanded):
        # Score bar
        st.markdown(
            f'<div style="background:#1e2d47;border-radius:4px;height:4px;margin-bottom:10px;">'
            f'<div style="background:{score_col};width:{score_bar}%;height:4px;border-radius:4px;"></div></div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"[🔗 {url[:60]}]({url})")
        if pub:
            c2.caption(pub[:16])
        if snippet:
            st.caption(snippet)
        if findings:
            st.markdown("**Key findings:**")
            st.markdown(findings)


# ── Document Card ─────────────────────────────────────────────────────────────

def document_card(doc: dict, on_delete=None) -> None:
    name    = doc.get("filename", "Unknown")
    status  = doc.get("status", "unknown")
    size_kb = doc.get("size_bytes", 0) / 1024
    ext     = name.rsplit(".", 1)[-1].upper() if "." in name else "FILE"
    ext_colors = {"PDF":"#ef4444","DOCX":"#4f8ef7","TXT":"#22c55e","MD":"#8b5cf6"}
    ext_col  = ext_colors.get(ext, "#64748b")

    with st.container():
        st.markdown(
            f'<div style="background:#131d32;border:1px solid #1e2d47;'
            f'border-radius:12px;padding:14px 16px;margin:6px 0;'
            f'display:flex;align-items:center;gap:12px;">'
            f'<div style="background:{ext_col}22;border:1px solid {ext_col}44;'
            f'color:{ext_col};font-size:0.7rem;font-weight:700;'
            f'padding:6px 8px;border-radius:8px;min-width:40px;text-align:center;">{ext}</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="color:#f0f4ff;font-weight:600;font-size:0.9rem;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>'
            f'<div style="color:#4a5568;font-size:0.76rem;margin-top:2px;">'
            f'{size_kb:.0f} KB</div></div>'
            f'<div>{status_badge(status)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if on_delete:
            if st.button("🗑", key=f"del_doc_{doc.get('id','')}", help="Delete"):
                on_delete(doc["id"])


# ── Tool Step Card ────────────────────────────────────────────────────────────

TOOL_META = {
    "calculator":         ("🧮", "#22c55e", "Calculator"),
    "web_search":         ("🌐", "#4f8ef7", "Web Search"),
    "document_search":    ("📄", "#8b5cf6", "Document Search"),
    "get_current_datetime":("🕐", "#14b8a6", "Date & Time"),
    "add_days":           ("📅", "#14b8a6", "Add Days"),
    "days_between":       ("📅", "#14b8a6", "Days Between"),
    "day_of_week":        ("📅", "#14b8a6", "Day of Week"),
}

def tool_badge(tool_name: str) -> str:
    icon, col, label = TOOL_META.get(tool_name, ("🔧", "#64748b", tool_name))
    return (
        f'<span style="background:{col}22;color:{col};border:1px solid {col}44;'
        f'font-size:0.75rem;font-weight:600;padding:3px 9px;border-radius:20px;'
        f'display:inline-flex;align-items:center;gap:4px;">{icon} {label}</span>'
    )


def tool_step_card(step: dict, idx: int) -> None:
    name   = step.get("name", "tool")
    args   = step.get("arguments", {})
    result = str(step.get("result", ""))
    icon, col, label = TOOL_META.get(name, ("🔧", "#64748b", name))

    st.markdown(
        f'<div style="background:#0f1629;border:1px solid {col}33;'
        f'border-left:3px solid {col};border-radius:0 10px 10px 0;'
        f'padding:12px 16px;margin:4px 0;animation:fadeInUp 0.2s ease;">'
        f'<div style="color:{col};font-weight:700;font-size:0.85rem;margin-bottom:6px;">'
        f'{icon} {label}</div>',
        unsafe_allow_html=True,
    )
    if args:
        arg_str = ", ".join(f"{k}={repr(v)}" for k, v in list(args.items())[:3])
        st.caption(f"Args: {arg_str}")
    if result:
        st.caption(f"→ {result[:200]}{'…' if len(result) > 200 else ''}")
    st.markdown("</div>", unsafe_allow_html=True)


# ── Progress Timeline ─────────────────────────────────────────────────────────

def progress_timeline(steps: list[str], completed: list[str], active: str = "") -> str:
    lines = []
    for step in steps:
        if step in completed:
            icon = '✓'
            col  = '#22c55e'
            weight = '600'
            opacity = '1'
        elif step == active:
            icon = '⟳'
            col  = '#f59e0b'
            weight = '600'
            opacity = '1'
        else:
            icon = '○'
            col  = '#1e2d47'
            weight = '400'
            opacity = '0.5'
        lines.append(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:5px 0;opacity:{opacity};">'
            f'<span style="color:{col};font-size:0.88rem;font-weight:700;'
            f'width:18px;text-align:center;">{icon}</span>'
            f'<span style="color:{col};font-size:0.88rem;font-weight:{weight};">{step}</span>'
            f'</div>'
        )
    return (
        '<div style="background:#0f1629;border:1px solid #1e2d47;'
        'border-radius:12px;padding:16px 18px;">' +
        "".join(lines) +
        "</div>"
    )


# ── Section Header ────────────────────────────────────────────────────────────

def section_header(title: str, subtitle: str = "", icon: str = "") -> None:
    st.markdown(
        f'<div style="margin-bottom:20px;">'
        f'<h2 style="color:#f0f4ff;font-size:1.4rem;font-weight:700;'
        f'margin:0;display:flex;align-items:center;gap:10px;">'
        f'{icon} {title}</h2>'
        + (f'<p style="color:#64748b;font-size:0.88rem;margin:4px 0 0;">{subtitle}</p>' if subtitle else '') +
        '</div>',
        unsafe_allow_html=True,
    )


# ── Empty State ───────────────────────────────────────────────────────────────

def empty_state(icon: str, title: str, description: str, action_label: str = "") -> bool:
    """Returns True if action button was clicked."""
    st.markdown(
        f'<div class="empty-state">'
        f'<div class="empty-state-icon">{icon}</div>'
        f'<div class="empty-state-title">{title}</div>'
        f'<div class="empty-state-desc">{description}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if action_label:
        c = st.columns([1, 2, 1])[1]
        return c.button(action_label, type="primary", use_container_width=True)
    return False


# ── Notification Toast ────────────────────────────────────────────────────────

def toast_success(msg: str) -> None:
    st.markdown(
        f'<div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);'
        f'border-radius:10px;padding:12px 16px;color:#22c55e;font-size:0.9rem;'
        f'display:flex;align-items:center;gap:10px;animation:fadeInUp 0.2s ease;">'
        f'✓ {msg}</div>',
        unsafe_allow_html=True,
    )


def toast_error(msg: str) -> None:
    st.markdown(
        f'<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);'
        f'border-radius:10px;padding:12px 16px;color:#ef4444;font-size:0.9rem;'
        f'display:flex;align-items:center;gap:10px;animation:fadeInUp 0.2s ease;">'
        f'✕ {msg}</div>',
        unsafe_allow_html=True,
    )


def toast_warning(msg: str) -> None:
    st.markdown(
        f'<div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);'
        f'border-radius:10px;padding:12px 16px;color:#f59e0b;font-size:0.9rem;'
        f'display:flex;align-items:center;gap:10px;animation:fadeInUp 0.2s ease;">'
        f'⚠ {msg}</div>',
        unsafe_allow_html=True,
    )


def toast_info(msg: str) -> None:
    st.markdown(
        f'<div style="background:rgba(79,142,247,0.1);border:1px solid rgba(79,142,247,0.3);'
        f'border-radius:10px;padding:12px 16px;color:#4f8ef7;font-size:0.9rem;'
        f'display:flex;align-items:center;gap:10px;animation:fadeInUp 0.2s ease;">'
        f'ℹ {msg}</div>',
        unsafe_allow_html=True,
    )


# ── Blocked Request Banner ────────────────────────────────────────────────────

def security_blocked_banner(category: str, reason: str) -> None:
    cat_labels = {
        "prompt_injection":    "Prompt Injection Detected",
        "jailbreak":           "Jailbreak Attempt Blocked",
        "harmful_content":     "Harmful Content Blocked",
        "prompt_extraction":   "System Prompt Extraction Blocked",
        "role_manipulation":   "Role Manipulation Blocked",
        "malicious_code":      "Malicious Code Generation Blocked",
        "pii_redacted":        "PII Redacted from Response",
        "dangerous_output":    "Dangerous Output Blocked",
        "input_too_long":      "Input Too Long",
    }
    label = cat_labels.get(category, "Request Blocked")
    st.markdown(
        f'<div style="background:rgba(239,68,68,0.08);'
        f'border:1px solid rgba(239,68,68,0.3);border-radius:14px;'
        f'padding:20px 24px;margin:12px 0;">'
        f'<div style="color:#ef4444;font-size:1rem;font-weight:700;'
        f'display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'🛡️ {label}</div>'
        f'<div style="color:#94a3b8;font-size:0.88rem;line-height:1.6;">{reason}</div>'
        f'<div style="color:#4a5568;font-size:0.80rem;margin-top:10px;">'
        f'Please modify your request and try again.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Quota Warning Banner ──────────────────────────────────────────────────────

def quota_exceeded_banner(used: int, limit: int, plan: str) -> None:
    st.markdown(
        f'<div style="background:rgba(245,158,11,0.08);'
        f'border:1px solid rgba(245,158,11,0.3);border-radius:14px;'
        f'padding:20px 24px;margin:12px 0;">'
        f'<div style="color:#f59e0b;font-size:1rem;font-weight:700;margin-bottom:8px;">'
        f'📊 Monthly Limit Reached</div>'
        f'<div style="color:#94a3b8;font-size:0.88rem;">'
        f'You have used <strong style="color:#f0f4ff">{used:,}</strong> of '
        f'<strong style="color:#f0f4ff">{limit:,}</strong> requests '
        f'on the <strong style="color:#f0f4ff">{plan.title()}</strong> plan.</div>'
        f'<div style="color:#4a5568;font-size:0.80rem;margin-top:8px;">'
        f'Upgrade your subscription to continue.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
