const text = document.querySelector("#text");
const phaseEl = document.querySelector("#phase");
const countEl = document.querySelector("#count");
const bar = document.querySelector("#bar");
const play = document.querySelector("#play");
const playIcon = document.querySelector("#play-icon");
const pauseIcon = document.querySelector("#pause-icon");
const reset = document.querySelector("#reset");
const speed = document.querySelector("#speed");
const speedBox = document.querySelector("#speed-box");
const shortcuts = document.querySelector("#shortcuts");
const onTop = document.querySelector("#on-top");
const dialog = document.querySelector("#settings");
const form = document.querySelector("#settings-form");
const errorEl = document.querySelector("#settings-error");

const fields = {
  start_delay: document.querySelector("#start-delay"),
  default_speed: document.querySelector("#default-speed"),
  mistake_frequency: document.querySelector("#mistake-frequency"),
  mistake_length: document.querySelector("#mistake-length"),
  start_hotkey: document.querySelector("#start-hotkey"),
  reset_hotkey: document.querySelector("#reset-hotkey"),
};

let state = null;
let dragging = false;
let listening = null;

function paintSpeed(value) {
  const n = Number(value);
  speed.value = String(n);
  speedBox.textContent = String(n);
  const pct = ((n - 1) / 29) * 100;
  speed.style.setProperty("--p", pct + "%");
}

function paint(next) {
  state = next;
  phaseEl.textContent = label(next.phase);
  countEl.textContent = next.index + "/" + next.total;
  const width = next.fraction > 0 ? Math.max(8, next.fraction * 100) : 8;
  bar.style.width = (next.fraction > 0 ? width : 8) + (next.fraction > 0 ? "%" : "px");
  const running = next.running;
  playIcon.classList.toggle("is-hidden", running);
  pauseIcon.classList.toggle("is-hidden", !running);
  play.setAttribute("aria-label", running ? "Pause" : "Start");
  text.readOnly = running;
  if (document.activeElement !== text && text.value !== next.text) {
    text.value = next.text;
  }
  if (!dragging) paintSpeed(next.speed);
  const s = next.settings;
  shortcuts.textContent = s.start_hotkey + " Start / Pause    " + s.reset_hotkey + " Reset";
  if (document.activeElement !== onTop) onTop.checked = !!s.always_on_top;
}

function label(phase) {
  return { ready: "Ready", waiting: "Waiting", typing: "Typing", paused: "Paused", done: "Done" }[phase] || "Ready";
}

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function refresh() {
  const response = await fetch("/api/state");
  paint(await response.json());
}

text.addEventListener("input", () => {
  if (state && state.running) return;
  const value = text.value;
  countEl.textContent = "0/" + value.length;
  post("/api/text", { text: value }).then(paint).catch(() => {});
});

play.addEventListener("click", async () => {
  text.blur();
  try {
    paint(await post("/api/toggle", { text: text.value, speed: Number(speed.value) }));
  } catch (error) {
    where.textContent = error.message;
  }
});

reset.addEventListener("click", async () => {
  paint(await post("/api/reset"));
});

onTop.addEventListener("change", async () => {
  paint(await post("/api/ontop", { always_on_top: onTop.checked }));
});

speed.addEventListener("pointerdown", () => { dragging = true; });
speed.addEventListener("input", () => paintSpeed(speed.value));
speed.addEventListener("change", async () => {
  dragging = false;
  paint(await post("/api/speed", { speed: Number(speed.value) }));
});

document.querySelector("#open-settings").addEventListener("click", async () => {
  if (!state) return;
  const s = state.settings;
  fields.start_delay.value = s.start_delay;
  fields.default_speed.value = s.default_speed;
  fields.mistake_frequency.value = s.mistake_frequency;
  fields.mistake_length.value = s.mistake_length;
  fields.start_hotkey.value = s.start_hotkey;
  fields.reset_hotkey.value = s.reset_hotkey;
  errorEl.hidden = true;
  await post("/api/hotkeys", { suspended: true });
  dialog.showModal();
});

async function closeSettings() {
  listening = null;
  document.querySelectorAll(".hotkey").forEach((el) => el.classList.remove("listening"));
  dialog.close();
  await post("/api/hotkeys", { suspended: false });
}

document.querySelector("#close-settings").addEventListener("click", closeSettings);
document.querySelector("#cancel-settings").addEventListener("click", closeSettings);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorEl.hidden = true;
  try {
    const saved = await post("/api/settings", {
      start_delay: fields.start_delay.value,
      default_speed: fields.default_speed.value,
      mistake_frequency: fields.mistake_frequency.value,
      mistake_length: fields.mistake_length.value,
      start_hotkey: fields.start_hotkey.value,
      reset_hotkey: fields.reset_hotkey.value,
      always_on_top: onTop.checked,
    });
    paint(saved);
    await closeSettings();
  } catch (error) {
    errorEl.textContent = error.message;
    errorEl.hidden = false;
  }
});

document.querySelectorAll(".hotkey").forEach((input) => {
  input.addEventListener("focus", () => {
    if (input.value !== "Press keys") input.dataset.previous = input.value;
    listening = input;
    input.classList.add("listening");
    input.value = "Press keys";
  });
});

document.addEventListener("keydown", (event) => {
  if (listening) {
    event.preventDefault();
    if (["Control", "Shift", "Alt", "Meta"].includes(event.key)) return;
    const names = [];
    if (event.ctrlKey) names.push("Ctrl");
    if (event.shiftKey) names.push("Shift");
    if (event.altKey) names.push("Alt");
    if (event.metaKey) names.push("Win");
    if (names.length === 0) {
      errorEl.textContent = "Use a shortcut such as Ctrl+Up, not a single character like s.";
      errorEl.hidden = false;
      listening.value = listening.dataset.previous || "";
      listening.classList.remove("listening");
      listening = null;
      return;
    }
    names.push(keyName(event));
    listening.value = names.join("+");
    listening.classList.remove("listening");
    listening = null;
    return;
  }
  if (dialog.open) return;
  const chord = chordFromEvent(event);
  if (!state) return;
  if (chord === state.settings.start_hotkey) {
    event.preventDefault();
    play.click();
  } else if (chord === state.settings.reset_hotkey) {
    event.preventDefault();
    reset.click();
  }
});

function keyName(event) {
  const map = {
    ArrowUp: "Up",
    ArrowDown: "Down",
    ArrowLeft: "Left",
    ArrowRight: "Right",
    " ": "Space",
    Escape: "Esc",
    Backspace: "Backspace",
    Delete: "Delete",
    Enter: "Enter",
    Tab: "Tab",
  };
  if (map[event.key]) return map[event.key];
  if (/^F\d{1,2}$/.test(event.key)) return event.key;
  if (event.key.length === 1) return event.key.toUpperCase();
  return event.key;
}

function chordFromEvent(event) {
  if (["Control", "Shift", "Alt", "Meta"].includes(event.key)) return "";
  const names = [];
  if (event.ctrlKey) names.push("Ctrl");
  if (event.shiftKey) names.push("Shift");
  if (event.altKey) names.push("Alt");
  if (event.metaKey) names.push("Win");
  if (!names.length) return "";
  names.push(keyName(event));
  return names.join("+");
}

refresh().catch(() => {});
setInterval(() => refresh().catch(() => {}), 300);
