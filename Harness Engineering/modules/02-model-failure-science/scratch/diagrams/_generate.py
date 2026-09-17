#!/usr/bin/env python3
"""Generate all hand-drawn Excalidraw diagrams for M2 Model Failure Science.

Writes <slug>/diagram.excalidraw + <slug>/diagram.animationinfo.json
into the directory containing this script (scratch/diagrams/).
"""
from __future__ import annotations

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

_seq = [10000]


def sid() -> int:
    _seq[0] += 1
    return _seq[0]


def _base(eid, x, y, w, h):
    return dict(
        id=eid, x=x, y=y, width=w, height=h,
        strokeColor="#1e1e1e", fillStyle="solid",
        strokeWidth=2, strokeStyle="solid", roughness=1, opacity=100, angle=0,
        seed=sid(), version=1, versionNonce=sid(), isDeleted=False,
        groupIds=[], boundElements=None, link=None, locked=False,
    )


def text(eid, x, y, s, fs=16, align="left", cid=None, valign="top"):
    # Give free-floating text a real measured width/height. The renderer does not
    # re-measure non-container text, so a tiny declared width wraps it into a
    # narrow column (the visible bug). Bound text is re-measured by the renderer.
    lines = s.split("\n")
    max_len = max((len(ln) for ln in lines), default=0)
    w = max_len * fs * 0.62 + 4
    h = len(lines) * fs * 1.25 + 4
    el = _base(eid, x, y, w, h)
    el.update(
        type="text", text=s, originalText=s, fontSize=fs, fontFamily=1,
        textAlign=align, verticalAlign=valign,
        backgroundColor="transparent", strokeWidth=1,
        containerId=cid, autoResize=True, lineHeight=1.25,
    )
    return el


def shape(kind, eid, x, y, w, h, label=None, fs=16, fill="#ffffff"):
    el = _base(eid, x, y, w, h)
    el.update(type=kind, backgroundColor=fill, boundElements=[])
    if kind == "rectangle":
        el["roundness"] = {"type": 3}
    els = [el]
    if label is not None:
        tid = "t_" + eid
        tx = text(tid, x + w / 2, y + h / 2, label, fs=fs,
                  align="center", cid=eid, valign="middle")
        el["boundElements"].append({"id": tid, "type": "text"})
        els.append(tx)
    return el, els


def arrow(eid, x, y, w, h, points=None, start=None, end=None):
    el = _base(eid, x, y, w, h)
    el.update(
        type="arrow", backgroundColor="transparent",
        points=points if points is not None else [[0, 0], [w, h]],
        startBinding=start, endBinding=end,
        startArrowhead=None, endArrowhead="arrow",
    )
    return el


def line(eid, x, y, w, h, points=None, dash=False):
    el = _base(eid, x, y, w, h)
    el.update(
        type="line", backgroundColor="transparent",
        points=points if points is not None else [[0, 0], [w, h]],
        strokeStyle="dashed" if dash else "solid",
    )
    return el


def v_arrow(eid, src_id, dst_id, x, y1, y2):
    """Vertical arrow from (x, y1) to (x, y2), bound to shapes."""
    return arrow(eid, x, y1, 0, y2 - y1,
                 [[0, 0], [0, y2 - y1]],
                 start={"elementId": src_id, "focus": 0, "gap": 2},
                 end={"elementId": dst_id, "focus": 0, "gap": 2})


def h_arrow(eid, src_id, dst_id, x1, x2, y):
    """Horizontal arrow from (x1, y) to (x2, y), bound to shapes."""
    return arrow(eid, x1, y, x2 - x1, 0,
                 [[0, 0], [x2 - x1, 0]],
                 start={"elementId": src_id, "focus": 0, "gap": 2},
                 end={"elementId": dst_id, "focus": 0, "gap": 2})


def free_arrow(eid, x1, y1, x2, y2):
    """Free arrow (no binding) from (x1,y1) to (x2,y2)."""
    x, y = min(x1, x2), min(y1, y2)
    return arrow(eid, x, y, abs(x2 - x1), abs(y2 - y1),
                 [[x1 - x, y1 - y], [x2 - x, y2 - y]])


def frame(eid, x, y, w, h, name):
    el = _base(eid, x, y, w, h)
    el.update(type="frame", backgroundColor="transparent",
              strokeColor="#bbbbbb", strokeWidth=2, roughness=0,
              name=name, frameId=None)
    return el


def build_animationinfo(elements):
    """Auto-derive a reveal story: title first, shapes+labels next, arrows last."""
    anim = []
    for el in elements:
        eid = el["id"]
        if el["type"] == "text" and el.get("containerId") is None and el["id"] == "title":
            anim.append({"id": eid, "order": 1, "duration": 300})
        elif el["type"] == "arrow":
            anim.append({"id": eid, "order": 3, "duration": 400})
        elif el["type"] == "text" and el.get("containerId") is None:
            anim.append({"id": eid, "order": 2})
        else:
            anim.append({"id": eid, "order": 2})
    return {"startMs": 400, "defaultDuration": 350, "elements": anim}


def emit(slug, elements):
    d = os.path.join(BASE, slug)
    os.makedirs(d, exist_ok=True)
    doc = {
        "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff"}, "files": {},
    }
    with open(os.path.join(d, "diagram.excalidraw"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    anim = build_animationinfo(elements)
    with open(os.path.join(d, "diagram.animationinfo.json"), "w", encoding="utf-8") as f:
        json.dump(anim, f, ensure_ascii=False, indent=1)
    print(f"wrote {slug}: {len(elements)} elements")


# ======================================================================
# Diagram 01 — opening scene: the category error
# ======================================================================
def d01():
    E = []
    E.append(text("title", 80, 50, "The postmortem that wasn't", fs=26))
    E.append(text("subtitle", 80, 100,
                  "Why \"the model hallucinated\" is a category error", fs=16))

    _, els = shape("ellipse", "msg", 250, 150, 250, 80, "Customer message\n(data)", fs=16)
    E += els
    _, els = shape("rectangle", "policy", 940, 150, 250, 80, "Standing policy\n(40% cap)", fs=16)
    E += els

    _, els = shape("rectangle", "gap", 470, 330, 440, 84,
                   "No policy-vs-data\ndistinction", fs=16)
    E += els

    # diagonals from the two inputs into the harness-gap box
    E.append(free_arrow("a_msg", 375, 230, 620, 330))
    E.append(free_arrow("a_policy", 1065, 230, 760, 330))

    _, els = shape("rectangle", "approve", 500, 490, 380, 80,
                   "Agent approves 40% off", fs=16)
    E += els
    E.append(v_arrow("a1", "gap", "approve", 690, 414, 490))

    _, els = shape("diamond", "diag", 550, 640, 280, 130, "Hallucinated?", fs=16)
    E += els
    E.append(v_arrow("a2", "approve", "diag", 690, 570, 640))
    E.append(text("wrong", 880, 690, "✗ category error", fs=16))

    _, els = shape("rectangle", "real", 470, 840, 440, 80,
                   "Followed the loudest instruction", fs=16)
    E += els
    E.append(v_arrow("a3", "diag", "real", 690, 770, 840))
    E.append(text("takeaway", 470, 950, "Salience, not hallucination", fs=18))
    return E


# ======================================================================
# Diagram 02 — nine failure classes (3x3 taxonomy)
# ======================================================================
def d02():
    E = []
    E.append(text("title", 80, 50, "Nine failure classes", fs=26))
    E.append(text("subtitle", 80, 100, "The catalog: what goes wrong, and why", fs=16))

    rows = [
        [
            ("1 · Hallucination", "fluent but false"),
            ("2 · Sycophancy", "agrees to please"),
            ("3 · Brittleness", "surface shortcuts"),
        ],
        [
            ("4 · Instruction drift", "early beats late"),
            ("5 · Position bias", "lost in middle"),
            ("6 · Reasoning load", "chains decay"),
        ],
        [
            ("7 · Overlooked limits", "goal, not limits"),
            ("8 · Tool errors", "wrong call / loop"),
            ("9 · Goal misspec", "literal, not meant"),
        ],
    ]
    colx = [80, 510, 940]
    rowy = [180, 360, 540]
    for r, row in enumerate(rows):
        for c, (name, hint) in enumerate(row):
            _, els = shape("rectangle", f"c{r}{c}", colx[c], rowy[r], 380, 140,
                           f"{name}\n{hint}", fs=16)
            E += els

    _, els = shape("rectangle", "take", 80, 760, 1240, 80,
                   "Takeaway — \"the model was wrong\" is never a diagnosis", fs=18)
    E += els
    return E


# ======================================================================
# Diagram 03 — attribution: who owns the failure
# ======================================================================
def d03():
    E = []
    E.append(text("title", 80, 50, "Who owns the failure?", fs=26))

    # harness box lightly tinted (the majority) — one neutral fill
    _, els = shape("rectangle", "cap", 80, 150, 380, 200,
                   "Model capability\n\nLow · rare, known ahead\nRoute around it", fs=16)
    E += els
    _, els = shape("rectangle", "harness", 510, 150, 380, 200,
                   "Harness design\n\nHigh · ~80%\nYou redesign the layer", fs=16,
                   fill="#f2f2f2")
    E += els
    _, els = shape("rectangle", "env", 940, 150, 380, 200,
                   "Environment\n\nRising · injection,\npoisoned tools", fs=16)
    E += els

    # 80/20 bar — widths proportional to 80:20 (992:248 of a 1240 span)
    _, els = shape("rectangle", "bar80", 80, 440, 992, 70, "Harness 80%", fs=18,
                   fill="#f2f2f2")
    E += els
    _, els = shape("rectangle", "bar20", 1072, 440, 248, 70, "Capability 20%", fs=18)
    E += els

    E.append(text("takeaway", 80, 560,
                  "Even capability limits are harness problems —\n"
                  "don't rely on the model where it's weakest.", fs=16))
    return E


# ======================================================================
# Diagram 04 — failure class -> harness layer map (9 rows)
# ======================================================================
def d04():
    E = []
    E.append(text("title", 80, 50, "Which layer catches it?", fs=26))

    rows = [
        ("1 · Hallucination", "M5 Grounding  +  M12 Eval"),
        ("2 · Sycophancy", "M12 Eval  +  M6 Instruction"),
        ("3 · Brittleness", "M12 Eval — adversarial sets"),
        ("4 · Instruction drift", "M6 Instruction  +  M7 Memory"),
        ("5 · Position bias", "M4 Context assembly"),
        ("6 · Reasoning load", "M10/M11 Orchestration"),
        ("7 · Overlooked limits", "M12 Eval  +  M6  +  M15 gates"),
        ("8 · Tool errors", "M8/M9 Tool interfaces"),
        ("9 · Goal misspec", "M15 Governance  +  M10 handoff"),
    ]
    y0 = 130
    step = 80
    for i, (cls, layer) in enumerate(rows):
        y = y0 + i * step
        _, els = shape("rectangle", f"cls{i}", 80, y, 400, 64, cls, fs=16)
        E += els
        _, els = shape("rectangle", f"lay{i}", 620, y, 640, 64, layer, fs=16)
        E += els
        E.append(h_arrow(f"a{i}", f"cls{i}", f"lay{i}", 480, 620, y + 32))

    E.append(text("takeaway", 80, y0 + 9 * step + 20,
                  "Read backwards: each layer's failure modes are already written here.", fs=16))
    return E


# ======================================================================
# Diagram 05 — contested boundaries (6 vs 4, 4 vs 5)
# ======================================================================
def d05():
    E = []
    E.append(text("title", 80, 50, "Contested boundaries", fs=26))

    E.append(frame("f1", 60, 130, 640, 540, "6 vs 4"))
    _, els = shape("rectangle", "c6", 110, 210, 520, 90, "6 · Reasoning load", fs=18)
    E += els
    E.append(text("c6h", 110, 300, "derived values lost across steps", fs=15))
    _, els = shape("rectangle", "c4a", 110, 360, 520, 90, "4 · Instruction drift", fs=18)
    E += els
    E.append(text("c4ah", 110, 450, "salience competition", fs=15))
    E.append(text("b1", 110, 540, "6 = chain depth  ·  4 = context salience", fs=16))

    E.append(frame("f2", 740, 130, 640, 540, "4 vs 5"))
    _, els = shape("rectangle", "c4b", 790, 210, 520, 90, "4 · Instruction drift", fs=18)
    E += els
    E.append(text("c4bh", 790, 300, "policy decays with length", fs=15))
    _, els = shape("rectangle", "c5", 790, 360, 520, 90, "5 · Position bias", fs=18)
    E += els
    E.append(text("c5h", 790, 450, "content-neutral U-curve", fs=15))
    E.append(text("b2", 790, 540, "4 = content competes  ·  5 = position only", fs=16))

    E.append(text("takeaway", 80, 720, "Different causal variable → different probe.", fs=18))
    return E


# ======================================================================
# Diagram 06 — tradeoff ledger
# ======================================================================
def d06():
    E = []
    E.append(text("title", 80, 50, "The attribution ledger", fs=26))

    # tension 1
    _, els = shape("rectangle", "trust", 100, 160, 260, 80, "Trust the model", fs=18)
    E += els
    _, els = shape("rectangle", "verify", 620, 160, 260, 80, "Verify the model", fs=18)
    E += els
    E.append(line("t1", 360, 200, 260, 0, dash=True))
    E.append(text("t1l", 340, 130, "cost = f(consequence)", fs=15))
    E.append(text("t1h", 100, 270, "Invest by consequence, not by model quality.", fs=16))

    # tension 2
    _, els = shape("rectangle", "demo", 100, 400, 280, 80, "Demo: short, one-domain", fs=16)
    E += els
    _, els = shape("rectangle", "prod", 620, 400, 280, 80, "Production: long, adversarial", fs=16)
    E += els
    E.append(line("t2", 380, 440, 240, 0, dash=True))
    E.append(text("t2h", 100, 510, "Design from the failure surface, not the demo's success surface.", fs=16))

    _, els = shape("rectangle", "take", 80, 620, 1240, 80,
                   "A 99.9% model still needs a gate before a binding message", fs=18)
    E += els
    return E


# ======================================================================
# Diagram 07 — what failure science gives the harness engineer
# ======================================================================
def d07():
    E = []
    E.append(text("title", 80, 50, "What failure science gives you", fs=26))

    _, els = shape("rectangle", "g1", 80, 160, 400, 240,
                   "A design method\n\nstart from the failure\ncatalog\nfault-tree thinking", fs=16)
    E += els
    _, els = shape("rectangle", "g2", 510, 160, 400, 240,
                   "A language\n\nprecise diagnoses\n→ work items\nnot vague alarm", fs=16)
    E += els
    _, els = shape("rectangle", "g3", 940, 160, 400, 240,
                   "A humility baseline\n\nirreducible failures\nmade cheap\ncontained + visible", fs=16)
    E += els

    _, els = shape("rectangle", "take", 80, 480, 1240, 80,
                   "caught · contained · visible · recoverable", fs=18)
    E += els
    return E


# ======================================================================
# Diagram 08 — design-exercise scenarios A / B / C
# ======================================================================
def d08():
    E = []
    E.append(text("title", 80, 50, "Design exercise — three incidents", fs=26))

    panels = [
        (60, "A · Summarizer", "dropped the\nliability clause",
         "7 · Overlooked limits", "omission, not\nfabrication",
         "Refuse:\n\"it hallucinated\""),
        (500, "B · Reviewer", "approved a\nbuggy PR",
         "2 · Sycophancy", "verdict flips with\nauthor confidence",
         "Refuse:\n\"it's biased\""),
        (940, "C · Escalation", "$400 refund at\nmessage 39",
         "4 + 5 · Drift + position", "policy decays\nwith context",
         "Refuse:\n\"it forgot\""),
    ]
    for i, (px, name, scen, cls, why, refuse) in enumerate(panels):
        E.append(frame(f"p{i}", px, 110, 400, 470, ""))
        _, els = shape("rectangle", f"s{i}", px + 20, 160, 360, 64, name, fs=16)
        E += els
        E.append(text(f"sc{i}", px + 20, 234, scen, fs=14))
        _, els = shape("rectangle", f"cl{i}", px + 20, 296, 360, 64, cls, fs=16,
                       fill="#f2f2f2")
        E += els
        E.append(text(f"wh{i}", px + 20, 368, why, fs=14))
        _, els = shape("rectangle", f"rf{i}", px + 20, 424, 360, 64, refuse, fs=15)
        E += els

    E.append(text("takeaway", 80, 640,
                  "Every root cause sits in a harness layer — not in \"the AI.\"", fs=18))
    return E


def main():
    diagrams = [
        ("01-category-error", d01),
        ("02-nine-failure-classes", d02),
        ("03-attribution-80-20", d03),
        ("04-class-to-layer-map", d04),
        ("05-contested-boundaries", d05),
        ("06-tradeoff-ledger", d06),
        ("07-what-failure-science-gives", d07),
        ("08-design-scenarios", d08),
    ]
    for slug, fn in diagrams:
        emit(slug, fn())


if __name__ == "__main__":
    main()
