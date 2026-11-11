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
let editingPaused = false;
let pauseView = "";

function renderHighlight(value, greenAt, typo) {
  const green = Math.max(0, Math.min(greenAt, value.length));
  const red = typo || "";
  const caret = '<span class="caret"></span>';
  let html = '<span class="typed">' + escapeHtml(value.slice(0, green)) + "</span>";
  if (red) html += '<span class="typo">' + escapeHtml(value.slice(green, green + red.length)) + "</span>";
  html += caret + escapeHtml(value.slice(green + red.length));
  highlight.innerHTML = html;
  highlight.scrollTop = text.scrollTop;
  highlight.scrollLeft = text.scrollLeft;
  syncEditCaret();
}

function syncEditCaret() {
  const at = savedPrefix.length;
  const collapsed = text.selectionStart === text.selectionEnd;
  const editingElsewhere = collapsed && text.selectionStart !== at &&
    document.activeElement === text && state && !state.running;
  text.style.caretColor = editingElsewhere ? "#f4f6fb" : "transparent";
}

function rememberText(value, index) {
  const at = Math.max(0, Math.min(index, value.length));
  savedPrefix = value.slice(0, at);
  lastValue = value;
}

function keepCaretInEditableText() {
  if (!state || !state.running) return;
  const index = state.index + ((state.typo || "").length);
  if (text.selectionStart === index && text.selectionEnd === index) return;
  ignoreSelection = true;
  text.setSelectionRange(index, index);
  ignoreSelection = false;
}

function paint(next) {
  state = next;
  phaseEl.textContent = label(next.phase);
  const versionEl = document.querySelector("#version");
  if (versionEl && next.version) versionEl.textContent = next.version;
  phaseEl.classList.toggle("paused", next.phase === "paused");
  phaseEl.classList.toggle("starting", next.phase === "waiting");
  phaseEl.classList.toggle("typing", next.phase === "typing");
  const userPaused = next.phase === "paused" && next.pause_reason === "user";
  const focusPaused = next.phase === "paused" && next.pause_reason === "focus";
  const coveredPause = userPaused || focusPaused;
  const view = coveredPause ? "paused" : "";
  if (view !== pauseView) editingPaused = false;
  pauseView = view;
  document.querySelector("#pause-mark").hidden = !(coveredPause && !editingPaused);
  document.querySelector("#focus-pause").hidden = !(coveredPause && editingPaused);
  const countdown = document.querySelector("#count-overlay");
  countdown.hidden = next.phase !== "waiting";
  countdown.textContent = String(next.seconds_left || 1);
  countEl.textContent = next.index + "/" + next.total;
  const width = next.fraction > 0 ? Math.max(8, next.fraction * 100) : 8;
  bar.style.width = (next.fraction > 0 ? width : 8) + (next.fraction > 0 ? "%" : "px");
  const running = next.running;
  playIcon.classList.toggle("is-hidden", running);
  pauseIcon.classList.toggle("is-hidden", !running);
  play.classList.toggle("busy", running);
  play.setAttribute("aria-label", running ? "Pause" : "Start");
  text.readOnly = running;
  const editingText = document.activeElement === text || editTarget === text;
  const typo = running ? (next.typo || "") : "";
  const at = Math.max(0, Math.min(next.index || 0, next.text.length));
  const display = next.text.slice(0, at) + typo + next.text.slice(at);
  if (running || !editingText) {
    if (text.value !== display) text.value = display;
  }
  if (!running && !text.value.startsWith(next.text.slice(0, at))) text.value = next.text;
  const index = !typo && pendingIndex !== null && text.value === next.text ? pendingIndex : at;
  rememberText(text.value, index);
  renderHighlight(text.value, index, typo);
  keepCaretInEditableText();
  if (!dragging) paintSpeed(next.speed);
  const s = next.settings;
  let status = "";
  if (next.phase === "waiting") {
    status = "Starting in " + (next.seconds_left || 1) + " s - click where you want to type";
  } else if (next.phase === "typing") {
    status = "Typing...";
  } else if (focusPaused) {
    status = "Paused: the window being typed into lost focus. Press " + s.start_hotkey + ", then click where to type.";
  } else if (userPaused) {
    status = "Paused - press " + s.start_hotkey + " to resume";
  }
  shortcuts.textContent = status || (s.start_hotkey + " Start / Pause    " + s.reset_hotkey + " Reset");
  shortcuts.classList.toggle("status", next.phase === "waiting" || next.phase === "paused");
  if (document.activeElement !== onTop) onTop.checked = !!s.always_on_top;
}

function label(phase) {
  return { ready: "Ready", waiting: "Starting", typing: "Typing", paused: "Paused", done: "Done" }[phase] || "Ready";
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

text.addEventListener("pointerdown", () => {
  if (!state || state.phase !== "paused" || editingPaused) return;
  if (state.pause_reason !== "user" && state.pause_reason !== "focus") return;
  editingPaused = true;
  paint(state);
});

text.addEventListener("scroll", () => {
  highlight.scrollTop = text.scrollTop;
  highlight.scrollLeft = text.scrollLeft;
});

let cursorTimer = null;
let caretBeforeKey = null;
let draggingCaret = false;
let suppressClick = false;
let progressToken = 0;

function moveProgress(index) {
  if (!state || state.running || text.value !== lastValue) return;
  const at = Math.max(0, Math.min(index, text.value.length));
  if (at === savedPrefix.length && pendingIndex === null) return;
  const token = ++progressToken;
  savedPrefix = text.value.slice(0, at);
  pendingIndex = at;
  if (text.selectionStart < at || text.selectionEnd < at) {
    ignoreSelection = true;
    text.setSelectionRange(at, at);
    ignoreSelection = false;
  }
  renderHighlight(text.value, at);
  countEl.textContent = at + "/" + text.value.length;
  clearTimeout(cursorTimer);
  cursorTimer = setTimeout(() => {
    if (!state || state.running || text.value !== lastValue) return;
    post("/api/index", { index: at }).then((next) => {
      if (token !== progressToken) return;
      pendingIndex = null;
      paint(next);
    }).catch(() => {
      if (token === progressToken) pendingIndex = null;
    });
  }, 40);
}

function indexFromPoint(x, y) {
  const mark = highlight.querySelector(".caret");
  if (mark) mark.classList.add("pass");
  const highlightEvents = highlight.style.pointerEvents;
  const textEvents = text.style.pointerEvents;
  highlight.style.pointerEvents = "auto";
  text.style.pointerEvents = "none";
  const range = document.caretRangeFromPoint ? document.caretRangeFromPoint(x, y) : null;
  highlight.style.pointerEvents = highlightEvents;
  text.style.pointerEvents = textEvents;
  if (mark) mark.classList.remove("pass");
  if (!range) return null;
  if (range.startContainer === text) return range.startOffset;
  if (!highlight.contains(range.startContainer) || range.startContainer.nodeType !== Node.TEXT_NODE) return null;
  const walker = document.createTreeWalker(highlight, NodeFilter.SHOW_TEXT);
  let count = 0;
  let current = walker.nextNode();
  while (current) {
    if (current === range.startContainer) return count + range.startOffset;
    count += current.textContent.length;
    current = walker.nextNode();
  }
  return null;
}

document.querySelector("#pause-mark").addEventListener("pointerdown", (event) => {
  event.preventDefault();
  event.stopPropagation();
  if (!state || state.phase !== "paused") return;
  editingPaused = true;
  paint(state);
  text.focus();
  const at = savedPrefix.length;
  ignoreSelection = true;
  text.setSelectionRange(at, at);
  ignoreSelection = false;
  syncEditCaret();
});

function keepEditCaretInUntyped() {
  if (!state || state.running || text.selectionStart !== text.selectionEnd) return;
  if (text.selectionStart >= savedPrefix.length) {
    syncEditCaret();
    return;
  }
  ignoreSelection = true;
  text.setSelectionRange(savedPrefix.length, savedPrefix.length);
  ignoreSelection = false;
  syncEditCaret();
}

document.addEventListener("pointerdown", (event) => {
  if (!event.target.closest || !event.target.closest(".caret")) return;
  if (!state || state.running) return;
  event.preventDefault();
  const cover = document.querySelector("#pause-mark");
  if (cover && !cover.hidden) {
    editingPaused = true;
    paint(state);
    text.focus();
    return;
  }
  draggingCaret = true;
  suppressClick = true;
  document.body.classList.add("dragging-caret");
});

document.addEventListener("pointermove", (event) => {
  if (!draggingCaret) return;
  const at = indexFromPoint(event.clientX, event.clientY);
  if (at === null) return;
  moveProgress(at);
});

function endCaretDrag() {
  if (!draggingCaret) return;
  draggingCaret = false;
  document.body.classList.remove("dragging-caret");
  setTimeout(() => { suppressClick = false; }, 0);
}

document.addEventListener("pointerup", endCaretDrag);
document.addEventListener("pointercancel", endCaretDrag);

text.addEventListener("click", () => {
  if (suppressClick) return;
  keepEditCaretInUntyped();
});

text.addEventListener("keydown", (event) => {
  if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) {
    caretBeforeKey = text.selectionStart;
  }
});

text.addEventListener("keyup", (event) => {
  if (caretBeforeKey === null) return;
  const before = caretBeforeKey;
  caretBeforeKey = null;
  if (!state || state.running || text.value !== lastValue) return;
  if (text.selectionStart !== text.selectionEnd) return;
  const pausedRun = state.phase === "paused" && (state.pause_reason === "user" || state.pause_reason === "focus");
  const caret = text.selectionStart;
  if (pausedRun && before <= savedPrefix.length && caret !== before) {
    moveProgress(caret);
    return;
  }
  keepEditCaretInUntyped();
});

document.addEventListener("selectionchange", () => {
  if (ignoreSelection || holdCursor || !state || document.activeElement !== text) return;
  if (state.running) {
    keepCaretInEditableText();
    return;
  }
  syncEditCaret();
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

let speedTimer = null;

function sendSpeed() {
  const n = Math.max(1, Math.min(30, Math.round(Number(speed.value) || 1)));
  post("/api/speed", { speed: n }).then((next) => {
    if (dragging) {
      if (state) state.speed = next.speed;
      return;
    }
    paint(next);
  }).catch(() => {});
}

speed.addEventListener("pointerdown", () => {
  dragging = true;
  sendSpeed();
});
speed.addEventListener("input", () => {
  paintSpeed(speed.value);
  clearTimeout(speedTimer);
  speedTimer = setTimeout(sendSpeed, 30);
});
speed.addEventListener("change", () => {
  dragging = false;
  clearTimeout(speedTimer);
  sendSpeed();
});
speed.addEventListener("pointerup", () => { dragging = false; });
speed.addEventListener("pointercancel", () => { dragging = false; });

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
  document.querySelectorAll(".hotkey").forEach((el) => {
    el.classList.remove("listening");
    if (el.value === "Press keys") el.value = el.dataset.previous || "";
  });
  listening = null;
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
      start_hotkey: hotkeyValue(fields.start_hotkey),
      reset_hotkey: hotkeyValue(fields.reset_hotkey),
      always_on_top: onTop.checked,
    });
    paint(saved);
    await closeSettings();
  } catch (error) {
    showAlert(error.message);
  }
});

function hotkeyValue(input) {
  if (input.value === "Press keys") return input.dataset.previous || "";
  return input.value;
}

function releaseHotkey(input) {
  input.classList.remove("listening");
  if (input.value === "Press keys") input.value = input.dataset.previous || "";
  if (listening === input) listening = null;
}

function beginHotkey(input) {
  document.querySelectorAll(".hotkey").forEach((other) => {
    if (other !== input) releaseHotkey(other);
  });
  if (listening === input) return;
  if (input.value !== "Press keys") input.dataset.previous = input.value;
  listening = input;
  input.classList.add("listening");
  input.value = "Press keys";
}

document.querySelectorAll(".hotkey").forEach((input) => {
  input.addEventListener("focus", () => beginHotkey(input));
  input.addEventListener("blur", () => {
    if (listening === input) releaseHotkey(input);
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
    event.stopPropagation();
    if (event.key === "Escape" || ["Control", "Shift", "Alt", "Meta"].includes(event.key)) {
      if (event.key === "Escape") releaseHotkey(listening);
      return;
    }
    const names = [];
    if (event.ctrlKey) names.push("Ctrl");
    if (event.shiftKey) names.push("Shift");
    if (event.altKey) names.push("Alt");
    if (event.metaKey) names.push("Win");
    if (names.length === 0) {
      showAlert("Use a shortcut such as Ctrl+Up, not a single character like s.");
      releaseHotkey(listening);
      return;
    }
    names.push(keyName(event));
    listening.dataset.previous = names.join("+");
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
setInterval(() => refresh().catch(() => {}), 100);
