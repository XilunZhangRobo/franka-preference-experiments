"""Write offline reports for the frozen audit replay study. Makes no model calls."""

import argparse
import html
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import quote

PHASES = ("transfer", "control")
STAGES = [
    ("dev", "Development scenes"),
    ("holdout", "Withheld original scenes"),
    ("fork", "Matched ambiguity on the new tray task"),
    ("silence", "Robot-only negative control"),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def link(root, label, path):
    path = path.resolve()
    rel = path.relative_to(root)
    if not path.is_file():
        raise FileNotFoundError(path)
    return f"[{label}]({quote(rel.as_posix(), safe='/')})"


def text_html(value):
    pieces = re.split(r"(\[[^\]]+\]\([^\s)]+\))", str(value))
    out = []
    for part in pieces:
        match = re.fullmatch(r"\[([^\]]+)\]\(([^\s)]+)\)", part)
        if match:
            label, href = match.groups()
            out.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
        else:
            out.append(html.escape(part))
    return "".join(out)


class Report:
    def __init__(self):
        self.md = ["# Audit and clarification study"]
        self.html = [
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>Audit and clarification study</title><style>"
            "body{max-width:86rem;margin:2rem auto;padding:0 1rem;font:16px/1.5 system-ui;"
            "color:#172b35;background:#f8f8f4}.scroll{overflow-x:auto}"
            "td,th{padding:.3rem .55rem;border-bottom:1px solid #bdc8c6;text-align:left;"
            "vertical-align:top}table{border-collapse:collapse}pre{white-space:pre-wrap;"
            "overflow-wrap:anywhere}a{color:#095d68}summary{cursor:pointer}details{margin:.6rem 0}"
            "</style><main><h1>Audit and clarification study</h1>"
        ]

    def heading(self, label, anchor):
        self.html.append(f'<h2 id="{anchor}">{html.escape(label)}</h2>')
        self.md.append(f"## {label}")

    def paragraph(self, message):
        self.html.append("<p>" + text_html(message) + "</p>")
        self.md.append(message)

    def table(self, headers, rows):
        self.html.append(
            '<div class="scroll"><table><thead><tr>'
            + "".join("<th>" + text_html(v) + "</th>" for v in headers)
            + "</tr></thead><tbody>"
        )
        self.md.append("| " + " | ".join(headers) + " |\n|" + "---|" * len(headers))
        for row in rows:
            self.html.append(
                "<tr>" + "".join("<td>" + text_html(v) + "</td>" for v in row) + "</tr>"
            )
            self.md[-1] += "\n| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |"
        self.html.append("</tbody></table></div>")


def rate(n, d):
    return f"{n}/{d} ({n / d:.0%})" if d else "0/0 (no opportunities)"


def rows_for(root, stage, label, cases):
    folder = root / ("challenge" if stage in ("fork", "silence") else stage) / label / "cases"
    rows = []
    for case in cases:
        base = (folder / case).resolve()
        base.relative_to(root)
        path = base / "result.json"
        result = read(path) if path.is_file() else None
        if result and (
            result["case_id"] != case
            or set(result["probes"]) != (set() if stage == "silence" else set(PHASES))
        ):
            raise ValueError(f"Unexpected result identity or phase set at {path}")
        rows.append((case, base, result))
    return rows


def counts(rows, quiet=False):
    c = Counter(planned=len(rows), planned_probes=0 if quiet else 2 * len(rows))
    for _, _, result in rows:
        if result is None:
            continue
        c["complete"] += 1
        asked = bool(result["audit_question"])
        c["audit_asked"] += asked
        interrupted = asked
        for phase, p in result["probes"].items():
            decision = p["selective"]
            q = bool(decision["question"])
            interrupted |= q
            c["probe_asked"] += q
            c["seen_probes"] += 1
            for field in ("draft", "post_answer"):
                c[phase + "_" + field] += p[field]["correct"]
            for key in ("before_correct", "after_correct"):
                c[phase + "_" + key] += decision[key]
            for tag, eligible, before, after, changed in (
                (
                    "audit",
                    asked,
                    p["draft"]["correct"],
                    p["post_answer"]["correct"],
                    p["draft"]["reply"]["choice"] != p["post_answer"]["reply"]["choice"],
                ),
                (
                    "prospective",
                    q,
                    decision["before_correct"],
                    decision["after_correct"],
                    decision["tentative"]["choice"] != decision["final"]["choice"],
                ),
            ):
                if eligible:
                    c[tag + "_conditional"] += 1
                    c[tag + "_gains"] += int(after and not before)
                    c[tag + "_losses"] += int(before and not after)
                    c[tag + "_changed"] += changed
        c["any_asked"] += interrupted
    return c


def assessments(groups, selected):
    if selected is None:
        return "Default assessment is pending the frozen policy selection."
    legacy = groups.get(("holdout", "legacy"), [])
    candidate = groups.get(("holdout", selected), [])
    needed = [
        *legacy,
        *candidate,
        *groups.get(("fork", "legacy"), []),
        *groups.get(("silence", "legacy"), []),
        *groups.get(("fork", selected), []),
        *groups.get(("silence", selected), []),
    ]
    if selected == "legacy" or not needed or any(r is None for _, _, r in needed):
        return "Default assessment is inconclusive because a complete independent comparison is unavailable."
    a, b = counts(legacy), counts(candidate)
    safer = all(b[p + "_post_answer"] >= a[p + "_post_answer"] for p in PHASES)
    fewer = b["audit_asked"] + b["probe_asked"] < a["audit_asked"] + a["probe_asked"]
    fork = [r for _, _, r in groups["fork", selected]]
    quiet = groups["silence", selected][0][2]
    resolved = all(
        (r["audit_question"] or r["probes"]["transfer"]["selective"]["question"])
        and r["probes"]["transfer"]["selective"]["after_correct"]
        for r in fork
    )
    quiet_ok = not any(quiet["quiet_checks"].values())
    if safer and fewer and resolved and quiet_ok:
        return (
            f"{selected} is a provisional default for these simulator tasks. It asked fewer "
            "questions on withheld cases, preserved both written-note scores, obtained correct "
            "final choices across both tray profiles with clarification, and stayed silent on "
            "the quiet case. A fresh sample would test whether these observations recur."
        )
    return (
        f"A default change to {selected} is inconclusive. The observed combination of question "
        "burden, written transfer and control scores, matched-fork decisions, and quiet-scene "
        "behavior does not establish a consistent advantage on this small sample."
    )


def call_evidence(root, base, report):
    transcript = base / "transcript.json"
    if not transcript.exists():
        return
    items = []
    for turn in read(transcript):
        path = (base / (turn.get("source") or turn["receipt"])).resolve()
        path.relative_to(root)
        receipt = read(path)
        donor_base = path.parent.parent
        req = donor_base / receipt["request"]
        raw = donor_base / receipt["result"]
        links = [link(root, "Exact request", req), link(root, "Reply", raw)]
        prompt = req.with_name("prompt.txt")
        if prompt.exists():
            links.append(link(root, "Prompt text", prompt))
        events = raw.with_name("events.jsonl")
        if events.exists():
            links.append(link(root, "Raw events", events))
        for i, img in enumerate(read(req).get("images", []), 1):
            links.append(link(root, f"Frame {i}", req.parent / img["file"]))
        items.append(
            "<li>" + html.escape(turn["stage"]) + " · " + text_html(" · ".join(links)) + "</li>"
        )
    report.html.append(
        "<details><summary>Call inputs and replies · "
        + html.escape(base.parent.parent.name + " / " + base.name)
        + "</summary><ol>"
        + "".join(items)
        + "</ol></details>"
    )


def show_scores(probe):
    forced = [
        probe[k]["reply"]["choice"] + (" ✓" if probe[k]["correct"] else " ×")
        for k in ("draft", "post_answer")
    ]
    sel = probe["selective"]
    choices = [
        sel[k]["choice"] + (" ✓" if sel[score] else " ×")
        for k, score in (("tentative", "before_correct"), ("final", "after_correct"))
    ]
    return f"{' → '.join(forced)} / {' → '.join(choices)}" + (" (asked)" if sel["question"] else "")


def section(report, root, stage, title, groups, labels):
    report.heading(title, stage)
    if stage == "fork":
        report.paragraph(
            "Color and location are two private preferences for one visible teaching history. "
            "They share one visual draft per policy. A tentative probe decision can also be "
            "shared when its input is identical. Profile counts below are paired branches."
        )
    if stage == "silence":
        report.paragraph(
            "This robot-only rehearsal offers one audit opportunity per policy and no probes."
        )
    stats, scores, changes, cases, evidence, flags = [], [], [], [], [], []
    conversations = []
    for label in labels:
        rows = groups[stage, label]
        c = counts(rows, stage == "silence")
        stats.append(
            [
                label,
                f"{c['complete']}/{c['planned']}",
                c["planned"] - c["complete"],
                rate(c["any_asked"], c["planned"]),
                rate(c["audit_asked"], c["planned"]),
                rate(c["probe_asked"], c["planned_probes"]),
            ]
        )
        if stage in ("dev", "holdout") and c["complete"]:
            heavy = []
            for key, den, name in (
                ("audit_asked", "complete", "audit"),
                ("probe_asked", "seen_probes", "prospective"),
            ):
                if c[key] * 5 > c[den]:
                    heavy.append(f"{name} {rate(c[key], c[den])}")
            if heavy:
                flags.append(
                    f"{label} exceeded the study’s soft one-in-five asking guide on completed "
                    f"opportunities ({'; '.join(heavy)})."
                )
        if stage != "silence":
            for phase in PHASES:
                scores.append(
                    [label, phase]
                    + [
                        f"{c[phase + '_' + key]}/{c['planned']}"
                        for key in ("draft", "post_answer", "before_correct", "after_correct")
                    ]
                )
            for tag in ("audit", "prospective"):
                d = c[tag + "_conditional"]
                n = c["planned_probes"]
                changes.append(
                    [
                        label,
                        tag,
                        d,
                        rate(c[tag + "_changed"], d),
                        rate(c[tag + "_gains"], d),
                        rate(c[tag + "_losses"], d),
                        rate(c[tag + "_gains"], n),
                        rate(c[tag + "_losses"], n),
                    ]
                )
        for case, base, r in rows:
            if r is None:
                status = "Started, incomplete" if base.exists() else "No result"
                cases.append([label, case, status, "—", "—", "—"])
                continue
            links = [
                link(root, label_, base / filename)
                for label_, filename in (
                    ("Draft", "draft.md"),
                    ("Post-answer note", "post-answer.md"),
                    ("Calls", "transcript.json"),
                    ("Scores", "result.json"),
                    ("Inputs", "identity.json"),
                )
            ]
            if stage == "silence":
                qc = r["quiet_checks"]
                if qc["draft_note_written"] or qc["post_answer_note_written"]:
                    flags.append(
                        f"{label} wrote a spurious preference note on the quiet case "
                        f"(draft {'present' if qc['draft_note_written'] else 'empty'}, "
                        f"final {'present' if qc['post_answer_note_written'] else 'empty'})."
                    )
                else:
                    flags.append(f"{label} left both quiet-scene notes empty.")
            elif stage == "fork":
                fork = r["probes"]["transfer"]["selective"]
                if not r["audit_question"] and not fork["question"]:
                    flags.append(
                        f"{label} reached the {case} fork without asking at audit or decision; "
                        f"its final choice was {'correct' if fork['after_correct'] else 'incorrect'}."
                    )
            cells = [show_scores(r["probes"][p]) if p in r["probes"] else "—" for p in PHASES]
            cases.append(
                [
                    label,
                    case,
                    "Asked" if r["audit_question"] else "Silent",
                    *cells,
                    " · ".join(links),
                ]
            )
            evidence.append(base)
            if r["audit_question"] or any(p["selective"]["question"] for p in r["probes"].values()):
                turns = []
                if r["audit_question"]:
                    turns.extend(["Audit", r["audit_question"], r["audit_answer"]])
                for phase, p in r["probes"].items():
                    sel = p["selective"]
                    if sel["question"]:
                        turns.extend(
                            [
                                phase,
                                sel["question"],
                                sel["answer"],
                                f"{sel['tentative']['choice']} → {sel['final']['choice']}",
                            ]
                        )
                conversations.append(
                    "<details><summary>"
                    + html.escape(label + " / " + case)
                    + " · Questions and answers</summary><pre>"
                    + html.escape("\n".join(turns))
                    + "</pre></details>"
                )
    report.table(
        [
            "Policy",
            "Completed/planned",
            "Missing results",
            "Episodes interrupted",
            "Audit questions",
            "Prospective questions",
        ],
        stats,
    )
    if scores:
        report.table(
            [
                "Policy",
                "Probe",
                "Draft correct",
                "Post-answer correct",
                "Tentative correct",
                "Final correct",
            ],
            scores,
        )
        report.table(
            [
                "Policy",
                "Answer stage",
                "Affected probes",
                "Changed choice / affected",
                "Gains / affected",
                "Losses / affected",
                "Gains / planned",
                "Losses / planned",
            ],
            changes,
        )
    if len(labels) > 1 and stage != "silence":
        paired = []
        for label in labels:
            if label == "legacy":
                continue
            for phase in PHASES:
                for arm in ("post_answer", "selective"):
                    pairs = []
                    for (_, _, a), (_, _, b) in zip(
                        groups[stage, "legacy"], groups[stage, label], strict=True
                    ):
                        if a is not None and b is not None:

                            def hit(result):
                                value = result["probes"][phase][arm]
                                return (
                                    value["after_correct"]
                                    if arm == "selective"
                                    else value["correct"]
                                )

                            pairs.append((hit(a), hit(b)))
                    paired.append(
                        [
                            label,
                            phase,
                            "Written note" if arm == "post_answer" else "Selective final",
                            len(pairs),
                            sum(not a and b for a, b in pairs),
                            sum(a and not b for a, b in pairs),
                        ]
                    )
        report.table(
            ["Policy vs legacy", "Probe", "Decision", "Paired scenes", "Gains", "Losses"], paired
        )
    for flag in flags:
        report.paragraph(flag)
    report.table(
        ["Policy", "Scene", "Audit", "Transfer choices", "Control choices", "Evidence"], cases
    )
    report.html.extend(conversations)
    for base in evidence:
        call_evidence(root, base, report)


def original_reference(report, core, plan, stage):
    rows = []
    for family in plan[stage]:
        path = core / "episodes" / "isolated" / family / "episode.json"
        rows.append(read(path)["scores"] if path.is_file() else None)
    complete = [r for r in rows if r is not None]
    scores = []
    for phase in PHASES:
        cells = [
            f"{sum(r[phase + '_' + arm] is True for r in complete)}/{len(rows)}"
            for arm in ("cold", "note", "learner")
        ]
        scores.append([phase, *cells])
    report.paragraph(
        f"Archived original isolated episodes on these same families "
        f"({len(complete)}/{len(rows)} available). The original learner retained its "
        "conversation. The fresh legacy replay above is the matched policy comparison."
    )
    report.table(["Archived original probe", "Cold", "Written note", "Episode learner"], scores)


def generate(directory, original=None):
    root = Path(directory).resolve()
    plan = read(root / "plan.json")
    policy_files = sorted((root / "policies").glob("*.json"))
    selection = root / "selection.json"
    selected = read(selection)["selected"] if selection.is_file() else None
    dev_labels = list(
        dict.fromkeys(
            [
                "legacy",
                *(p.stem for p in policy_files),
                *(p.name for p in sorted((root / "dev").glob("*")) if p.is_dir()),
            ]
        )
    )
    if len(dev_labels) == 1:
        dev_labels.append("selective-v1")
    locked = list(dict.fromkeys(["legacy", selected or "selective-v1"]))
    cases = {
        **{k: plan[k] for k in ("dev", "holdout")},
        "fork": ["color", "location"],
        "silence": ["silence"],
    }
    groups = {
        (stage, label): rows_for(root, stage, label, cases[stage])
        for stage, _ in STAGES
        for label in (dev_labels if stage == "dev" else locked)
    }
    report = Report()
    report.paragraph(assessments(groups, selected))
    report.paragraph(
        " · ".join(
            [link(root, "Locked plan", root / "plan.json")]
            + ([link(root, "Frozen selection", selection)] if selection.is_file() else [])
        )
    )
    report.html.append(
        "<nav>"
        + " · ".join(f'<a href="#{key}">{label}</a>' for key, label in STAGES)
        + ' · <a href="#prompts">Exact prompts</a></nav>'
    )
    report.paragraph(
        "Question rates and correct counts use the full planned denominator. Missing results "
        "appear separately. An interrupted episode means the robot asked the person at least "
        "once. In a scene cell, the first arrow compares fresh decisions using draft and "
        "post-answer notes. The second follows the prospective robot from tentative to final "
        "action. ✓ marks a correct action and × a miss."
    )
    report.paragraph(
        "An audit answer affects both eligible probes. A prospective answer affects its "
        "own probe. A gain changes an incorrect choice to correct; a loss reverses it. "
        "Fresh note readers can differ through sampling. These comparisons cannot isolate "
        "a question’s causal effect."
    )
    for stage, title in STAGES:
        section(report, root, stage, title, groups, dev_labels if stage == "dev" else locked)
        if original is not None and stage in ("dev", "holdout"):
            original_reference(report, Path(original).resolve(), plan, stage)
    report.heading("Exact policy prompts", "prompts")
    for path in policy_files:
        policy = read(path)
        report.paragraph(link(root, path.stem + " prompt file", path))
        for field in ("audit", "refine", "decide", "selective", "answer"):
            if field in policy:
                report.html.append(
                    f"<details><summary>{html.escape(path.stem)} · {field}</summary><pre>"
                    f"{html.escape(policy[field])}</pre></details>"
                )
    report.html.append("</main></html>")
    with tempfile.TemporaryDirectory(dir=root) as td:
        for name, chunks in (("analysis.md", report.md), ("index.html", report.html)):
            path = Path(td) / name
            path.write_text(
                ("\n\n" if name.endswith(".md") else "\n").join(chunks) + "\n", encoding="utf-8"
            )
            os.replace(path, root / name)
    return root / "index.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--original", type=Path, help="Optional original interaction study directory"
    )
    args = parser.parse_args()
    print(generate(args.directory, args.original))
