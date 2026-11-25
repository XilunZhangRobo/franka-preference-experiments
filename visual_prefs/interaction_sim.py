"""Private simulation and answer keys for independently selected robot/person actions."""

from dataclasses import dataclass, replace
from pathlib import Path

from .episode import Motion
from .study import public_choices, render, scene_for

# First-person briefs are delivered only to the person, never to the robot.
PREFERENCES = {
    "paused-work": (
        "I clip a mat to mark a project I want to keep on the bench.",
        "I clip a mat to mark the project I want shelved.",
    ),
    "gift-finishing": (
        "I like to do the finishing touches on personal gifts myself.",
        "I like my helper to finish and assemble personal gifts for me.",
    ),
    "material-order": (
        "For my own assembly work I use the first component on my right, then work left.",
        "For my own assembly work I use the first component on my left, then work right.",
    ),
    "receiving-hand": (
        "I prefer receiving things in my left hand when it is free.",
        "I prefer receiving things in my right hand when it is free.",
    ),
    "approach-side": (
        "When there is room, I like things presented in front of my left shoulder.",
        "When there is room, I like things presented in front of my right shoulder.",
    ),
    "private-storage": (
        "I prefer my own belongings out of sight in the closed compartment between uses.",
        "I prefer my own belongings visible in the open tray between uses.",
    ),
    "cleaning-scent": (
        "I enjoy mild citrus cleaner in spaces I use privately.",
        "I prefer fragrance-free cleaner in spaces I use privately.",
    ),
    "lighting": (
        "When I work alone I like the even light from the ceiling fixture.",
        "When I work alone I like a small pool of light from the desk lamp.",
    ),
    "vegetable-texture": (
        "I like tender vegetables with warm meals.",
        "I like firm vegetables with warm meals.",
    ),
    "completion-update": (
        "I want brief routine updates immediately while I work alone.",
        "I want brief routine updates at a pause even when I work alone.",
    ),
}
SCOPE = {
    "paused-work": "An already closed kit can go on the shelf when starting a fresh project.",
    "gift-finishing": "Routine lunches for tomorrow should be packed completely.",
    "material-order": "When a group shares supplies, put them in the common tray.",
    "receiving-hand": "Use my free hand if the other one is busy.",
    "approach-side": "Use the accessible side when a shelf blocks the other side.",
    "private-storage": "Group equipment needed immediately should be available in the open.",
    "cleaning-scent": "Use fragrance-free cleaner for shared surfaces when guests are coming.",
    "lighting": "During a projected presentation keep the room dim and light just the craft table.",
    "vegetable-texture": "I want firm vegetables for chilled salads.",
    "completion-update": "A routine update can wait until my video call ends.",
}


def _human(motion):
    return replace(motion, actor="human-left" if motion.target[0] > 0 else "human")


def _point(motion):
    x, y, z = motion.target
    return _human(Motion("human", motion.item, (x, y, z + 0.055), "point"))


@dataclass
class Trial:
    family: str
    phase: str
    scene: object
    case: object
    choices: dict

    @property
    def options(self):
        return {letter: self.case.options[key] for letter, key in self.choices.items()}

    def persona(self, profile):
        return (
            PREFERENCES[self.family][("standard", "reverse").index(profile)]
            + " "
            + SCOPE[self.family]
        )

    def expected(self, profile):
        self.persona(profile)  # validate profile
        preferred = self.case.expected
        if profile == "reverse" and self.phase != "exception":
            preferred = next(key for key in self.case.options if key != preferred)
        return next(letter for letter, key in self.choices.items() if key == preferred)

    def expected_response(self, profile, letter):
        return "accept" if self.expected(profile) == letter else "change"

    def _keys(self, letter):
        current = self.choices[letter]
        return current, next(key for key in self.case.options if key != current)

    def _origin(self, item):
        return tuple(map(float, self.scene.props[item].get("pos").split()))

    def _response(self, letter, response):
        if self.phase != "teach":
            raise ValueError("Person responses belong to the teaching interaction.")
        current, other = self._keys(letter)
        chosen = current if response == "accept" else other
        old, new = self.case.robot[current], self.case.robot[chosen]
        action = new[0]
        fam = self.family
        if fam == "receiving-hand":
            actor = "human-left" if chosen == "left" else "human"
            x, y, z = action.target
            receive = Motion(actor, action.item, (x, y + 0.048, z + 0.016), "hold")
            if chosen == current:
                return f"Take and keep the flashlight in your {chosen} hand.", [receive]
            offered_hand = "human-left" if current == "left" else "human"
            return (
                f"Take the flashlight in the offered hand, then pass it to your {chosen} hand.",
                [Motion(offered_hand, action.item, (0, y + 0.045, z + 0.026), "hold"), receive],
            )
        if fam == "approach-side":
            return f"Point to your {chosen}-front quarter for the drink.", [
                _point(action),
                *([] if chosen == current else new),
            ]
        if fam == "completion-update":
            # A report cannot be unsaid. Re-enact its timing with the playback button.
            pencil = "pencil"
            start = Motion("human", pencil, self._origin(pencil))
            writing, down = self.case.robot["later"][:2]
            button = _human(replace(self.case.robot["now"][0], style="touch"))
            sequence = [button, down] if chosen == "now" else [down, button]
            when = "before" if chosen == "now" else "after"
            return (
                f"Demonstrate the timing: resume writing and tap the announcement button {when} putting the pencil down.",
                [start, writing, *sequence],
            )
        if fam == "gift-finishing":
            if chosen == "place":
                return "Point to the card for the robot to finish placing the flower.", [
                    _point(self.case.human[-1]),
                    replace(self.case.human[-1], actor="robot"),
                ]
            return "Take the flower and put the finishing touch on the card yourself.", [
                self.case.human[-1]
            ]
        if chosen == current:
            return "Point at the selected arrangement and leave it in place.", [_point(action)]
        if fam == "lighting":
            return "Switch the selected light off and switch on the other light.", [
                _human(old[0]),
                _human(action),
            ]
        if fam in ("paused-work", "vegetable-texture", "cleaning-scent"):
            undo = _human(Motion("human", old[0].item, self._origin(old[0].item)))
            if fam == "paused-work":
                return (
                    "Bring the shelved mat back to its original spot and leave the other mat alone.",
                    [undo],
                )
            return (
                "Return the selected item to its starting spot and move the other item into its place.",
                [undo, _human(action)],
            )
        if fam == "private-storage":
            cover = self.case.robot["compartment"]
            moves = new if chosen == "compartment" else [cover[0], *new, cover[-1]]
            return (
                "Move the belongings to the other storage location, opening and closing the compartment.",
                [_human(m) for m in moves],
            )
        if fam == "material-order":
            stage = replace(new[1], target=(0, 0.035, self.scene.table_z))
            return "Swap the two components so their order is reversed.", [
                _human(m) for m in [stage, *new]
            ]
        raise ValueError(fam)

    def person_menu(self, letter):
        return {key: self._response(letter, key)[0] for key in ("accept", "change")}

    def _render(self, folder, case, choice, **kwargs):
        settings = dict(fps=6, size=(640, 480), camera="agent", profile=None)
        settings.update(kwargs)
        return render(self.scene, case, Path(folder), choice=choice, **settings)

    def initial(self, folder, **kwargs):
        return self._render(folder, self.case, None, **kwargs)

    def execute(self, folder, letter, response=None, **kwargs):
        key = self.choices[letter]
        case = self.case
        if response is not None:
            if response not in ("accept", "change"):
                raise ValueError(response)
            _, moves = self._response(letter, response)
            case = replace(case, robot={key: [*case.robot[key], *moves]})
        return self._render(folder, case, key, **kwargs)


def prepare(family, phase, seed):
    scene, case = scene_for(family, phase, seed, "standard")
    if family == "completion-update":
        # A visible button press and the logged audio onset refer to the same event.
        # Both alternatives still contain exactly the same surrounding activity.
        case = replace(
            case,
            robot={
                key: [
                    replace(motion, style="touch") if motion.style == "say" else motion
                    for motion in moves
                ]
                for key, moves in case.robot.items()
            },
        )
        scene.grasp("speaker", (0, 0, 0.056))
    if family == "lighting" and phase == "exception":
        screen = scene.prop("projection", (-0.19, 0.21, scene.table_z))
        scene.box(screen, (0, 0, 0.11), (0.29, 0.015, 0.21), "#434952")
        scene.label(screen, (0, -0.009, 0.11), "SLIDE SHOW\nPaper folding", 0.27, 0.18)
        case = replace(
            case,
            expected="desk",
            default="ceiling",
            command=(
                "A projected slide show is in progress. Keep the room dim while giving the craft table enough light."
            ),
        )
    return Trial(family, phase, scene, case, public_choices(case, seed, phase))
