/**
 * Stay4S JavaScript SDK - 1 file, fetch-based
 * npm install niet nodig (gebruikt native fetch)
 *
 * Gebruik:
 *   import { Stay4S } from "./stay4s.js";
 *   const api = new Stay4S("jouw-api-key");
 *   const antwoord = await api.chat("Hallo, wie ben jij?");
 *   const scan = await api.scan("Bel snel naar 06-12345678");
 *   const vertaling = await api.translate("Hello world", "en", "nl");
 */

export class Stay4S {
  constructor(apiKey, baseUrl = "https://api.stay4s.com/v1") {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.headers = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
  }

  async _post(endpoint, body, timeout = 60000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const r = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      return await r.json();
    } finally {
      clearTimeout(id);
    }
  }

  async _get(endpoint, timeout = 10000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const r = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: this.headers,
        signal: controller.signal,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } finally {
      clearTimeout(id);
    }
  }

  async chat(message, system = "", history = []) {
    return this._post("/chat", { message, system, history }, 60000);
  }

  async scan(text) {
    return this._post("/scan", { text }, 30000);
  }

  async translate(text, source = "nl", target = "en") {
    return this._post("/translate", { text, source_lang: source, target_lang: target }, 30000);
  }

  async summarize(text, format = "bullet") {
    return this._post("/summarize", { text, format }, 30000);
  }

  async search(query, limit = 5) {
    return this._post("/search", { query, limit }, 30000);
  }

  async code(prompt, language = "python") {
    return this._post("/code", { prompt, language }, 60000);
  }

  async email(topic, tone = "formeel", recipient = "") {
    return this._post("/email", { topic, tone, recipient }, 30000);
  }

  async content(topic, type = "blog", length = "medium") {
    return this._post("/content", { topic, type, length }, 30000);
  }

  async agents(task, agent = "default") {
    return this._post("/agents", { task, agent }, 120000);
  }

  async usage() {
    return this._get("/usage");
  }

  async health() {
    return this._get("/health");
  }
}

// CommonJS export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { Stay4S };
}
