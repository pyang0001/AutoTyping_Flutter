const text = document.querySelector("#text");
const highlight = document.querySelector("#highlight");
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

function escapeHtml(value) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

let savedPrefix = "";
let lastValue = "";
let pendingIndex = null;
let ignoreSelection = false;
let holdCursor = false;

function renderHighlight(value, greenAt) {
  const green = Math.max(0, Math.min(greenAt, value.length));
  const selecting = document.activeElement === text && text.selectionStart !== text.selectionEnd;
  let caretAt = green;
  if (!selecting && !(state && state.running) && document.activeElement === text) {
    caretAt = Math.max(0, Math.min(text.selectionStart, value.length));
  }
  const caret = '<span class="caret"></span>';
  let html;
  if (selecting) {
    html = '<span class="typed">' + escapeHtml(value.slice(0, green)) + "</span>" + escapeHtml(value.slice(green));
  } else if (caretAt <= green) {
    html = '<span class="typed">' + escapeHtml(value.slice(0, caretAt)) + "</span>" + caret +
      '<span class="typed">' + escapeHtml(value.slice(caretAt, green)) + "</span>" + escapeHtml(value.slice(green));
  } else {
    html = '<span class="typed">' + escapeHtml(value.slice(0, green)) + "</span>" +
      escapeHtml(value.slice(green, caretAt)) + caret + escapeHtml(value.slice(caretAt));
  }
  highlight.innerHTML = html;
  highlight.scrollTop = text.scrollTop;
  highlight.scrollLeft = text.scrollLeft;
}

function rememberText(value, index) {
  const at = Math.max(0, Math.min(index, value.length));
  savedPrefix = value.slice(0, at);
  lastValue = value;
}

function keepCaretInEditableText() {
  if (!state || !state.running) return;
  const index = state.index;
  if (text.selectionStart === index && text.selectionEnd === index) return;
  ignoreSelection = true;
  text.setSelectionRange(index, index);
  ignoreSelection = false;
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
  const editingText = document.activeElement === text || editTarget === text;
  if (!editingText && text.value !== next.text) text.value = next.text;
  if (!text.value.startsWith(next.text.slice(0, next.index))) text.value = next.text;
  const index = pendingIndex !== null && text.value === next.text ? pendingIndex : next.index;
  rememberText(text.value, index);
  renderHighlight(text.value, index);
  keepCaretInEditableText();
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

function editTouchesTyped(event) {
  if (!state || state.running) return true;
  const start = text.selectionStart ?? 0;
  const end = text.selectionEnd ?? start;
  const index = savedPrefix.length;
  if (start < index) return true;
  const kind = event.inputType || "";
  return kind.includes("Backward") && start === index && end === index;
}

text.addEventListener("beforeinput", (event) => {
  if (!editTouchesTyped(event)) return;
  event.preventDefault();
});

text.addEventListener("input", () => {
  holdCursor = true;
  if (!state || state.running || !text.value.startsWith(savedPrefix)) {
    text.value = lastValue;
    renderHighlight(text.value, savedPrefix.length);
    holdCursor = false;
    return;
  }
  lastValue = text.value;
  renderHighlight(text.value, savedPrefix.length);
  countEl.textContent = savedPrefix.length + "/" + text.value.length;
  post("/api/text", { text: text.value, index: savedPrefix.length }).then(paint).catch(() => {});
  setTimeout(() => { holdCursor = false; }, 0);
});

text.addEventListener("scroll", () => {
  highlight.scrollTop = text.scrollTop;
  highlight.scrollLeft = text.scrollLeft;
});

let cursorTimer = null;

document.addEventListener("selectionchange", () => {
  if (ignoreSelection || holdCursor || !state || document.activeElement !== text) return;
  if (state.running) {
    keepCaretInEditableText();
    return;
  }
  if (text.selectionStart !== text.selectionEnd || text.value !== lastValue) return;
  const index = text.selectionStart;
  if (index === savedPrefix.length && pendingIndex === null) return;
  savedPrefix = text.value.slice(0, index);
  pendingIndex = index;
  renderHighlight(text.value, index);
  countEl.textContent = index + "/" + text.value.length;
  clearTimeout(cursorTimer);
  cursorTimer = setTimeout(() => {
    if (!state || state.running || text.selectionStart !== text.selectionEnd || text.value !== lastValue) return;
    post("/api/index", { index: text.selectionStart }).then((next) => {
      pendingIndex = null;
      paint(next);
    }).catch(() => { pendingIndex = null; });
  }, 40);
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

let alertTimer = null;

function showAlert(message) {
  clearTimeout(alertTimer);
  errorEl.textContent = message;
  errorEl.classList.remove("show", "leaving");
  void errorEl.offsetWidth;
  errorEl.classList.add("show");
  alertTimer = setTimeout(hideAlert, 3000);
}

function hideAlert() {
  clearTimeout(alertTimer);
  alertTimer = null;
  if (!errorEl.classList.contains("show")) return;
  errorEl.classList.remove("show");
  errorEl.classList.add("leaving");
}

errorEl.addEventListener("animationend", () => {
  if (!errorEl.classList.contains("show")) errorEl.classList.remove("leaving");
});

function nextFieldValue(input, insert) {
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? input.value.length;
  return input.value.slice(0, start) + insert + input.value.slice(end);
}

function allowOnly(input, accepts, message) {
  input.addEventListener("beforeinput", (event) => {
    if (event.inputType && event.inputType.startsWith("delete")) return;
    const insert = event.data ?? "";
    if (accepts(nextFieldValue(input, insert))) return;
    event.preventDefault();
    showAlert(message);
  });
  input.addEventListener("input", () => {
    if (accepts(input.value)) {
      input.dataset.lastGood = input.value;
      return;
    }
    input.value = input.dataset.lastGood || "";
    showAlert(message);
  });
}

allowOnly(fields.start_delay, (text) => text === "" || text === "1" || text === "2" || text === "3", "Start delay must be 1, 2, or 3.");
allowOnly(fields.default_speed, (text) => speedTextOk(text), "Default speed must be a number from 1 to 30.");
allowOnly(fields.mistake_frequency, (text) => frequencyTextOk(text), "Mistake frequency must be a number from 0 to 10.");
allowOnly(fields.mistake_length, (text) => text === "" || /^[0-5]$/.test(text), "Mistake length must be a number from 0 to 5.");

function speedTextOk(text) {
  if (text === "") return true;
  if (!/^\d+$/.test(text) || (text.length > 1 && text.startsWith("0"))) return false;
  const value = Number(text);
  if (text.length === 1) return value >= 1 && value <= 9;
  return text.length === 2 && value >= 10 && value <= 30;
}

function frequencyTextOk(text) {
  if (text === "") return true;
  if (!/^\d+$/.test(text) || (text.length > 1 && text.startsWith("0"))) return false;
  const value = Number(text);
  if (text.length === 1) return value >= 0 && value <= 9;
  return text.length === 2 && value === 10;
}

document.querySelector("#open-settings").addEventListener("click", async () => {
  if (!state) return;
  const s = state.settings;
  fields.start_delay.value = s.start_delay;
  fields.default_speed.value = s.default_speed;
  fields.mistake_frequency.value = s.mistake_frequency;
  fields.mistake_length.value = s.mistake_length;
  fields.start_hotkey.value = s.start_hotkey;
  fields.reset_hotkey.value = s.reset_hotkey;
  for (const input of [fields.start_delay, fields.default_speed, fields.mistake_frequency, fields.mistake_length]) {
    input.dataset.lastGood = input.value;
  }
  hideAlert();
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
  hideAlert();
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
    showAlert(error.message);
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

dialog.addEventListener("cancel", (event) => {
  if (!errorEl.classList.contains("show")) return;
  event.preventDefault();
  hideAlert();
});

function isEditShortcut(event) {
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && !event.altKey && ["a", "c", "v", "x", "z", "y"].includes(key)) return true;
  if (event.shiftKey && (event.key === "Insert" || event.key === "Delete")) return true;
  return event.ctrlKey && event.key === "Insert";
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !editMenu.hidden) {
    event.preventDefault();
    event.stopPropagation();
    closeEditMenu();
    return;
  }
  const field = event.target;
  const inField = field instanceof HTMLTextAreaElement || field instanceof HTMLInputElement;
  if (inField && !field.classList.contains("hotkey") && isEditShortcut(event)) return;
  if (listening) {
    event.preventDefault();
    if (["Control", "Shift", "Alt", "Meta"].includes(event.key)) return;
    const names = [];
    if (event.ctrlKey) names.push("Ctrl");
    if (event.shiftKey) names.push("Shift");
    if (event.altKey) names.push("Alt");
    if (event.metaKey) names.push("Win");
    if (names.length === 0) {
      showAlert("Use a shortcut such as Ctrl+Up, not a single character like s.");
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

const editMenu = document.querySelector("#edit-menu");
let editTarget = null;

function closeEditMenu() {
  editMenu.hidden = true;
  editTarget = null;
}

function writeClipboard(value) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(value).catch(() => {});
  }
  return Promise.resolve();
}

async function readClipboard() {
  if (navigator.clipboard && navigator.clipboard.readText) {
    try {
      return await navigator.clipboard.readText();
    } catch (error) {
      return "";
    }
  }
  return "";
}

function editableRange(field) {
  if (field !== text) return !field.readOnly && !field.disabled;
  if (!state || state.running || field.readOnly) return false;
  const start = field.selectionStart ?? 0;
  const end = field.selectionEnd ?? start;
  return start >= savedPrefix.length && end >= savedPrefix.length;
}

function replaceSelection(target, insert) {
  const start = target.selectionStart ?? target.value.length;
  const end = target.selectionEnd ?? start;
  target.setRangeText(insert, start, end, "end");
  target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertFromPaste", data: insert }));
}

document.querySelectorAll("#text, .row input").forEach((field) => {
  field.addEventListener("contextmenu", (event) => {
    if (field.classList.contains("hotkey")) return;
    event.preventDefault();
    editTarget = field;
    const locked = field === text ? !editableRange(field) : field.readOnly || field.disabled;
    editMenu.querySelector("[data-edit='cut']").disabled = locked;
    editMenu.querySelector("[data-edit='paste']").disabled = locked;
    const menuWidth = 148;
    const menuHeight = 156;
    const x = Math.min(event.clientX, window.innerWidth - menuWidth - 8);
    const y = Math.min(event.clientY, window.innerHeight - menuHeight - 8);
    editMenu.style.left = Math.max(8, x) + "px";
    editMenu.style.top = Math.max(8, y) + "px";
    editMenu.hidden = false;
  });
});

editMenu.addEventListener("pointerdown", (event) => {
  event.preventDefault();
});

editMenu.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-edit]");
  const target = editTarget;
  const command = button && target ? button.dataset.edit : "";
  closeEditMenu();
  if (!target || !command) return;
  target.focus();
  const start = target.selectionStart ?? 0;
  const end = target.selectionEnd ?? 0;
  const selected = target.value.slice(start, end);
  if (command === "selectAll") {
    target.select();
    return;
  }
  if (command === "copy") {
    if (!selected) return;
    if (!document.execCommand("copy")) await writeClipboard(selected);
    return;
  }
  if (command === "cut") {
    if (!editableRange(target) || !selected) return;
    if (document.execCommand("cut")) {
      target.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }
    try {
      await navigator.clipboard.writeText(selected);
    } catch (error) {
      return;
    }
    replaceSelection(target, "");
    return;
  }
  if (command === "paste") {
    if (!editableRange(target)) return;
    if (document.execCommand("paste")) return;
    const clip = await readClipboard();
    if (clip) replaceSelection(target, clip);
  }
});

document.addEventListener("pointerdown", (event) => {
  if (!editMenu.hidden && !editMenu.contains(event.target)) closeEditMenu();
});

window.addEventListener("blur", closeEditMenu);

refresh().catch(() => {});
setInterval(() => refresh().catch(() => {}), 300);
