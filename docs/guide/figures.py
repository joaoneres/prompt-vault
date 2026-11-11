"""SVG figures for the study guide, generated from small drawing helpers.

Every figure is plain inline SVG so the PDF stays vector and the text stays selectable.
"""
from __future__ import annotations

import html

C = {
    "domain": "#D9482B", "app": "#E0961F", "port": "#188A68", "adapter": "#3B5E92", "infra": "#6B7A90",
    "front": "#6D4AAE", "api": "#0E7C86", "core": "#2F5D9F", "nats": "#B8651B", "ext": "#8493A8",
    "ink": "#17243A", "muted": "#566883", "line": "#9AA8BC", "bg": "#F4F7FB", "ok": "#188A68", "bad": "#C9402B",
}
TINT = {  # light fills matching the strokes
    "domain": "#FBE3DC", "app": "#FBEBCB", "port": "#D3EEE4", "adapter": "#DCE6F3", "infra": "#E6EAF0",
    "front": "#E9E1F6", "api": "#D6EEF0", "core": "#DCE6F3", "nats": "#F8E6D3", "ext": "#EDF0F4",
}
_count = 0


def reset() -> None:
    global _count
    _count = 0


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def svg(w: int, h: int, body: str, dark: bool = False) -> str:
    return (
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="DejaVu Sans, Arial, sans-serif">'
        f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs>{body}</svg>'
    )


def text(x, y, s, size=11, anchor="middle", weight="400", fill=None, mono=False, italic=False):
    fam = ' font-family="DejaVu Sans Mono, monospace"' if mono else ""
    st = ' font-style="italic"' if italic else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill or C["ink"]}"{fam}{st}>{esc(s)}</text>'


def box(x, y, w, h, title, sub=None, kind="core", rx=8, fill=None, size=12, sub_size=9.5, title_fill=None):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or TINT[kind]}" stroke="{C[kind]}" stroke-width="1.6"/>'
    ty = y + h / 2 + (-2 if sub else 4)
    out += text(x + w / 2, ty, title, size, weight="700", fill=title_fill or C[kind])
    if sub:
        out += text(x + w / 2, ty + sub_size + 4, sub, sub_size, fill=C["muted"])
    return out


def arrow(x1, y1, x2, y2, dashed=False, color=None, width=1.6, label=None, lx=None, ly=None, size=9, path=None):
    col = color or C["muted"]
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    d = path or f"M{x1} {y1}L{x2} {y2}"
    out = f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{width}"{dash} marker-end="url(#ah)"/>'
    if label:
        out += text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 5, label, size, fill=col)
    return out


def figure(name: str, caption: str) -> str:
    global _count
    body = FIGS[name]()
    if name == "cover":
        return body
    _count += 1
    return f'<figure>{body}<figcaption>Figure {_count} — {esc(caption)}</figcaption></figure>'


# ------------------------------------------------------------------ figures

def cover():
    b = ""
    items = [(20, "front", "front", "React"), (225, "api", "api", "FastAPI"), (430, "core", "core", "hexagonal")]
    for x, k, t, s in items:
        b += f'<rect x="{x}" y="50" width="170" height="80" rx="12" fill="none" stroke="#9FB4D3" stroke-width="2"/>'
        b += text(x + 85, 88, t, 20, weight="700", fill="#fff") + text(x + 85, 110, s, 11, fill="#9FB4D3")
    b += arrow(190, 90, 223, 90, color="#9FB4D3") + arrow(395, 90, 428, 90, color="#9FB4D3")
    b += text(207, 80, "HTTP", 9, fill="#9FB4D3") + text(412, 80, "NATS", 9, fill="#9FB4D3")
    b += f'<rect x="430" y="150" width="170" height="40" rx="10" fill="none" stroke="#9FB4D3" stroke-width="2"/>' + text(515, 175, "SQLite", 13, fill="#fff")
    b += arrow(515, 130, 515, 148, color="#9FB4D3")
    return svg(620, 210, b)


def system():
    b = ""
    b += box(10, 60, 118, 70, "Browser", "React front", "front")
    b += box(190, 60, 118, 70, "api", "FastAPI gateway", "api")
    b += box(372, 60, 110, 70, "NATS", "message broker", "nats")
    b += box(546, 60, 118, 70, "core", "hexagonal service", "core")
    b += box(546, 190, 118, 44, "SQLite", "prompt_vault.db", "infra")
    b += box(354, 190, 146, 44, "nats CLI / other services", None, "ext", size=10)
    b += arrow(128, 95, 188, 95, label="HTTP / JSON", ly=86) + arrow(188, 107, 128, 107, dashed=True)
    b += arrow(308, 90, 370, 90, label="request", ly=80) + arrow(370, 104, 308, 104, dashed=True, label="reply", ly=118)
    b += arrow(482, 90, 544, 90) + arrow(544, 104, 482, 104, dashed=True)
    b += arrow(605, 130, 605, 188, label="SQL", lx=630, ly=162)
    b += arrow(427, 190, 427, 132, label="requests, events", lx=427, ly=150, size=8.5)
    b += text(80, 160, "Vite dev proxy: /api -> :8000", 9, fill=C["muted"])
    b += text(249, 160, "validates input, maps errors", 9, fill=C["muted"])
    b += text(249, 174, "to HTTP statuses", 9, fill=C["muted"])
    b += text(430, 258, "the core also publishes events (prompt.events.*) and unrecoverable command errors (prompt.errors) on NATS", 9, fill=C["nats"])
    return svg(690, 270, b)


def rings():
    b = f'<rect x="1" y="1" width="738" height="368" rx="14" fill="none" stroke="{C["ext"]}" stroke-dasharray="6 4"/>'
    b += text(14, 22, "EXTERNAL WORLD", 9, anchor="start", weight="700", fill=C["muted"])
    b += box(12, 140, 104, 60, "NATS clients", "nats CLI, api", "ext", size=11)
    b += box(624, 140, 104, 60, "SQLite file", "prompt_vault.db", "ext", size=11)
    b += box(624, 50, 104, 50, "Terminal", "rich logs", "ext", size=11)
    for k, x, y, w, h, lab in [("adapter", 140, 24, 460, 286, "adapter/  ·  translates and connects"), ("port", 176, 64, 388, 206, "port/  ·  contracts"), ("app", 214, 102, 312, 130, "app/  ·  use cases")]:
        b += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{TINT[k]}" stroke="{C[k]}" stroke-width="1.6"/>' + text(x + w / 2, y + 20, lab, 11, weight="700", fill=C[k])
    b += f'<rect x="268" y="140" width="204" height="70" rx="12" fill="{TINT["domain"]}" stroke="{C["domain"]}" stroke-width="2"/>'
    b += text(370, 165, "domain/", 14, weight="700", fill=C["domain"]) + text(370, 183, "Prompt · PromptVersion", 10) + text(370, 197, "rules · states · events (pure Python)", 9, fill=C["muted"])
    b += box(140, 322, 460, 34, "infra/  ·  configures the technologies the adapters use", None, "infra", size=11)
    b += arrow(116, 170, 138, 170) + arrow(600, 170, 622, 170) + arrow(600, 76, 622, 76)
    return svg(740, 372, b)


def deps():
    nodes = {"adapter": (40, 60, "messaging · persistence"), "infra": (500, 60, "settings · db · nats · log"),
             "app": (40, 160, "use cases"), "port": (500, 160, "Protocols (contracts)"), "domain": (270, 260, "the core")}
    b = ""
    edges = [("M260 85H498", "adapter", "infra"), ("M150 110V158", "adapter", "app"), ("M260 102L498 170", "adapter", "port"),
             ("M40 85H16V285H268", "adapter", "domain"), ("M260 185H498", "app", "port"), ("M200 210L296 258", "app", "domain"), ("M560 210L464 258", "port", "domain")]
    for d, _, _ in edges:
        b += arrow(0, 0, 0, 0, path=d, color=C["adapter"])
    for k, (x, y, s) in nodes.items():
        b += box(x, y, 220, 50, k + "/", s, k, size=13)
    b += text(380, 342, "No arrow starts at domain/. Nothing in the core points to adapter/ or infra/.", 10, fill=C["muted"], italic=True)
    b += text(380, 22, "main.py knows everyone: it is the composition root", 10, fill=C["muted"])
    return svg(740, 352, b)


def pointer():
    def row(y, active, label):
        o = text(10, y - 8, label, 10, anchor="start", weight="700", fill=C["muted"])
        for i, (x, body) in enumerate([(10, ["Hello", "world"]), (250, ["Hi", "world"]), (490, ["Hey", "world", "end"])], start=1):
            on = i == active
            o += f'<rect x="{x}" y="{y}" width="220" height="74" rx="8" fill="{TINT["port"] if on else "#fff"}" stroke="{C["port"] if on else C["line"]}" stroke-width="{2.2 if on else 1.4}"/>'
            o += text(x + 14, y + 22, f"v{i}", 13, anchor="start", weight="700")
            for j, ln in enumerate(body):
                o += text(x + 14, y + 40 + j * 13, ln, 10, anchor="start", mono=True, fill=C["muted"])
            if on:
                o += f'<rect x="{x + 150}" y="{y + 8}" width="60" height="18" rx="9" fill="{C["port"]}"/>' + text(x + 180, y + 21, "ACTIVE", 9, weight="700", fill="#fff")
        return o
    b = row(32, 3, "1) after update_content(...): the new version is created and activated")
    b += row(142, 1, "2) after activate_version(1): only the pointer moves, nothing is erased")
    return svg(730, 232, b)


def states():
    b = box(20, 20, 150, 52, "ACTIVE", "in use", "port", rx=26, size=13)
    b += box(380, 20, 150, 52, "INACTIVE", "switched off", "app", rx=26, size=13)
    b += box(200, 134, 150, 52, "DELETED", "soft delete", "domain", rx=26, size=13)
    b += arrow(172, 38, 378, 38, label="deactivate()", ly=30) + arrow(378, 56, 172, 56, label="reactivate()", ly=70)
    b += arrow(70, 74, 210, 138, label="delete()", lx=100, ly=112) + arrow(480, 74, 342, 138, label="delete()", lx=462, ly=112)
    b += arrow(220, 134, 150, 76, dashed=True, label="restore()", lx=146, ly=118) + arrow(330, 134, 400, 76, dashed=True, label="restore()", lx=404, ly=118)
    return svg(550, 200, b)


def er():
    def table(x, title, rows):
        o = f'<rect x="{x}" y="14" width="250" height="{34 + 20 * len(rows)}" rx="6" fill="#fff" stroke="{C["adapter"]}" stroke-width="1.6"/>'
        o += f'<rect x="{x}" y="14" width="250" height="26" rx="6" fill="{C["adapter"]}"/>' + text(x + 125, 32, title, 12, weight="700", fill="#fff")
        for i, (a, b2) in enumerate(rows):
            o += text(x + 12, 58 + i * 20, a, 10, anchor="start", mono=True) + text(x + 238, 58 + i * 20, b2, 9, anchor="end", fill=C["muted"])
        return o
    b = table(10, "prompts", [("id (PK)", "text 36"), ("name", "text"), ("status", "text 16 · index"), ("active_version_number", "int · nullable"), ("status_before_deletion", "text · nullable"), ("created_at / updated_at", "UTC date"), ("deleted_at", "UTC date · nullable")])
    b += table(380, "prompt_versions", [("id (PK)", "text 36"), ("prompt_id (FK)", "-> prompts.id"), ("number", "int"), ("content", "text"), ("created_at", "UTC date"), ("UNIQUE (prompt_id, number)", "")])
    b += arrow(260, 80, 378, 80, color=C["adapter"]) + text(272, 70, "1", 11, weight="700") + text(366, 70, "N", 11, weight="700")
    b += text(319, 100, "one prompt,", 9, fill=C["muted"]) + text(319, 112, "many versions", 9, fill=C["muted"])
    return svg(640, 190, b)


def nats():
    b = ""
    heads = [(10, "Publish / subscribe", "events: 1 emitter, N listeners"), (240, "Request / reply", "queries: the asker waits"), (470, "Fire and forget", "commands without a reply subject")]
    for x, h, s in heads:
        b += f'<rect x="{x}" y="10" width="210" height="170" rx="10" fill="{TINT["nats"]}" stroke="{C["nats"]}" stroke-width="1.4"/>' + text(x + 105, 32, h, 12, weight="700", fill=C["nats"]) + text(x + 105, 48, s, 9, fill=C["muted"])
    b += box(70, 70, 90, 34, "publisher", None, "core", size=10) + arrow(115, 104, 115, 128) + text(115, 120, "prompt.events.created", 8, fill=C["muted"], anchor="middle")
    b += box(25, 136, 80, 30, "listener 1", None, "ext", size=9) + box(125, 136, 80, 30, "listener 2", None, "ext", size=9)
    b += box(262, 74, 70, 34, "client", None, "api", size=10) + box(354, 74, 80, 34, "service", None, "core", size=10)
    b += arrow(334, 86, 352, 86) + arrow(352, 98, 334, 98, dashed=True) + text(343, 124, "reply comes back via a", 8, fill=C["muted"]) + text(343, 136, "temporary inbox, with the", 8, fill=C["muted"]) + text(343, 148, "same correlation id", 8, fill=C["muted"])
    b += box(490, 74, 76, 34, "sender", None, "api", size=10) + box(588, 74, 76, 34, "service", None, "core", size=10)
    b += arrow(568, 91, 586, 91) + text(627, 124, "if it fails, nobody waits:", 8, fill=C["muted"]) + text(627, 136, "the error goes to", 8, fill=C["muted"]) + text(627, 148, "prompt.errors", 8, weight="700", fill=C["bad"])
    return svg(690, 190, b)


def sequence(parts, steps, width, step_h=34, head_h=44, label_w=5.4):
    n = len(parts)
    gap = (width - 40) / n
    xs = [20 + gap / 2 + i * gap for i in range(n)]
    height = 70 + len(steps) * step_h
    b = ""
    for i, (kind, l1, l2) in enumerate(parts):
        b += f'<rect x="{xs[i] - gap / 2 + 4}" y="6" width="{gap - 8}" height="{head_h}" rx="7" fill="{TINT[kind]}" stroke="{C[kind]}" stroke-width="1.5"/>'
        b += text(xs[i], 25 if l2 else 33, l1, 9.5, weight="700", fill=C[kind]) + (text(xs[i], 38, l2, 9.5, weight="700", fill=C[kind]) if l2 else "")
        b += f'<line x1="{xs[i]}" y1="{6 + head_h}" x2="{xs[i]}" y2="{height - 6}" stroke="{C["line"]}" stroke-dasharray="3 4"/>'
    for k, (a, c, lab, ret) in enumerate(steps):
        y = 70 + k * step_h
        x1, x2 = xs[a], xs[c]
        d = 1 if x2 > x1 else -1
        w = len(lab) * label_w + 8
        mx = (x1 + x2) / 2
        b += f'<line x1="{x1}" y1="{y}" x2="{x2 - d * 6}" y2="{y}" stroke="{C["muted"]}" stroke-width="1.4"' + (' stroke-dasharray="5 4"' if ret else "") + "/>"
        b += f'<path d="M{x2} {y} l{-d * 8} -4.5 v9z" fill="{C["muted"]}"/>'
        b += f'<rect x="{mx - w / 2}" y="{y - 15}" width="{w}" height="13" fill="#fff"/>' + text(mx, y - 5, lab, 8.5, fill=C["ink"])
        b += f'<circle cx="{x1 + d * 11}" cy="{y + 9}" r="6.5" fill="{C["accent"] if "accent" in C else "#2F5D9F"}"/>' + text(x1 + d * 11, y + 12, str(k + 1), 8, weight="700", fill="#fff")
    return svg(width, height, b)


def seq_core():
    parts = [("ext", "NATS", "client"), ("adapter", "Messaging", "Adapter"), ("app", "UpdateContent", "UseCase"), ("domain", "Prompt", "(domain)"), ("adapter", "UnitOfWork", "+ Repository"), ("ext", "SQLite", ""), ("adapter", "NatsEvent", "Publisher")]
    steps = [(0, 1, "request prompt.content.update", 0), (1, 2, "execute(Command)", 0), (2, 4, "async with uow · get(id)", 0), (4, 5, "SELECT prompt + versions", 0),
             (4, 2, "rehydrated Prompt", 1), (2, 3, "add_version(content, activate=True)", 0), (2, 4, "save(prompt) + commit()", 0), (4, 5, "INSERT version · UPDATE prompt", 0),
             (2, 6, "publish(prompt.pull_events())", 0), (6, 0, "prompt.events.version_added / activated", 1), (2, 1, "Prompt aggregate", 1), (1, 0, "reply: {ok: true, data: {...}}", 1)]
    return sequence(parts, steps, 740)


def seq_e2e():
    parts = [("front", "Browser", "(React)"), ("api", "Controller", "(FastAPI)"), ("api", "PromptService", "NATSPublisher"), ("nats", "NATS", ""), ("adapter", "Core", "adapter"), ("domain", "Use case", "+ domain"), ("ext", "SQLite", "")]
    steps = [(0, 1, "PUT /api/prompts/{id}/content", 0), (1, 2, "service.update_content(dto)", 0), (2, 3, "request prompt.content.update", 0), (3, 4, "deliver + correlation id", 0),
             (4, 5, "execute(UpdateContentCommand)", 0), (5, 6, "INSERT version · UPDATE prompt", 0), (5, 3, "events: prompt.events.version_*", 1), (4, 3, "reply {ok, data}", 1),
             (3, 2, "reply message", 1), (2, 1, "unwrap data (or raise)", 1), (1, 0, "200 + JSON (or error JSON)", 1), (0, 0, "update state · toast", 1)]
    return sequence(parts, steps, 740, label_w=5.2)


def api_layers():
    b = box(10, 60, 130, 60, "HTTP request", "from the browser", "front")
    b += box(190, 20, 160, 56, "controllers/", "FastAPI router", "api")
    b += box(190, 100, 160, 56, "services/", "PromptService", "api")
    b += box(190, 180, 160, 56, "messaging/", "NATSPublisher", "api")
    b += box(400, 180, 120, 56, "NATS", "request / reply", "nats")
    b += box(400, 20, 150, 56, "models/", "request DTOs, ApiWrapper[T]", "ext", size=11)
    b += box(400, 100, 150, 56, "utils/", "exceptions, handlers, logs", "ext", size=11)
    b += arrow(140, 90, 188, 50) + arrow(270, 78, 270, 98) + arrow(270, 158, 270, 178) + arrow(352, 208, 398, 208)
    b += arrow(402, 48, 352, 48, dashed=True, color=C["muted"]) + arrow(402, 128, 352, 128, dashed=True) + arrow(402, 138, 352, 208, dashed=True)
    b += text(270, 262, "Only messaging/ imports nats-py. Controllers never catch errors: handlers do.", 10, fill=C["muted"], italic=True)
    return svg(580, 274, b)


def front_arch():
    b = box(10, 10, 560, 40, "main.tsx  ->  App.tsx   (state: prompts · route from the URL hash · toasts)", None, "front", size=11)
    comps = [("PromptList", "PromptCard"), ("PromptDetailModal", "CreatePromptModal"), ("ComparePage", "VersionSelector, DiffViewer"), ("TimelinePage", "VersionTimeline"), ("TrashPage", "ConfirmModal")]
    for i, (a, s) in enumerate(comps):
        b += box(10 + i * 114, 80, 106, 52, a, s, "front", size=9.5, sub_size=8)
        b += arrow(63 + i * 114, 50, 63 + i * 114, 78)
    b += box(10, 168, 560, 40, "api/prompts.ts   (one function per endpoint)  ->  api/client.ts (Axios + error interceptor)", None, "api", size=11)
    b += arrow(290, 132, 290, 166)
    b += box(10, 240, 270, 36, "Vite dev proxy   /api/*  ->  http://localhost:8000", None, "ext", size=10)
    b += box(310, 240, 260, 36, "API gateway   (FastAPI)", None, "api", size=10)
    b += arrow(290, 208, 145, 238) + arrow(282, 258, 308, 258)
    return svg(580, 290, b)


def errors():
    steps = [("core", "core replies", "{ok:false, error:{code}}"), ("api", "NATSPublisher", "code -> exception"), ("api", "BaseAppException", "message · code · status"), ("api", "exception handler", "-> JSON error"),
             ("front", "Axios interceptor", "-> ApiError"), ("front", "toast", "shows the message")]
    b = ""
    for i, (k, t, s) in enumerate(steps):
        x = 8 + i * 120
        b += box(x, 20, 108, 60, t, s, k, size=10, sub_size=8)
        if i < len(steps) - 1:
            b += arrow(x + 109, 50, x + 119, 50)
    b += text(366, 112, "Controllers and services never catch exceptions: the error travels untouched to the handler.", 10, fill=C["muted"], italic=True)
    return svg(730, 124, b)


FIGS = {f.__name__: f for f in [cover, system, rings, deps, pointer, states, er, nats, seq_core, seq_e2e, api_layers, front_arch, errors]}
