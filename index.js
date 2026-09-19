var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/index.js
var MAX_GIFT_B64 = 256 * 1024;
var MAX_COMMENT = 200;
var MAX_EVENTS_GET = 20;
var MAX_ACK = 50;
var EVENT_TTL_SEC = 24 * 3600;
var RATE_WINDOW_MS = 1e3;
var RATE_MAX = 3;
var rateMap = /* @__PURE__ */ new Map();
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });
}
__name(json, "json");
function nowSec() {
  return Math.floor(Date.now() / 1e3);
}
__name(nowSec, "nowSec");
async function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
__name(sha256Hex, "sha256Hex");
function randomToken(bytes = 32) {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return btoa(String.fromCharCode(...arr)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
__name(randomToken, "randomToken");
function checkRate(key) {
  const t = Date.now();
  let list = rateMap.get(key) || [];
  list = list.filter((x) => t - x < RATE_WINDOW_MS);
  if (list.length >= RATE_MAX) {
    rateMap.set(key, list);
    return false;
  }
  list.push(t);
  rateMap.set(key, list);
  return true;
}
__name(checkRate, "checkRate");
async function resolveUser(env, authHeader) {
  if (!authHeader || !authHeader.startsWith("Bearer ")) return null;
  const token = authHeader.slice(7).trim();
  if (!token || token.length < 24) return null;
  const hash = await sha256Hex(token);
  const row = await env.DB.prepare(
    "SELECT telegram_id FROM users WHERE token_hash = ? AND revoked = 0 LIMIT 1"
  ).bind(hash).first();
  if (!row) return null;
  return String(row.telegram_id);
}
__name(resolveUser, "resolveUser");
async function saveToken(env, telegramId, token) {
  const hash = await sha256Hex(token);
  const ts = nowSec();
  await env.DB.prepare("UPDATE users SET revoked = 1 WHERE telegram_id = ?").bind(String(telegramId)).run();
  await env.DB.prepare(
    "INSERT INTO users (telegram_id, token_hash, created_at, revoked) VALUES (?, ?, ?, 0) ON CONFLICT(telegram_id) DO UPDATE SET token_hash = excluded.token_hash, created_at = excluded.created_at, revoked = 0"
  ).bind(String(telegramId), hash, ts).run();
}
__name(saveToken, "saveToken");
async function telegram(method, body, env) {
  const url = `https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return res.json().catch(() => ({}));
}
__name(telegram, "telegram");
async function handleTelegramWebhook(request, env, secret) {
  if (secret !== env.WEBHOOK_SECRET) {
    return json({ error: "not found" }, 404);
  }
  let update;
  try {
    update = await request.json();
  } catch {
    return json({ ok: true });
  }
  try {
    if (update.callback_query) {
      const cq = update.callback_query;
      const chatId2 = cq.message?.chat?.id || cq.from?.id;
      const fromId2 = cq.from?.id;
      if (cq.data === "generate_key" && fromId2) {
        const token = randomToken(32);
        await saveToken(env, fromId2, token);
        await telegram(
          "answerCallbackQuery",
          { callback_query_id: cq.id, text: "\u041A\u043B\u044E\u0447 \u0441\u043E\u0437\u0434\u0430\u043D" },
          env
        );
        await telegram(
          "sendMessage",
          {
            chat_id: chatId2,
            text: "VG_TOKEN: " + token + "\n\n\u041A\u043B\u044E\u0447 \u0441\u043E\u0437\u0434\u0430\u043D.\n\u0412\u0441\u0442\u0430\u0432\u044C\u0442\u0435 \u0435\u0433\u043E \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430\u0445 \u043F\u043B\u0430\u0433\u0438\u043D\u0430, \u0435\u0441\u043B\u0438 \u043E\u043D \u043D\u0435 \u043F\u043E\u0434\u0441\u0442\u0430\u0432\u0438\u043B\u0441\u044F \u0430\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u0447\u0435\u0441\u043A\u0438.\n\u041D\u0438\u043A\u043E\u043C\u0443 \u043D\u0435 \u043F\u0435\u0440\u0435\u0434\u0430\u0432\u0430\u0439\u0442\u0435 \u044D\u0442\u043E\u0442 \u043A\u043B\u044E\u0447."
          },
          env
        );
      }
      return json({ ok: true });
    }
    const msg = update.message;
    if (!msg || !msg.text) return json({ ok: true });
    const text = String(msg.text || "").trim();
    const fromId = msg.from?.id;
    const chatId = msg.chat?.id;
    if (!fromId || !chatId) return json({ ok: true });
    if (text.startsWith("/start")) {
      const parts = text.split(/\s+/);
      const arg = (parts[1] || "").toLowerCase();
      if (arg === "auto") {
        const token = randomToken(32);
        await saveToken(env, fromId, token);
        await telegram(
          "sendMessage",
          {
            chat_id: chatId,
            text: "VG_TOKEN: " + token + "\n\n\u041A\u043B\u044E\u0447 \u0441\u043E\u0437\u0434\u0430\u043D \u0430\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u0447\u0435\u0441\u043A\u0438.\n\u041D\u0438\u043A\u043E\u043C\u0443 \u043D\u0435 \u043F\u0435\u0440\u0435\u0434\u0430\u0432\u0430\u0439\u0442\u0435 \u044D\u0442\u043E\u0442 \u043A\u043B\u044E\u0447."
          },
          env
        );
      } else {
        await telegram(
          "sendMessage",
          {
            chat_id: chatId,
            text: "\u041D\u0430\u0436\u043C\u0438\u0442\u0435 \u043A\u043D\u043E\u043F\u043A\u0443 \u0434\u043B\u044F \u0433\u0435\u043D\u0435\u0440\u0430\u0446\u0438\u0438 \u043F\u0435\u0440\u0441\u043E\u043D\u0430\u043B\u044C\u043D\u043E\u0433\u043E \u043A\u043B\u044E\u0447\u0430.",
            reply_markup: {
              inline_keyboard: [
                [{ text: "\u{1F511} \u0421\u0433\u0435\u043D\u0435\u0440\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u043A\u043B\u044E\u0447", callback_data: "generate_key" }]
              ]
            }
          },
          env
        );
      }
    }
  } catch (e) {
    console.error("webhook error", e);
  }
  return json({ ok: true });
}
__name(handleTelegramWebhook, "handleTelegramWebhook");
async function cleanupExpired(env) {
  const ts = nowSec();
  await env.DB.prepare("DELETE FROM events WHERE expires_at < ? OR used = 1").bind(ts).run();
}
__name(cleanupExpired, "cleanupExpired");
async function handlePutEvent(request, env, recipientId) {
  const senderId = await resolveUser(env, request.headers.get("Authorization"));
  if (!senderId) return json({ error: "unauthorized" }, 401);
  if (!checkRate("put:" + senderId)) return json({ error: "rate limit" }, 429);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "bad json" }, 400);
  }
  const gift = body.gift || {};
  const b64 = String(gift.b64 || "");
  if (!b64) return json({ error: "gift required" }, 400);
  if (b64.length > MAX_GIFT_B64) return json({ error: "gift too large" }, 413);
  const comment = String(gift.custom_comment || "").slice(0, MAX_COMMENT);
  const kind = String(gift.gift_kind || "sent").slice(0, 32);
  const anonymous = !!body.anonymous;
  const senderName = String(body.sender_name || "").slice(0, 100);
  const rid = String(recipientId || "").replace(/[^\d-]/g, "");
  if (!rid || Math.abs(Number(rid)) < 1e3) return json({ error: "bad recipient" }, 400);
  const eventId = crypto.randomUUID();
  const ts = nowSec();
  const giftJson = JSON.stringify({
    b64,
    gift_kind: kind,
    custom_comment: comment
  });
  await env.DB.prepare(
    `INSERT INTO events (event_id, sender_id, recipient_id, gift_json, created_at, expires_at, used)
     VALUES (?, ?, ?, ?, ?, ?, 0)`
  ).bind(eventId, senderId, rid, giftJson, ts, ts + EVENT_TTL_SEC).run();
  return json({ ok: true, event_id: eventId });
}
__name(handlePutEvent, "handlePutEvent");
async function handleGetEvents(request, env) {
  const recipientId = await resolveUser(env, request.headers.get("Authorization"));
  if (!recipientId) return json({ error: "unauthorized" }, 401);
  await cleanupExpired(env);
  const ts = nowSec();
  const rows = await env.DB.prepare(
    `SELECT event_id, sender_id, recipient_id, gift_json, created_at, expires_at
     FROM events
     WHERE recipient_id = ? AND used = 0 AND expires_at > ?
     ORDER BY created_at ASC
     LIMIT ?`
  ).bind(recipientId, ts, MAX_EVENTS_GET).all();
  const events = (rows.results || []).map((r) => {
    let gift = {};
    try {
      gift = JSON.parse(r.gift_json);
    } catch {
    }
    return {
      event_id: r.event_id,
      sender_id: r.sender_id,
      recipient_id: r.recipient_id,
      anonymous: false,
      gift,
      created_at: r.created_at,
      expires_at: r.expires_at
    };
  });
  return json({ events });
}
__name(handleGetEvents, "handleGetEvents");
async function handleAck(request, env) {
  const recipientId = await resolveUser(env, request.headers.get("Authorization"));
  if (!recipientId) return json({ error: "unauthorized" }, 401);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "bad json" }, 400);
  }
  const ids = Array.isArray(body.event_ids) ? body.event_ids.slice(0, MAX_ACK) : [];
  if (!ids.length) return json({ ok: true, updated: 0 });
  let updated = 0;
  for (const eid of ids) {
    const id = String(eid || "").slice(0, 64);
    if (!id) continue;
    const res = await env.DB.prepare(
      "UPDATE events SET used = 1 WHERE event_id = ? AND recipient_id = ? AND used = 0"
    ).bind(id, recipientId).run();
    if (res.meta?.changes) updated += res.meta.changes;
  }
  return json({ ok: true, updated });
}
__name(handleAck, "handleAck");
var index_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === "POST" && path.startsWith("/telegram/webhook/")) {
      const secret = path.slice("/telegram/webhook/".length);
      return handleTelegramWebhook(request, env, secret);
    }
    if (request.method === "PUT" && path.startsWith("/api/v1/events/")) {
      const recipientId = path.slice("/api/v1/events/".length).split("/")[0];
      return handlePutEvent(request, env, recipientId);
    }
    if (request.method === "GET" && path === "/api/v1/events") {
      return handleGetEvents(request, env);
    }
    if (request.method === "POST" && path === "/api/v1/events/ack") {
      return handleAck(request, env);
    }
    if (path === "/" || path === "/health") {
      return json({ ok: true, service: "visual-gifts" });
    }
    return json({ error: "not found" }, 404);
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
