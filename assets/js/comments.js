/* Techima comments UI. Set API_BASE to the deployed Cloudflare Worker URL. */
(function () {
  "use strict";
  var API_BASE = "https://REPLACE-WITH-YOUR-WORKER.workers.dev";
  var configured = /^https:\/\/[a-z0-9-]+(\.[a-z0-9-]+)*\.workers\.dev$/i.test(API_BASE) &&
    API_BASE.indexOf("REPLACE-WITH-YOUR-WORKER") === -1;
  var widgets = document.querySelectorAll("[data-comments-widget]");
  if (!widgets.length) return;

  function faNumber(value) {
    try { return Number(value).toLocaleString("fa-IR"); } catch (_) { return String(value); }
  }
  function formatDate(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    try { return date.toLocaleDateString("fa-IR", { year: "numeric", month: "short", day: "numeric" }); }
    catch (_) { return ""; }
  }
  function createCommentCard(item) {
    var card = document.createElement("article");
    card.className = "comment-card";
    var header = document.createElement("div");
    header.className = "comment-card-header";
    var avatar = document.createElement("span");
    avatar.className = "comment-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = (item.name || "?").trim().slice(0, 1);
    var meta = document.createElement("div");
    var author = document.createElement("div");
    author.className = "comment-author";
    author.textContent = item.name || "بازدیدکننده";
    var date = document.createElement("div");
    date.className = "comment-date";
    date.textContent = formatDate(item.createdAt);
    meta.appendChild(author);
    meta.appendChild(date);
    header.appendChild(avatar);
    header.appendChild(meta);
    var message = document.createElement("p");
    message.className = "comment-message";
    message.textContent = item.message || "";
    card.appendChild(header);
    card.appendChild(message);
    return card;
  }
  function setStatus(widget, text, kind) {
    var status = widget.querySelector("[data-comments-status]");
    if (!status) return;
    status.textContent = text || "";
    if (kind) status.setAttribute("data-kind", kind);
    else status.removeAttribute("data-kind");
  }
  function renderComments(widget, items) {
    var list = widget.querySelector("[data-comments-list]");
    var count = widget.querySelector("[data-comments-count]");
    if (!list || !count) return;
    list.replaceChildren();
    count.textContent = faNumber(items.length) + " پیام";
    if (!items.length) {
      var empty = document.createElement("div");
      empty.className = "comments-empty";
      var icon = document.createElement("span");
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = "✧";
      var text = document.createElement("p");
      text.textContent = "هنوز پیامی ثبت نشده است؛ اولین نفر باشید.";
      empty.appendChild(icon);
      empty.appendChild(text);
      list.appendChild(empty);
      return;
    }
    items.slice(0, 50).forEach(function (item) { list.appendChild(createCommentCard(item)); });
  }
  async function loadComments(widget) {
    if (!configured) {
      renderComments(widget, []);
      var list = widget.querySelector("[data-comments-list]");
      if (list) {
        list.replaceChildren();
        var empty = document.createElement("div");
        empty.className = "comments-empty";
        var icon = document.createElement("span");
        icon.textContent = "⚙";
        icon.setAttribute("aria-hidden", "true");
        var text = document.createElement("p");
        text.textContent = "سامانهٔ ثبت و نمایش پیام‌ها هنوز به سرویس امن متصل نشده است.";
        empty.appendChild(icon);
        empty.appendChild(text);
        list.appendChild(empty);
      }
      setStatus(widget, "برای فعال‌شدن ارسال پیام، سرویس امن را طبق راهنمای backend/README.md راه‌اندازی کن.", "error");
      var button = widget.querySelector(".comments-submit");
      if (button) button.disabled = true;
      return;
    }
    try {
      var res = await fetch(API_BASE + "/comments", { headers: { "Accept": "application/json" } });
      if (!res.ok) throw new Error("load_failed");
      var data = await res.json();
      renderComments(widget, Array.isArray(data.comments) ? data.comments : []);
    } catch (_) {
      var list = widget.querySelector("[data-comments-list]");
      if (list) {
        list.replaceChildren();
        var empty = document.createElement("div");
        empty.className = "comments-empty";
        var icon = document.createElement("span");
        icon.textContent = "!";
        icon.setAttribute("aria-hidden", "true");
        var text = document.createElement("p");
        text.textContent = "دریافت پیام‌ها فعلاً ممکن نیست. کمی بعد دوباره تلاش کن.";
        empty.appendChild(icon);
        empty.appendChild(text);
        list.appendChild(empty);
      }
    }
  }
  widgets.forEach(function (widget) {
    var form = widget.querySelector("[data-comments-form]");
    var textarea = form && form.querySelector('textarea[name="message"]');
    var counter = widget.querySelector("[data-comment-counter]");
    if (textarea && counter) {
      var updateCounter = function () { counter.textContent = faNumber(textarea.value.length) + " از ۳۰۰۰"; };
      textarea.addEventListener("input", updateCounter);
      updateCounter();
    }
    if (form) {
      form.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (!configured) {
          setStatus(widget, "فرم هنوز به سرویس امن متصل نشده است؛ ارسال واقعی فعلاً فعال نیست.", "error");
          return;
        }
        if (!form.reportValidity()) return;
        var submit = form.querySelector(".comments-submit");
        var data = new FormData(form);
        var payload = {
          name: String(data.get("name") || "").trim(),
          email: String(data.get("email") || "").trim(),
          message: String(data.get("message") || "").trim(),
          website: String(data.get("website") || ""),
          page: window.location.pathname
        };
        if (submit) submit.disabled = true;
        setStatus(widget, "در حال ثبت امن پیام شما…");
        try {
          var res = await fetch(API_BASE + "/comments", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify(payload)
          });
          var result = await res.json().catch(function () { return {}; });
          if (!res.ok || !result.ok) {
            var messages = {
              invalid_name: "نام واردشده معتبر نیست.",
              invalid_email: "ایمیل واردشده معتبر نیست.",
              invalid_message: "متن پیام باید بین ۲ تا ۳۰۰۰ نویسه باشد.",
              submission_failed: "ثبت پیام انجام نشد. لطفاً بعداً دوباره تلاش کن."
            };
            throw new Error(messages[result.error] || "ثبت پیام ناموفق بود. لطفاً کمی بعد دوباره تلاش کن.");
          }
          form.reset();
          if (counter) counter.textContent = "۰ از ۳۰۰۰";
          setStatus(widget, "پیامت با موفقیت ثبت شد. ممنون از اینکه برای تکیما نوشتی.", "success");
          await loadComments(widget);
        } catch (error) {
          setStatus(widget, error.message || "خطایی رخ داد؛ لطفاً دوباره تلاش کن.", "error");
        } finally {
          if (submit) submit.disabled = false;
        }
      });
    }
    loadComments(widget);
  });
})();
