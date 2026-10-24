(() => {
  "use strict";
  const body = document.body;
  const ingestUrl = body.dataset.ingestUrl;
  if (!ingestUrl) return;

  const QUEUE_KEY = "soilsense-pending-readings";
  const SETTINGS_KEY = "soilsense-device-settings";
  const MAX_QUEUE = 15000;
  const BATCH = 200;
  const MISSING = new Set(["", "nan", "null", "none", "--", "-999", "na", "n/a", "undefined"]);
  const supported = "serial" in navigator;
  const encoder = new TextEncoder();
  const buttons = [...document.querySelectorAll("[data-serial-connect]")];
  const notes = [...document.querySelectorAll("[data-serial-note]")];

  let queue = [];
  try {
    queue = JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
    if (!Array.isArray(queue)) queue = [];
  } catch (error) {
    queue = [];
  }

  let port = null, writer = null, reader = null;
  let busy = false, syncing = false, lastCommand = "", message = "", persistTimer = null;

  function persist() {
    clearTimeout(persistTimer);
    persistTimer = null;
    try {
      localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error("Unable to save readings on this device.", error);
    }
  }

  function persistSoon() {
    if (!persistTimer) persistTimer = setTimeout(persist, 3000);
  }

  window.addEventListener("pagehide", persist);

  function num(value, low, high) {
    if (value === null || value === undefined || typeof value === "boolean") return null;
    if (typeof value === "string" && MISSING.has(value.trim().toLowerCase())) return null;
    const n = Number(value);
    if (!Number.isFinite(n) || n === -999 || n < low || n > high) return null;
    return n;
  }

  function parseLine(line) {
    let raw;
    try {
      if (line.startsWith("{")) {
        const value = JSON.parse(line);
        raw = [value.temperature, value.humidity, value.moisture];
      } else {
        raw = line.split(",");
        if (raw.length !== 3) return null;
      }
    } catch (error) {
      return null;
    }
    const reading = {
      temperature: num(raw[0], -50, 100),
      humidity: num(raw[1], 0, 100),
      moisture: num(raw[2], 0, 100),
    };
    return Object.values(reading).every(value => value === null) ? null : reading;
  }

  function noteText() {
    if (message) return message;
    if (!supported) return "Use Chrome or Edge on a computer to connect an Arduino.";
    if (busy) {
      if (!navigator.onLine) return `Offline · ${queue.length} readings saved on this device`;
      return queue.length > 1 ? `Syncing ${queue.length} saved readings…` : "Sending live readings";
    }
    return queue.length ? `${queue.length} saved readings waiting to sync` : "";
  }

  function updateUI() {
    buttons.forEach(button => {
      button.disabled = !supported;
      button.textContent = busy ? "Disconnect Arduino" : "⚡ Connect Arduino (USB)";
    });
    const text = noteText();
    notes.forEach(note => { note.textContent = text; });
    window.dispatchEvent(new CustomEvent("soil:status", {
      detail: {connected: busy, text: busy ? "Arduino connected" : "No sensor connected"},
    }));
  }

  async function send(command, force) {
    if (!writer) return false;
    if (!force && command === lastCommand) return true;
    try {
      await writer.write(encoder.encode(command));
      lastCommand = command;
      return true;
    } catch (error) {
      console.error("Unable to send settings to the Arduino.", error);
      return false;
    }
  }

  function commandFor(settings) {
    return `SET,${settings.moisture_threshold},${settings.sample_interval}\n`;
  }

  function remember(command) {
    try {
      localStorage.setItem(SETTINGS_KEY, command);
    } catch (error) {
      console.error("Unable to save Arduino settings on this device.", error);
    }
  }

  function sendSavedSettings() {
    let command = null;
    try {
      command = localStorage.getItem(SETTINGS_KEY);
    } catch (error) {
      console.error("Unable to load Arduino settings from this device.", error);
    }
    if (command) send(command);
  }

  function applyServerSettings(settings) {
    if (!settings) return;
    const command = commandFor(settings);
    remember(command);
    send(command);
  }

  function csrfToken() {
    const match = document.cookie.split("; ").find(cookie => cookie.startsWith("csrftoken="));
    return match ? decodeURIComponent(match.split("=")[1]) : body.dataset.csrf;
  }

  async function flush() {
    if (syncing || !queue.length || !navigator.onLine) return;
    syncing = true;
    try {
      while (queue.length && navigator.onLine) {
        const batch = queue.slice(0, BATCH);
        const response = await fetch(ingestUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken()},
          body: JSON.stringify({readings: batch}),
        });
        if (response.redirected || response.status === 401 || response.status === 403) {
          message = "Sign in again to sync saved readings.";
          break;
        }
        if (response.ok || response.status === 400) {
          queue.splice(0, batch.length);
          persistSoon();
          message = "";
          if (response.ok) applyServerSettings((await response.json()).settings);
        } else {
          break;
        }
      }
    } catch (error) {
      // Keep queued readings when offline or when the server is unavailable.
    } finally {
      syncing = false;
      updateUI();
    }
  }

  function handleReading(parsed) {
    const reading = {recorded_at: new Date().toISOString(), ...parsed};
    queue.push(reading);
    if (queue.length > MAX_QUEUE) queue.splice(0, queue.length - MAX_QUEUE);
    persistSoon();
    window.dispatchEvent(new CustomEvent("soil:reading", {detail: reading}));
    updateUI();
    flush();
  }

  async function connect(selected) {
    if (busy || !supported) return;
    try {
      const chosen = selected || await navigator.serial.requestPort();
      await chosen.open({baudRate: Number(body.dataset.baud) || 9600});
      port = chosen;
    } catch (error) {
      message = error.name === "NotFoundError" ? "" :
        `Could not open the port: ${error.message}. Close other apps using it (e.g. Arduino IDE Serial Monitor).`;
      updateUI();
      return;
    }
    busy = true;
    message = "";
    lastCommand = "";
    reader = port.readable.getReader();
    writer = port.writable.getWriter();
    updateUI();
    setTimeout(sendSavedSettings, 2500);
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        if (buffer.length > 4096) buffer = "";
        let index;
        while ((index = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, index).trim();
          buffer = buffer.slice(index + 1);
          const parsed = line && parseLine(line);
          if (parsed) handleReading(parsed);
        }
      }
    } catch (error) {
      message = `Arduino disconnected: ${error.message}. Plug it back in to reconnect.`;
    } finally {
      try { reader.releaseLock(); } catch (error) { /* Ignore a lock already released by the device. */ }
      try { writer.releaseLock(); } catch (error) { /* Ignore a lock already released by the device. */ }
      try { await port.close(); } catch (error) { /* The device may already be disconnected. */ }
      busy = false;
      reader = null;
      writer = null;
      port = null;
      updateUI();
    }
  }

  buttons.forEach(button => button.addEventListener("click", () => {
    if (busy) {
      if (reader) reader.cancel();
    } else {
      connect();
    }
  }));

  document.querySelectorAll("form[data-send-settings]").forEach(form =>
    form.addEventListener("submit", async event => {
      const command = commandFor({
        moisture_threshold: form.elements.moisture_threshold.value,
        sample_interval: form.elements.sample_interval.value,
      });
      remember(command);
      if (!busy && navigator.onLine) return;
      event.preventDefault();
      const sent = await send(command, true);
      if (navigator.onLine) {
        form.submit();
        return;
      }
      message = sent
        ? "Sent to the Arduino. You're offline, so save again once you're back online to keep it on your account."
        : "You're offline and no Arduino is connected, so nothing was sent.";
      updateUI();
    })
  );

  window.addEventListener("online", flush);
  window.addEventListener("offline", updateUI);
  setInterval(flush, 15000);

  if (supported) {
    navigator.serial.getPorts().then(ports => {
      if (ports.length === 1) connect(ports[0]);
    }).catch(error => console.error("Unable to check previously authorized Arduino ports.", error));
    navigator.serial.addEventListener("connect", event => connect(event.target));
  }

  window.SoilSerial = {
    isConnected: () => busy,
    pending: () => queue.slice(),
    send,
  };
  updateUI();
  flush();
})();
