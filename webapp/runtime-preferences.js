/* Browser-safe preferences shared by the local console and the hosted Site. */
"use strict";

(function installForecastPreferences(target) {
  const memory = new Map();

  const cloneObject = value => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    try { return JSON.parse(JSON.stringify(value)); } catch { return {}; }
  };

  const browserStorage = () => {
    try { return target.localStorage || null; } catch { return null; }
  };

  const readObject = key => {
    try {
      const raw = browserStorage()?.getItem?.(key);
      if (raw) {
        const parsed = cloneObject(JSON.parse(raw));
        memory.set(key, parsed);
        return cloneObject(parsed);
      }
    } catch {
      // Sandboxed browsers may expose storage but reject reads.
    }
    return cloneObject(memory.get(key));
  };

  const writeObject = (key, value) => {
    const safeValue = cloneObject(value);
    // Memory is authoritative for the current page, so a denied storage write
    // can never abort the action that requested the preference update.
    memory.set(key, safeValue);
    try { browserStorage()?.setItem?.(key, JSON.stringify(safeValue)); } catch {
      // Persistence is optional; interaction continuity is not.
    }
    return cloneObject(safeValue);
  };

  target.__FORECAST_PREFERENCES = Object.freeze({ readObject, writeObject });
})(globalThis);
