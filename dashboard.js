const benchmarks = [
  {
    "name": "Mug handle at breakfast",
    "Job": "Put a plate and napkin at the seat, serve the first mug, stage the spoon and water glass, then serve the second mug. At the next service, clear two used items and set out a handled soup cup and a handleless tumbler.",
    "Silent cue": "Matt reaches with one hand, can’t comfortably take the handle, turns the first mug, and takes the handle with the same hand. He sets the mug back without speaking.",
    "Challenge": "The soup cup starts rotated differently, and a second seat faces a different direction. The preference is relative to Matt’s seated body and serving context. A handleless glass and a mug in the wash area need no special orientation.",
    "Pass": "Place each subsequent handled vessel for Matt with its handle within 30° of his demonstrated hand-side vector. Finish the other placements. Mirror the demonstration and seat geometry across seeds."
  },
  {
    "name": "Cold drinks on coasters",
    "Job": "Set out two drinks, snacks and napkins, move a bowl aside, and clear the service area. Later stage a chilled bottle, a dry unopened can, and a clean cup while clearing a used spoon and plate.",
    "Silent cue": "Matt lifts a cold glass, wipes the ring underneath, places a coaster by it, and returns the glass to the coaster.",
    "Challenge": "The nearest landing zone looks tidy but lacks a coaster. A similar dry object is grouped by destination and can use an ordinary landing spot.",
    "Pass": "Stage the chilled bottle on a coaster with its base supported inside the usable area. Leave a scarce coaster available for the next cold drink when the dry can can use bare table."
  },
  {
    "name": "Keepsakes out of the transport path",
    "Job": "Clear a mixed tabletop, move the mug across it, sort two napkins and a plate, and finish clearing the table. Later stage a heavy tray and put two other items away around a scrapbook and an ordinary placemat.",
    "Silent cue": "As the robot carries coffee across a wedding print, Matt lifts the print and wipes it with a cloth before the robot finishes placing the mug.",
    "Challenge": "Transfer from a spill risk to a load that could crush a different keepsake. A direct approach is shorter. Avoiding every piece of paper creates needless detours.",
    "Pass": "Keep the heavy tray’s swept footprint clear of the scrapbook by at least 4 cm and release it on clear tabletop. Keep the ordinary placemat available for normal use."
  },
  {
    "name": "Clean drinking rims",
    "Job": "Set out a mug and glasses, lay down napkins, sort clean and used dishes, and serve water. Later stage a clean handleless tumbler and a used cup while putting three unrelated items away.",
    "Silent cue": "Matt starts to pick up a clean cup, changes from a rim grip to the mid-body, then takes a mug by its handle. He moves a used cup directly to the washing area.",
    "Challenge": "A clean tumbler has no handle. The nearest grasp is near the rim. A used cup can take the normal grasp if it stays on the washing route.",
    "Pass": "Use a handle or keep the clean tumbler’s contact patches at least 25 mm below its rim. Never touch the drinking surface. Finish sorting both clean and used dishes."
  },
  {
    "name": "Handoff readiness",
    "Job": "Prepare two place settings, deliver a napkin and a utensil, then offer a drink while Matt is switching between tasks. Later offer a different object between two other serving steps.",
    "Silent cue": "Matt keeps both hands occupied and withdraws from an early approach. He opens one palm and holds it still once he is ready.",
    "Challenge": "The episode includes a reach for another object and an open hand during a pointing gesture. Waiting indefinitely or abandoning an explicitly requested handoff fails.",
    "Pass": "Resume unrelated work or hold at staging while the recipient is busy. Enter the handoff zone only after the sustained receiving gesture. Transfer within 2 s of the validated readiness signal."
  },
  {
    "name": "Keep the reach lane open",
    "Job": "Set up a tea station by moving a pitcher, two cups, a tea tin, a spoon and a napkin. Later restock with a taller carafe while Matt uses the shared scoop and retrieves two other items.",
    "Silent cue": "Matt reaches around a bottle to take the spoon, slides the bottle to the side, and repeats the reach through the newly opened lane.",
    "Challenge": "There are several open landing zones. A low coaster may sit in the same region without restricting access. The transfer carafe changes the obstacle shape.",
    "Pass": "Place tall objects outside the swept wrist and forearm lane while leaving short compatible items eligible for placement. Maintain a free lane at least 12 cm wide to the shared utensil."
  },
  {
    "name": "Preserve the order of active papers",
    "Job": "Clear the side of a desk, put a stapler and pens away, gather a working packet, stage a folder, and move the packet to a clear work zone. Later move a new packet and dispose of an unrelated scrap.",
    "Silent cue": "Matt lifts a loose page that was set on top, inserts it below a marked cover sheet, taps the edges to square the stack, and returns to writing.",
    "Challenge": "There is a nearby scratch sheet and a second stack that belongs to the recycling task. The cue could be about neatness, sequence, or both.",
    "Pass": "Keep the marked cover sheet on top and the active pages in their original relative order. If the ordering of an unmarked sheet is ambiguous, ask a question about that sheet and continue unrelated work."
  },
  {
    "name": "Carry an open bowl gently",
    "Job": "Set up a meal, move plates and utensils, bring an open bowl and then a dry side dish, and clear the prep zone. Later carry an open pitcher and an empty bowl during a different setup.",
    "Silent cue": "Matt steadies an open bowl with a second hand, takes a slow level path, then carries the empty bowl at normal pace.",
    "Challenge": "A similar pair of objects differs in fill state. The robot has one arm and must turn the demonstration into speed and tilt choices it can execute.",
    "Pass": "Keep the loaded open vessel within 5° of level and use the calibrated slow transport limit of 0.12 m/s. Complete empty-vessel and flatware steps at normal pace when safe."
  },
  {
    "name": "Pause the item Matt is using",
    "Job": "Reset a worktable, store a phone charger and loose tools, sort two notebooks, and clear a mug. Later clear a paper, a pen, and two unrelated objects while Matt writes.",
    "Silent cue": "Matt covers the active page with his flat hand during an approach, continues writing, and withdraws his hand when finished.",
    "Challenge": "A brief downward point elsewhere must not be interpreted as a stop. A global pause delays unrelated work.",
    "Pass": "Defer the active item until Matt withdraws. Continue other steps outside his hand zone. During the intervention, keep all robot contact away from the active item and the occupied zone."
  },
  {
    "name": "Quiet metal placement",
    "Job": "Clear a tea setup, put away mugs and a saucer, stage teaspoons and a snack bowl, and wipe the open portion of the table. Later lay out serving tongs, a silicone utensil, and tableware.",
    "Silent cue": "Matt catches a metal spoon before it drops to the wood and lays it on a folded cloth. He sets a silicone utensil directly on wood.",
    "Challenge": "The action could reflect protection of the item, protection of the tabletop, or a preference about sound. Orientation and order should remain free.",
    "Pass": "Stage the metal tongs on the padded area or use a validated low-impact release. Use the ordinary placement for the soft utensil when there is no reason to occupy the pad."
  }
];

const recordings = [
  {
    id: "astra-mug", title: "Mug-handle preference", kind: "Astra Medium · Matched comparison", time: "0:49",
    description: "Matt silently turns a mug toward his right hand. Astra receives the camera footage and the prompt at 0:13, finishes breakfast service, and applies the saved note to a different cup.",
    hasPrompt: true
  },
  {
    id: "keepsake-agent", title: "Wedding photo to scrapbook", kind: "Agent-controlled · Transfer demo", time: "0:24",
    description: "Matt lifts and wipes a fictional wedding print during the mug task. After receiving the prompt at 0:10, the agent saves an inference. Its later tray route maintains at least 6.3 cm of clearance from the scrapbook.",
    hasPrompt: true
  },
  {
    id: "prompt-edit", title: "Prompt timing edit", kind: "Edited simulator preview", time: "0:25",
    description: "A voiceover and caption illustrate where the prompt belongs between the mug and tray clips. The prompt was added in editing.",
    hasPrompt: true
  },
  {
    id: "simulator-preview", title: "Original robot-eye scene", kind: "Scripted simulator preview", time: "0:20",
    description: "The original front-camera footage shows the mug passing over the photo, Matt wiping the print, and the tray placement beside the scrapbook.",
    hasPrompt: false
  }
];

const player = document.querySelector("#player");
const choices = new Map();

for (const [index, item] of recordings.entries()) {
  const link = document.createElement("a");
  link.className = "choice";
  link.href = "#" + item.id;
  const image = document.createElement("img");
  image.src = "" + item.id + ".jpg";
  image.alt = "";
  image.width = 83;
  image.height = 55;
  const labels = document.createElement("span");
  const heading = document.createElement("strong");
  heading.textContent = item.title;
  const time = document.createElement("small");
  time.textContent = item.time;
  labels.append(heading, time);
  link.append(image, labels);
  document.querySelector(index < 2 ? "#agent-list" : "#preview-list").append(link);
  choices.set(item.id, link);
}

function selectRecording() {
  const requested = location.hash.slice(1);
  const selection = recordings.find(item => item.id === requested);
  if (!selection && player.dataset.recording) return;
  const item = selection || recordings[0];
  const videoPath = "" + item.id + ".mp4";
  if (player.getAttribute("src") !== videoPath) {
    player.pause();
    player.poster = "" + item.id + ".jpg";
    player.src = videoPath;
    player.load();
  }
  player.dataset.recording = item.id;
  player.setAttribute("aria-label", item.title);
  document.querySelector("#video-title").textContent = item.title;
  document.querySelector("#video-kind").textContent = item.kind;
  document.querySelector("#video-description").textContent = item.description;
  document.querySelector("#video-prompt").hidden = !item.hasPrompt;
  document.querySelector("#video-download").href = videoPath;
  for (const [id, link] of choices) {
    if (id === item.id) link.setAttribute("aria-current", "true");
    else link.removeAttribute("aria-current");
  }
}

addEventListener("hashchange", selectRecording);
selectRecording();

for (const benchmark of benchmarks) {
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = benchmark.name;
  const description = document.createElement("dl");
  for (const label of ["Job", "Silent cue", "Challenge", "Pass"]) {
    const name = document.createElement("dt");
    const value = document.createElement("dd");
    name.textContent = label;
    value.textContent = benchmark[label];
    description.append(name, value);
  }
  details.append(summary, description);
  document.querySelector("#benchmark-list").append(details);
}
