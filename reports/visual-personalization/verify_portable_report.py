"""Check a staged portable report directory or ZIP. Pass --firefox for offline playback."""
import argparse
from contextlib import contextmanager
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import socket
import stat
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import build_opener, ProxyHandler, Request
from zipfile import ZipFile

FAMILIES = set("approach-side cleaning-scent completion-update gift-finishing lighting "
               "material-order paused-work private-storage receiving-hand vegetable-texture".split())
CONTRAST = {"material-order", "paused-work", "private-storage", "vegetable-texture"}
EXPECTED = {(mode, family) for family in FAMILIES for mode in ("isolated", "continuous")}
EXPECTED.update(("contrast", family) for family in CONTRAST)
PHASES = ("action", "feedback", "transfer", "control")
ANCHORS = ("action", "feedback", "note", "transfer", "control")
SUPPLEMENT_VIDEOS = {"receiving-hand": 4, "tray-choice": 2}
VOID = set("area base br col embed hr img input link meta param source track wbr".split())


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.ids = set()
        self.refs = []
        self.links = []
        self.videos = {}
        self.stack = []
        self.body = {}
        self.feed(path.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body":
            self.body = a
        if a.get("id"):
            self.ids.add(a["id"])
        self.refs.extend(a[k] for k in ("src", "href", "poster") if a.get(k))
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag not in VOID:
            self.stack.append((tag, a.get("id")))
        phase = next((ident for _, ident in reversed(self.stack) if ident in PHASES), None)
        if tag == "video" and phase:
            self.videos.setdefault(phase, []).append([a["src"]] if a.get("src") else [])
        if tag == "source" and phase and any(t == "video" for t, _ in self.stack):
            self.videos[phase][-1].append(a.get("src", ""))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def target(root, path, ref):
    u = urlsplit(ref)
    name = unquote(u.path)
    require(not (u.scheme or u.netloc or name.startswith("/") or "\\" in name),
            f"{path}: nonportable reference {ref!r}")
    dest = Path(os.path.normpath(path.parent / name)) if name else path
    require(dest.is_relative_to(root) and dest.is_file(), f"{path}: missing or escaping {ref!r}")
    return dest, unquote(u.fragment)


@contextmanager
def report_root(source, scratch):
    if source.is_dir():
        yield source.resolve()
        return
    root = scratch / "Extracted portable report"
    with ZipFile(source) as archive:
        seen = set()
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            require(not (path.is_absolute() or ".." in path.parts or "\\" in info.filename
                         or stat.S_ISLNK(info.external_attr >> 16) or path in seen),
                    f"Unexpected ZIP entry {info.filename!r}")
            seen.add(path)
        require(archive.testzip() is None, "ZIP checksum failure")
        archive.extractall(root)
    yield root


def verify(root, index):
    pages = {}
    pending = [index]
    refs = 0
    while pending:
        path = pending.pop()
        if path in pages:
            continue
        page = pages[path] = Page(path)
        for ref in page.refs:
            dest, _ = target(root, path, ref)
            if dest.suffix.lower() in {".htm", ".html"} and dest not in pages:
                pending.append(dest)
            refs += 1
    for path, page in pages.items():
        for ref in page.refs:
            dest, anchor = target(root, path, ref)
            if anchor and dest in pages:
                require(anchor in pages[dest].ids, f"{path}: broken anchor {ref!r}")
    manifest = json.loads((root / "trial-clips/manifest.json").read_text())
    require(set(manifest) == {f"{m}/{f}" for m, f in EXPECTED}, "Unexpected manifest inventory")
    expected_paths = {root / "experiments" / f / f"{m}.html" for m, f in EXPECTED}
    check_paths = {root / "experiments" / f / "checks.html" for f in FAMILIES | {"tray-choice"}}
    require(set((root / "experiments").glob("*/*.html")) == expected_paths | check_paths,
            "Unexpected experiment page inventory")
    require(check_paths <= pages.keys(), "Unreachable supplementary check page")
    links = {target(root, index, ref)[0] for ref in pages[index].links}
    require(expected_paths <= links, "Index lacks direct links to some trials")
    clips = set()
    for mode, family in sorted(EXPECTED):
        path = root / "experiments" / family / f"{mode}.html"
        page = pages[path]
        require((page.body.get("data-mode"), page.body.get("data-family")) == (mode, family),
                f"{path}: incorrect trial identity")
        require(set(ANCHORS) <= page.ids, f"{path}: missing required section")
        destinations = {target(root, path, ref) for ref in page.links}
        require(index in {dest for dest, _ in destinations}, f"{path}: no return link")
        for phase in PHASES:
            media = page.videos.get(phase, [])
            require(len(media) == 1 and len(media[0]) == 1, f"{path}#{phase}: expected one clip")
            actual = target(root, path, media[0][0])[0]
            expected = target(root, index, manifest[f"{mode}/{family}"][phase]["file"])[0]
            require(actual == expected, f"{path}#{phase}: mismatched clip {actual}")
            clips.add(actual)
    print(f"Verified 10 families, 24 trial pages, 96 phase mappings, {len(clips)} media files, "
          f"and {refs} references across {len(pages)} reachable HTML documents.", flush=True)


@contextmanager
def firefox(scratch):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    opener = build_opener(ProxyHandler({}))
    def send(method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                      headers={"Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=60) as response:
                return json.load(response)["value"]
        except HTTPError as exc:
            raise RuntimeError(exc.read().decode()[:1200]) from exc
    profiles = scratch / "profiles"
    profiles.mkdir()
    with (scratch / "geckodriver.log").open("w") as log:
        driver = subprocess.Popen(["geckodriver", "--port", str(port), "--profile-root", str(profiles)],
                                  stdout=log, stderr=subprocess.STDOUT)
        sid = None
        try:
            for _ in range(80):
                try:
                    send("GET", "/status")
                    break
                except URLError:
                    time.sleep(.25)
            prefs = {"network.proxy.type": 1, "network.proxy.http": "127.0.0.1",
                     "network.proxy.http_port": 9, "network.proxy.ssl": "127.0.0.1",
                     "network.proxy.ssl_port": 9, "media.autoplay.default": 0,
                     "network.captive-portal-service.enabled": False,
                     "network.connectivity-service.enabled": False}
            options = {"args": ["-headless"], "prefs": prefs}
            caps = {"browserName": "firefox", "moz:firefoxOptions": options}
            sid = send("POST", "/session", {"capabilities": {"alwaysMatch": caps}})["sessionId"]
            def post(path, data):
                return send("POST", f"/session/{sid}/{path}", data)
            yield post
        finally:
            try:
                if sid:
                    send("DELETE", f"/session/{sid}")
            finally:
                driver.terminate()
                try:
                    driver.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    driver.kill()
                    driver.wait()


PLAY = """
const [phase, done] = arguments;
const v = typeof phase === 'number' ? document.querySelectorAll('video')[phase]
                                    : document.getElementById(phase).querySelector('video');
v.muted = true;
v.scrollIntoView();
const start = performance.now();
function check() {
    if (v.currentTime > .05 && v.readyState >= 2 && v.videoWidth > 0) {
        v.pause(); done({ok:true, seconds:v.duration, src:v.currentSrc}); return;
    }
    if (v.error || performance.now() - start > 12000) {
        done({error:v.error?.message || 'playback timed out', time:v.currentTime,
              duration:v.duration, state:v.readyState, width:v.videoWidth}); return;
    }
    setTimeout(check, 40);
}
v.play().then(check, e => done({error:String(e)}));
"""


def playback(root, scratch, index):
    index = index.as_uri()
    manifest = json.loads((root / "trial-clips/manifest.json").read_text())
    with firefox(scratch) as post:
        def js(script, *args):
            return post("execute/sync", {"script": script, "args": args})
        def click(uri):
            clicked = js("""const a = Array.from(document.links).find(a => a.href === arguments[0]);
                            if (!a) return false; a.click(); return true;""", uri)
            require(clicked, f"No browser link to {uri}")
            for _ in range(80):
                if js("return location.href") == uri:
                    return
                time.sleep(.05)
            raise ValueError(f"Click failed to navigate to {uri}")
        post("url", {"url": index})
        default = js("return document.getElementById('start-at').value")
        def choose(value):
            js("""const s = document.getElementById('start-at');
                  s.value = arguments[0];
                  s.dispatchEvent(new Event('change', {bubbles:true}));""", value)
        choose("feedback")
        sample = (root / "experiments" / "paused-work" / "isolated.html").as_uri()
        click(sample + "#feedback")
        post("back", {})
        choose(default)
        for family in sorted(FAMILIES):
            for mode in ("isolated", "contrast", "continuous"):
                if (mode, family) not in EXPECTED:
                    continue
                uri = (root / "experiments" / family / f"{mode}.html").as_uri()
                click(uri)
                for phase in PHASES:
                    result = post("execute/async", {"script": PLAY, "args": [phase]})
                    require(result.get("ok"), f"{uri}#{phase}: {result}")
                    entry = manifest[f"{mode}/{family}"][phase]
                    require(result["src"] == (root / entry["file"]).as_uri()
                            and entry["file"].endswith(".webm"),
                            f"{uri}#{phase}: incorrect primary source {result['src']}")
                    expected = entry["duration"]
                    require(abs(result["seconds"] - expected) < .25,
                            f"{uri}#{phase}: duration {result['seconds']} vs recorded {expected}")
                for anchor in ANCHORS:
                    click(uri + "#" + anchor)
                post("back", {})
                require(js("return location.href") == uri + "#transfer", f"Back failed on {uri}")
            click(index)
        for family, count in SUPPLEMENT_VIDEOS.items():
            uri = (root / "experiments" / family / "checks.html").as_uri()
            post("url", {"url": uri})
            require(js("return document.querySelectorAll('video').length") == count,
                    f"{uri}: expected {count} supplemental players")
            for i in range(count):
                result = post("execute/async", {"script": PLAY, "args": [i]})
                require(result.get("ok") and result.get("src", "").endswith(".webm"),
                        f"{uri} video {i + 1}: {result}")
    print("Firefox navigated all 24 trials, exercised 120 anchor links and browser Back, "
          "and played 96 phase clips and 6 supplemental clips.",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--firefox", action="store_true")
    args = parser.parse_args()
    # Firefox's snap packaging can access the workspace but has a private /tmp.
    with tempfile.TemporaryDirectory(prefix=".portable-qa-", dir=Path.cwd()) as directory:
        scratch = Path(directory)
        with report_root(args.source, scratch) as root:
            index = root / "index.html"
            if args.source.is_dir() and not index.exists():
                index = root / "consolidated-report.html"
            verify(root, index)
            if args.firefox:
                playback(root, scratch, index)


if __name__ == "__main__":
    main()
