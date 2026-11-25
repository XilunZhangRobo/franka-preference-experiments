"""Build the offline experiment index, focused trial pages and aggregate results."""
import os
from urllib.parse import quote
from collections import Counter
from hashlib import sha256
from html import escape
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
STUDY = BASE / "visual-interaction-study-v1"


SCENES = {
    'approach-side': 'A blue drinking cup sits between the white robot arm and the person, whose two hands rest near the table edge.',
    'cleaning-scent': 'Two different cleaner bottles stand in front of the person, with a folded blue cloth closer to the robot.',
    'completion-update': 'The person faces a paper on the work surface. Two small bins sit between the paper and the robot.',
    'gift-finishing': 'A loose pink flower lies in front of a card bearing a drawn stem. The person has both hands near the card.',
    'lighting': 'A desk lamp stands beside a small puzzle. Two rectangular controls are spaced across the table.',
    'material-order': 'A red base and a yellow cap sit apart on the tabletop, with the red piece on the person’s right.',
    'paused-work': 'A rust mat and a teal mat hold separate work arrangements. A small shelving unit stands behind them.',
    'private-storage': 'Keys and a flashlight sit in front of a brown compartment and an open teal tray.',
    'receiving-hand': 'A flashlight stands on the table. Both hands are empty, with the person’s right hand nearer the flashlight.',
    'vegetable-texture': 'Two portions of broccoli sit on separate square dishes beside a round dinner plate and a utensil.',
}


def read(path):
    return json.loads(path.read_text())


def url(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return escape(str(path.relative_to(BASE)), quote=True)


def link(path, label):
    return f'<a href="{url(path)}">{escape(label)}</a>'


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join(
        f'<th scope="col">{h}</th>' for h in headers
    ) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>' for row in rows
    ) + '</tbody></table></div>'


def outcome(value):
    return 'Matched' if value else 'Missed'


def frozen(families):
    rows = []
    notes = {sha256(p.read_bytes()).hexdigest(): p for p in (STUDY / "library").glob("*.md")}
    totals = Counter()
    paired = Counter()
    changes = {"Gains": [], "Losses": []}
    for family in families:
        for phase in ('transfer','exception'):
            directory = STUDY/'retention'/f'{family}-{phase}'
            identity = read(directory/'identity.json')
            options = identity['visible']['options']
            cells = []
            choices = []
            for stage in ('cold','retrieve','decision'):
                file = directory/stage/'receipt.json'
                if not file.exists():
                    cells.append('Pending')
                    choices.append(None)
                    continue
                receipt = read(file)
                if stage == 'retrieve':
                    selected = [notes[identity["notes"][key]] for key in receipt["ids"]]
                    titles = [link(p,p.read_text().splitlines()[0].lstrip("# ")) for p in selected]
                    cells.append((" · ".join(titles) or "No notes selected") + " (" + link(file,"receipt") + ")")
                    choices.append(None)
                else:
                    choice = receipt.get('choice')
                    if choice not in options:
                        cells.append(link(file,'Unscored'))
                        choices.append(None)
                        continue
                    matched = choice == identity['expected']
                    choices.append(matched)
                    cells.append(link(file,options[choice]+' · '+outcome(matched)))
                totals[stage] += 1
            if choices[0] is not None and choices[2] is not None:
                paired[phase] += 1
                paired[phase+'cold'] += choices[0]
                paired[phase+'library'] += choices[2]
                if choices[0] != choices[2]:
                    changes['Gains' if choices[2] else 'Losses'].append(family.replace('-', ' ') + (' transfer' if phase=='transfer' else ' scope control'))
            rows.append([link(directory/'first.jpg',family.replace('-',' ').title()),'Transfer' if phase=='transfer' else 'Scope control',*cells])
    summary = f'<p>Across 20 scenes, the archive contains {totals["cold"]} scored cold choices, {totals["retrieve"]} title selections and {totals["decision"]} scored choices with retrieved notes. Pending entries have no completed receipt.</p>'
    for phase, label in [('transfer','Transfer'),('exception','Scope control')]:
        n = paired[phase]
        if n:
            summary += f'<p>{label}, same {n} paired scenes · cold readers matched {paired[phase+"cold"]}/{n}, readers with retrieved notes matched {paired[phase+"library"]}/{n}.</p>'
    for label, cases in changes.items():
        summary += f'<p><strong>{label} among completed pairs</strong> · {", ".join(cases) or "None observed"}.</p>'
    return summary + table(['Scene image','Test','Fresh, no note','Retrieval','Fresh, retrieved notes'],rows)


def clarification_summary(revision):
    plan = read(revision / "plan.json")
    selected = read(revision / "selection.json")["selected"]
    rows = []
    interruptions = []
    for policy, label in (("legacy", "Original audit"), (selected, "Two-question audit")):
        run = revision / "holdout" / policy / "cases"
        cases = [read(run / family / "result.json") for family in plan["holdout"]]
        size = len(cases)
        audit = sum(bool(case["audit_question"]) for case in cases)
        decisions = [probe for case in cases for probe in case["probes"].values()]
        asked = sum(bool(probe["selective"]["question"]) for probe in decisions)
        interruptions.append((audit + asked, size + len(decisions)))
        def matches(phase, mode):
            return sum(case["probes"][phase]["post_answer"]["correct"] if mode == "note"
                       else case["probes"][phase]["selective"]["after_correct"] for case in cases)
        rows.append((label, f"{audit}/{size}", f"{asked}/{len(decisions)}",
                     f'{matches("transfer", "note")}/{size}', f'{matches("transfer", "action")}/{size}',
                     f'{matches("control", "action")}/{size}'))
    forks = [read(revision / "challenge" / selected / "cases" / f / "result.json")
             for f in ("color", "location")]
    final = sum(x["probes"]["transfer"]["selective"]["after_correct"] for x in forks)
    silent = read(revision / "challenge" / selected / "cases" / "silence" / "result.json")["quiet_checks"]
    return "".join((
        '<section id="questions"><h2>When to ask the person</h2>',
        '<p>Fresh agents replayed the same camera evidence using the original and revised audit. ',
        'Four scenario families were used for development. The table covers the six held back from prompt selection. ',
        'A fresh note reader received the written result of the audit. A separate robot could ask one question before its final action.</p>',
        table(["Policy", "Asked after demonstration", "Asked before action", "Note-only transfer",
               "Final transfer", "Final scope control"], rows),
        f'<p>Across all opportunities, the original policy asked {interruptions[0][0]}/{interruptions[0][1]} times ',
        f'and the revised policy asked {interruptions[1][0]}/{interruptions[1][1]}. ',
        'The revised writer retained the same note-only transfer score, while its acting agent missed more transfer choices. ',
        'The original policy remains the default.</p>',
        f'<p>In a separate test, two people made the same correction into a teal tray on their left. ',
        f'After the trays switched places they preferred opposite choices. The revised policy matched {final}/2 people. ',
        f'On a quiet replay it {"wrote a preference note" if silent["post_answer_note_written"] else "left memory empty"}. ',
        'These designed cases are reported separately from ordinary interruption rates.</p>',
        link(revision / "index.html", "Prompts, transcripts and clarification results"), '</section>',
    ))



MODES = {"isolated": "Fresh start", "continuous": "Continuous run", "contrast": "Contrasting preference"}
STAGES = {"action": "Robot action", "feedback": "Human response", "note": "Audit and note",
          "transfer": "Transfer", "control": "Scope control"}
TITLES = {"paused-work": "Paused work", "gift-finishing": "Gift finishing",
          "receiving-hand": "Receiving hand", "material-order": "Material order",
          "approach-side": "Approach side", "completion-update": "Completion updates",
          "vegetable-texture": "Vegetable texture", "private-storage": "Private storage",
          "lighting": "Lighting", "cleaning-scent": "Cleaning scent"}


def rel(page, target):
    """Both the live report and the extracted ZIP use the same relative references."""
    return escape(quote(os.path.relpath(target, page.parent), safe="/"), quote=True)


def anchor(page, target, label, fragment=""):
    href = rel(page, target) + ("#" + fragment if fragment else "")
    return f'<a href="{href}">{escape(label)}</a>'


def trial_path(family, mode):
    return BASE / "experiments" / family / f"{mode}.html"


def layout(page, title, body, family=None, mode=None):
    attr = f' data-family="{family}" data-mode="{mode}"' if family else ""
    home = BASE / "index.html"
    script = r'''
<script>
document.addEventListener("play", event => {
  if (event.target.tagName === "VIDEO") {
    document.querySelectorAll("video").forEach(player => {
      if (player !== event.target && !player.paused) player.pause();
    });
  }
}, true);
const picker = document.querySelector("#start-at");
if (picker) {
  const updateTrialLinks = () => {
    document.querySelectorAll(".card a[href]").forEach(link => {
      if (/\/(isolated|continuous|contrast)\.html$/.test(link.pathname)) link.hash = picker.value;
    });
  };
  picker.addEventListener("change", updateTrialLinks);
  window.addEventListener("pageshow", updateTrialLinks);
}
const markPhase = () => {
  document.querySelectorAll(".stage-nav a").forEach(link => {
    if (link.hash === (location.hash || "#action")) link.setAttribute("aria-current", "location");
    else link.removeAttribute("aria-current");
  });
};
markPhase();
window.addEventListener("hashchange", () => {
  markPhase();
  document.querySelectorAll("video").forEach(player => player.pause());
});
</script>'''
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><title>{escape(title)} · Robot personalization</title>'
            f'<link rel="stylesheet" href="{rel(page, BASE/"report.css")}"></head><body{attr}>'
            f'<a class="skip" href="#main">Skip to content</a><header class="bar"><div class="wrap mast">'
            f'{anchor(page, home, "Robot personalization")}<nav aria-label="Report">'
            f'{anchor(page, home, "Experiments","experiments")}{anchor(page, BASE/"study-results.html","Study results")}'
            f'</nav></div></header><main id="main" class="wrap">{body}</main>{script}</body></html>')


def write_page(page, html):
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")


def note_text(text):
    if not text.strip():
        return '<p>No preference note was written.</p>'
    paragraphs = text.strip().split('\n\n')
    title = paragraphs.pop(0) if paragraphs[0].startswith("# ") else None
    return (f'<p class="note-title">{escape(title[2:])}</p>' if title else "") + "".join(
        f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def player(page, manifest, key):
    item = manifest[key]
    asset = BASE / item["file"]
    if not asset.is_file() or item["duration"] <= 0:
        raise ValueError(f"Missing {key} video for {page}")
    poster = f' poster="{rel(page, BASE/item["poster"])}"' if item.get("poster") else ""
    alternative = item.get("mp4")
    fallback = ""
    if alternative and alternative != item["file"]:
        fallback = " · " + anchor(page, BASE/alternative, "Open MP4")
    return (f'<figure><video src="{rel(page, asset)}" controls playsinline preload="none"{poster} '
            f'aria-label="{STAGES[key]} video"></video><figcaption>{STAGES[key]} · {item["duration"]:.1f} s'
            f'{fallback}</figcaption></figure>')


def one(turns, channel):
    matches = [t for t in turns if t["channel"] == channel]
    if len(matches) != 1:
        raise ValueError(f"Expected one {channel} in phase, found {len(matches)}")
    return matches[0]


def divide_phases(turns):
    transfer = turns.index(one(turns, "new task"))
    control = turns.index(one(turns, "scope control"))
    return turns[:transfer], turns[transfer:control], turns[control:]


def exchange(turns):
    roles = {"question to person": "Robot asked", "spoken answer to robot": "Person answered"}
    relevant = [t for t in turns if t["channel"] in roles]
    return "".join(f'<p class="speech"><strong>{roles[t["channel"]]}</strong> {escape(t["text"])}</p>'
                   for t in relevant)


def task_text(text):
    return f'<p class="command">“{escape(text)}”</p>'


def matched(is_match):
    return f'<span class="status {"matched" if is_match else "missed"}">{outcome(is_match)}</span>'


def show_probe(page, key, turns, scores, clips, expected):
    comparison = []
    for channel, label, suffix in (("cold comparison","Fresh reader without a note","cold"),
                                   ("note comparison","Fresh reader with the note","note"),
                                   ("executed probe action","Continuing robot","learner")):
        comparison.append((label, escape(one(turns,channel)["text"]), matched(scores[f"{key}_{suffix}"])))
    edits = [t for t in turns if t["channel"] == "refines personal note"]
    revised = "".join('<details><summary>Updated note after the answer</summary>' +
                      note_text(t["text"]) + '</details>' for t in edits)
    return (f'<section class="phase" id="{key}"><h2>{STAGES[key]}</h2>' + task_text(turns[0]["text"])
            + player(page, clips, key) + exchange(turns) + f'<p><strong>Assigned action</strong> {escape(expected)}</p>'
            + table(["Who chose","Decision and reason","Preference match"], comparison) + revised + '</section>')


def family_page(episode, family_modes, clips, scored):
    family, mode = episode["scenario"], episode["mode"]
    page = trial_path(family, mode)
    folder = STUDY / "episodes" / mode / family
    teach, transfer, control = divide_phases(episode["turns"])
    cmd = one(teach, "task command")
    first = one(teach, "selected action")
    human = one(teach, "private motion command to simulator")
    audit = read(folder/"receipts/audit.json")["reply"]
    scores = episode["scores"]
    tabs = "".join(f'<a href="{rel(page, trial_path(family, m))}"' +
                   (' aria-current="page"' if m == mode else '') + f'>{MODES[m]}</a>'
                   for m in family_modes)
    tabs += anchor(page, page.parent/"checks.html", "Follow-up checks")
    stage_nav = "".join(f'<a href="#{k}">{v}</a>' for k,v in STAGES.items())
    start = ('New robot and person threads with empty preference memory.' if mode == "isolated" else
             'Fresh threads. The experimenter selected a prewritten preference that disagreed with the opening action.' if mode == "contrast" else
             f'The same robot and person continued across tasks. The robot began this trial with {len(read(folder/"library-before.json"))} earlier written notes.')
    title = TITLES[family]
    header = (f'<div class="back">{anchor(page,BASE/"index.html","← All experiments","experiments")}</div>'
              f'<h1>{title}</h1><nav class="tabs" aria-label="Trials for {title}">{tabs}</nav>'
              f'<p class="context">{MODES[mode]} · {start}</p>')
    side = (f'<aside class="phase-rail"><nav class="stage-nav" aria-label="Interactions in this trial">{stage_nav}</nav>'
            f'<div class="related">{anchor(page, folder/"transcript.json", "Trial transcript")}<br>'
            f'{anchor(page, folder/"calls.json", "Model call index")}</div></aside>')
    before_notes = read(folder/"library-before.json")
    starting_memory = ('<details><summary>Notes available before this trial</summary>' +
                       "".join(note_text(body) for body in before_notes.values()) + '</details>' if before_notes else '')
    action = (f'<section id="action" class="phase"><h2>{STAGES["action"]}</h2>{task_text(cmd["text"])}'
              f'<p>{escape(SCENES[family])}</p>{starting_memory}{player(page,clips,"action")}'
              f'<p>{escape(first["text"])}</p><p><strong>Assigned action</strong> {escape(scored["preferred_teaching_action"])}</p><p>First choice · {matched(not scores["teaching_miss"])}</p>'
              f'<details><summary>Starting camera image</summary><img width="640" height="480" '
              f'src="{rel(page,STUDY/cmd["image"])}" loading="lazy" alt="{escape(SCENES[family])}"></details></section>')
    heard = "".join(f'<p class="speech"><strong>Person said</strong> {escape(t["text"])}</p>'
                    for t in teach if t["channel"] == "simulated utterance")
    response = (f'<section id="feedback" class="phase"><h2>{STAGES["feedback"]}</h2>'
                +player(page,clips,"feedback")+f'<p><strong>Simulated response</strong> {escape(human["text"])}</p>'
                +heard+'</section>')
    draft, clarified = [(folder/name).read_text() for name in ("visual-only.md","memory.md")]
    notes = (f'<section id="note" class="phase"><h2>{STAGES["note"]}</h2>'
             f'<dl><dt>What the robot observed</dt><dd>{escape(audit["observation"])}</dd>'
             f'<dt>How it interpreted the response</dt><dd>{escape(audit["interpretation"])}</dd></dl>')
    if draft!=clarified:
        notes += '<details><summary>Visual draft before clarification</summary>'+note_text(draft)+'</details>'
    notes += exchange(teach)+'<h3>Written memory used for transfer</h3><div class="note">'+note_text(clarified)+'</div></section>'
    footer = '<p class="next">'+anchor(page,page.parent/"checks.html",f'Follow-up checks for {title.lower()} →')+'</p>'
    return layout(page, title+" · "+MODES[mode], header+'<div class="reader">'+side+'<article>'+action+response+notes+
                  show_probe(page,'transfer',transfer,scores,clips,scored["probes"]["transfer"]["expected"])+show_probe(page,'control',control,scores,clips,scored["probes"]["exception"]["expected"])+
                  footer+'</article></div>', family, mode)


def aggregate_results(episodes, families):
    page = BASE/"study-results.html"
    rows = []
    for mode in ("isolated","contrast","continuous"):
        group = [e["scores"] for e in episodes if e["mode"]==mode]
        n=len(group)
        def rate(key):
            return f'{sum(g[key] for g in group)}/{n}'
        rows.append([MODES[mode],rate("teaching_miss"),rate("transfer_cold"),rate("transfer_note"),rate("transfer_learner"),
                     " / ".join(rate("control_"+field) for field in ("cold","note","learner"))])
    summary=read(STUDY/"summary.json")
    drafts=summary["visual_comparisons"]
    draft_scores=[sum(v[k] for v in drafts) for k in ("cold_correct","draft_correct","note_correct")]
    parts=['<h1>Study results</h1><nav class="tabs"><a href="#trials">Trial outcomes</a><a href="#library">Frozen library</a><a href="#questions">Clarification</a><a href="#evidence">Evidence</a></nav>',
           '<section id="trials"><h2>Trial outcomes</h2><p>Two Astra agents played the robot and the person. The person had a prewritten preference. The robot saw camera frames of the response and could ask a question. Each reader made one choice per scene.</p>',
           table(["Trials","Initial misses","Transfer without note","Transfer with note","Continuing robot on transfer","Scope controls without note / with note / continuing"],rows),
           f'<p>On the {len(drafts)} fresh-start trials where clarification changed the note, fresh readers matched the transfer choice on {draft_scores[0]}/{len(drafts)} without notes, {draft_scores[1]}/{len(drafts)} with the visual draft, and {draft_scores[2]}/{len(drafts)} after the answer.</p>',
           '<p>Four contrasts used an opposing preference selected after the opening action. Their initial mismatches were induced. These simulated choices do not measure physical reliability or human comfort.</p></section>',
           '<section id="library"><h2>Frozen ten-note library</h2><p>These tests used fresh readers on new layouts with familiar commands. Some notes already contained answers about those tasks. Selection and action were separate calls.</p>',frozen(families),'</section>',
           clarification_summary(BASE/'audit-revision'),
           '<section id="evidence"><h2>Supporting evidence</h2><ul>']
    for file,label in ((STUDY/"index.html","Complete research archive and original films"),
                       (STUDY/"corrections.html","Selected correction trials"),
                       (BASE/"clarification-analysis.md","Questions that changed an action"),
                       (BASE/"audit-revision/index.html","Audit replay records"),
                       (STUDY/"evidence-validation.json","Evidence verification"),
                       (BASE/"trial-clips/manifest.json","Clip sources and time boundaries")):
        parts.append(f'<li>{anchor(page,file,label)}</li>')
    parts.append('</ul></section>')
    write_page(page,layout(page,"Study results","".join(parts)))


def main():
    from report_supplements import build_supplements

    families=read(STUDY/"plan.json")["families"]
    episodes=read(STUDY/"report_manifest.json")["episodes"]
    scored = {(e["mode"],e["family"]):e for e in read(STUDY/"summary.json")["episodes"]}
    clips=read(BASE/"trial-clips/manifest.json")
    if set(clips)!={f'{e["mode"]}/{e["scenario"]}' for e in episodes}:
        raise ValueError("Clip manifest and recorded trials disagree")
    build_supplements(BASE)
    aggregate_results(episodes,families)
    page=BASE/"index.html"
    parts=['<h1>Robot personalization</h1><p class="lede">Ten experiments with a simulated Franka arm. Choose a trial to see its robot action, the person’s response, the memory it produced, and what happened on transfer.</p>',
           '<nav class="index-links"><a href="#experiments">Browse experiments ↓</a> · <a href="study-results.html">Study results</a></nav>',
           '<section id="experiments"><div class="index-tools"><h2>Experiments</h2><label>Open trials at <select id="start-at"><option value="">Start of trial</option>' + "".join(f'<option value="{k}">{v}</option>' for k,v in STAGES.items()) + '</select></label></div><div class="cards">']
    for family in families:
        group={e['mode']:e for e in episodes if e['scenario']==family}
        modes=[m for m in MODES if m in group]
        for mode in modes:
            write_page(trial_path(family,mode),family_page(group[mode],modes,clips[f'{mode}/{family}'],scored[mode,family]))
        command=one(group['isolated']['turns'],'task command')
        opening=trial_path(family,'isolated')
        links="".join(anchor(page,trial_path(family,m),MODES[m]) for m in modes)
        links+=anchor(page,opening.parent/'checks.html','Follow-up checks')
        parts.append(f'<article class="card" id="{family}"><a class="cover" href="{rel(page,opening)}" aria-label="Open {TITLES[family]} fresh-start trial"><img src="{rel(page,STUDY/command["image"])}" width="640" height="480" loading="lazy" alt="{escape(SCENES[family])}"></a><div class="card-copy"><h3>{anchor(page,opening,TITLES[family])}</h3>{task_text(command["text"])}<nav aria-label="Trials for {TITLES[family]}">{links}</nav></div></article>')
    parts+=['</div></section><section id="library"><h2>Across experiments</h2><ul>',
            '<li><a href="study-results.html#library">What carried over from the frozen library?</a></li>',
            '<li id="questions"><a href="study-results.html#questions">When did clarification help?</a></li>',
            '<li><a href="experiments/tray-choice/checks.html">Tray choice and non-intervention controls</a></li></ul></section>']
    write_page(page,layout(page,"Experiments","".join(parts)))
    print(f"Built {len(episodes)} focused trial pages across {len(families)} experiments.")


if __name__ == "__main__":
    main()
