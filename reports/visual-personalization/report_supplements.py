"""Build focused experiment pages from the archived visual choices and replays."""
import hashlib
import json
import os
import subprocess
from tempfile import TemporaryDirectory
from html import escape
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def outcome(correct):
    return 'Matched' if correct else 'Missed'


class Page:
    def __init__(self, base, family):
        self.base = base
        self.directory = base / 'experiments' / family

    def url(self, path):
        return escape(os.path.relpath(path, self.directory), quote=True)

    def link(self, path, label):
        return f'<a href="{self.url(path)}">{escape(label)}</a>'

    def image(self, path, label):
        return f'<img src="{self.url(path)}" alt="{escape(label)}" loading="lazy" style="max-width:100%;height:auto">'

    def clip(self, path, poster, label, filename):
        webm = self.directory / "media" / filename
        if not webm.is_file():
            raise FileNotFoundError(f"Run build_supplement_media first: {webm}")
        return (f'<video controls preload="none" poster="{self.url(poster)}" '
                f'aria-label="{escape(label)}" style="width:40rem;max-width:100%" src="{self.url(webm)}"></video>'
                f'<p>{self.link(path, "Original MP4")}</p>')

    def write(self, title, nav, sections):
        self.directory.mkdir(parents=True, exist_ok=True)
        top = '<a href="../../index.html">Report overview</a>'
        if self.directory.name != 'tray-choice':
            top += ' · <a href="isolated.html">Isolated episode</a>'
        body = ''.join(sections)
        (self.directory / 'checks.html').write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><link rel="stylesheet" href="../../report.css"></head>'
            f'<body><main><nav>{top}</nav><h1>{escape(title)}</h1><nav>{nav}</nav>{body}</main></body></html>')


def frozen(page, study, family, notes):
    content = ['<section id="library"><h2>Frozen-library choices</h2>'
               '<p>Each scene went to a fresh reader with no notes, a separate title selector, '
               'and a fresh reader with the selected notes. The assigned action sets the score.</p>']
    for stage, title in [('transfer', 'Transfer'), ('exception', 'Scope control')]:
        directory = study / 'retention' / f'{family}-{stage}'
        record = read(directory / 'identity.json')
        scene = record['visible']
        options = scene['options']
        content.extend([f'<article id="library-{stage}"><h3>{title}</h3><p>{escape(scene["task"])}</p>',
                        page.image(directory / 'first.jpg', f'{title} scene for {family}'),
                        f'<p><strong>Assigned action</strong> · {escape(options[record["expected"]])}</p>'])
        for role, actor in [('cold', 'Without notes'), ('retrieve', 'Selected notes'), ('decision', 'With selected notes')]:
            receipt = directory / role / 'receipt.json'
            result = read(receipt)
            if role == 'retrieve':
                selected = [notes[record['notes'][key]] for key in result['ids']]
                action = ' · '.join(page.link(p, p.read_text().splitlines()[0].lstrip('# ')) for p in selected) or 'None'
            else:
                choice = result['choice']
                action = f'{escape(options[choice])} <strong>{outcome(choice == record["expected"])}</strong>'
            content.append(f'<p><strong>{actor}</strong> · {action} ({page.link(receipt, "receipt")})</p>')
        content.append('</article>')
    return ''.join(content) + '</section>'


def exchange(question, answer):
    if not question:
        return '<p>The robot proceeded without a question.</p>'
    return f'<p><strong>Robot</strong> · {escape(question)}</p><p><strong>Person</strong> · {escape(answer)}</p>'


def replay(page, directory, label, anchor):
    case = read(directory / 'result.json')
    identity = read(directory / 'identity.json')
    body = [f'<article id="{anchor}"><h3>{escape(label)}</h3><h4>After the demonstration</h4>',
            f'<p>{escape(case["draft_reply"]["observation"])}</p>',
            exchange(case['audit_question'], case['audit_answer'])]
    for key, heading in [('draft_note', 'Draft note'), ('post_answer_note', 'Note carried forward')]:
        note = case[key].strip().lstrip('# ').replace('\n\n', ' · ') or 'No note recorded.'
        body.append(f'<p><strong>{heading}</strong> · {escape(note)}</p>')
    for phase, probe in case['probes'].items():
        scene = identity['probes'][phase]['public']
        options = scene['options']
        action = probe['selective']
        body.append(f'<h4>{"Transfer" if phase == "transfer" else "Scope control"}</h4>'
                    f'<p>{escape(scene["task"])}</p><p><strong>Assigned action</strong> · {escape(options[probe["expected"]])}</p>')
        for key, name in [('draft', 'Fresh reader with draft'), ('post_answer', 'Fresh reader with final note')]:
            result = probe[key]
            body.append(f'<p><strong>{name}</strong> · {escape(options[result["reply"]["choice"]])} '
                        f'({outcome(result["correct"])})</p>')
        body.append(f'<p><strong>Tentative action</strong> · {escape(options[action["tentative"]["choice"]])} '
                    f'({outcome(action["before_correct"])})</p>')
        body.append(exchange(action['question'], action['answer']))
        body.append(f'<p><strong>Final action</strong> · {escape(options[action["final"]["choice"]])} '
                    f'({outcome(action["after_correct"])})</p><p>{escape(action["final"]["reason"])}</p>')
    body.append('<p>' + page.link(directory / 'transcript.json', 'Recorded conversation') + ' · '
                + page.link(directory / 'result.json', 'Scored decisions') + '</p></article>')
    return ''.join(body)


def mug(page, study):
    directory = study / 'mug-handoff'
    trials = read(directory / 'results.json')
    body = ['<section id="mug"><h2>Mug handoff trials</h2><p>Two fresh readers saw the same initial scene in each context. '
            'One received the note written after the flashlight handoff. Each clip shows the action selected in that trial.</p>']
    for condition, title in [('both-free', 'Both hands free'), ('left-occupied', 'Left hand holding a cloth')]:
        body.append(f'<h3 id="mug-{condition}">{title}</h3>')
        for trial in (t for t in trials if t['condition'] == condition):
            arm = 'Without a note' if trial['arm'] == 'empty' else 'With the flashlight note'
            body.extend([f'<h4>{arm}</h4>', page.clip(directory / trial['clip'], directory / trial['image'], f'{title}, {arm}', f'{condition}-{trial["arm"]}.webm'),
                         f'<p>Offered to the {escape(trial["hand"])} hand. Assigned hand · {escape(trial["expected"])}. '
                         f'<strong>{outcome(trial["correct"])}</strong></p><p>{escape(trial["reason"])}</p>',
                         page.link(directory / trial['transcript'], 'Trial decision')])
    return ''.join(body) + '</section>'


def build_supplements(base):
    base = Path(base).absolute()
    study = base / 'visual-interaction-study-v1'
    revision = base / 'audit-revision'
    plan = read(revision / 'plan.json')
    policies = [('legacy', 'Original audit'), (read(revision / 'selection.json')['selected'], 'Revised audit')]
    notes = {hashlib.sha256(p.read_bytes()).hexdigest(): p for p in (study / 'library').glob('*.md')}
    for group in ['dev', 'holdout']:
        for family in plan[group]:
            page = Page(base, family)
            nav = '<a href="#library">Frozen library</a> · <a href="#audit">Audit replays</a>'
            sections = [frozen(page, study, family, notes), '<section id="audit"><h2>Audit replays</h2>']
            split = 'used for prompt development' if group == 'dev' else 'held out during prompt selection'
            sections.append(f'<p>This family was {split}. Each policy replayed the archived camera evidence.</p>')
            for policy, label in policies:
                sections.append(replay(page, revision / group / policy / 'cases' / family, label, policy))
            sections.append('</section>')
            if family == 'receiving-hand':
                nav += ' · <a href="#mug">Mug handoffs</a>'
                sections.append(mug(page, study))
            page.write(family.replace('-', ' ').title() + ' · additional experiments', nav, sections)

    page = Page(base, 'tray-choice')
    public = revision / 'locked-trays' / 'public'
    sections = ['<section id="paired"><h2>Paired tray correction</h2><p>Both simulated people moved the piece to the teal '
                'tray on their left. The same clip was shown for both. When the trays switched places, their assigned choices diverged.</p>',
                page.clip(public / 'teach/v.mp4', public / 'teach/i000.jpg', 'Shared tray correction', 'paired.webm')]
    for scene, label in [('fork', 'Transfer after the trays switched places'), ('control', 'Scope control')]:
        packet = read(public / scene / 'packet.json')
        sections.extend([f'<h3>{label}</h3><p>{escape(packet["task"])}</p>',
                         page.image(public / scene / 'i000.jpg', label)])
    for scenario, title in [('color', 'Person who prefers the teal tray'), ('location', 'Person who prefers the left side'),
                            ('silence', 'Quiet replay')]:
        if scenario == 'silence':
            sections.extend(['</section><section id="quiet"><h2>Quiet replay</h2><p>The person left the piece in the amber tray. '
                             'This replay tested whether the robot would ask a question or write a preference.</p>',
                             page.clip(public / 'silence/v.mp4', public / 'silence/i000.jpg', 'Quiet tray scene', 'quiet.webm')])
        else:
            sections.append(f'<h2 id="{scenario}">{title}</h2>')
        for policy, label in policies:
            sections.append(replay(page, revision / 'challenge' / policy / 'cases' / scenario, label, f'{scenario}-{policy}'))
    sections.append('</section>')
    page.write('Tray choice experiments', '<a href="#paired">Paired stimulus</a> · <a href="#color">Color preference</a> · '
               '<a href="#location">Location preference</a> · <a href="#quiet">Quiet stimulus</a>', sections)

def build_supplement_media(base):
    """Encode the six archived stimuli and compare frame hashes, PTS, and durations."""
    import imageio_ffmpeg
    encoder = imageio_ffmpeg.get_ffmpeg_exe()
    base = Path(base).absolute()
    mug_dir = base / 'visual-interaction-study-v1' / 'mug-handoff'
    tray_dir = base / 'audit-revision' / 'locked-trays' / 'public'
    assets = [(mug_dir / trial['clip'], 'receiving-hand', f"{trial['condition']}-{trial['arm']}.webm")
              for trial in read(mug_dir / 'results.json')]
    assets.extend([(tray_dir / 'teach/v.mp4', 'tray-choice', 'paired.webm'),
                   (tray_dir / 'silence/v.mp4', 'tray-choice', 'quiet.webm')])

    def signature(path):
        # framemd5 includes the decoded pixels and each frame's PTS and duration in stream timebase units.
        data = subprocess.check_output([encoder, '-v', 'error', '-xerror', '-i', path, '-map', '0:v:0',
                                        '-fps_mode', 'passthrough', '-f', 'framemd5', '-'], text=True)
        return [line for line in data.splitlines() if line.startswith(('#tb', '#dimensions')) or not line.startswith('#')]

    for source, family, name in assets:
        directory = base / 'experiments' / family / 'media'
        directory.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=directory) as tmp:
            output = Path(tmp) / name
            subprocess.run([encoder, '-v', 'error', '-xerror', '-i', source, '-map', '0:v:0', '-an',
                            '-c:v', 'libvpx-vp9', '-lossless', '1', '-row-mt', '1', '-cpu-used', '6',
                            '-threads', '4', '-fps_mode', 'passthrough', output], check=True)
            source_frames = signature(source)
            if len(source_frames) < 3 or source_frames != signature(output):
                raise ValueError(f'Decoded frames or timing differ for {source}')
            output.replace(directory / name)
