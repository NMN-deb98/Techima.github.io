(function () {
  "use strict";
  var API_BASE = "https://techima-comments-api.nimamadadinemati.workers.dev";
  var tokenInput = document.querySelector("#admin-token");
  var status = document.querySelector("#admin-status");
  var list = document.querySelector("#pending-list");
  var loadButton = document.querySelector("#load-pending");
  function say(message, kind) {
    status.textContent = message;
    status.dataset.kind = kind || "";
  }
  function makeButton(label, action, danger) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = danger ? "admin-button admin-danger" : "admin-button";
    button.textContent = label;
    button.addEventListener("click", action);
    return button;
  }
  async function api(path, options) {
    var response = await fetch(API_BASE + path, Object.assign({}, options || {}, {
      headers: Object.assign({ "Accept": "application/json", "Authorization": "Bearer " + tokenInput.value.trim() }, options && options.headers || {})
    }));
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      if (response.status === 401) throw new Error("توکن مدیریت معتبر نیست یا در Worker تنظیم نشده است.");
      throw new Error("درخواست انجام نشد. لطفاً تنظیمات Worker و مخزن خصوصی را بررسی کن.");
    }
    return data;
  }
  function render(items) {
    list.replaceChildren();
    if (!items.length) {
      var empty = document.createElement("p");
      empty.className = "admin-empty";
      empty.textContent = "در حال حاضر کامنتی در انتظار تأیید نیست.";
      list.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "pending-card";
      var title = document.createElement("h2");
      title.textContent = item.name || "بدون نام";
      var meta = document.createElement("p");
      meta.className = "pending-meta";
      meta.textContent = (item.page || "/") + " · " + (item.createdAt ? new Date(item.createdAt).toLocaleString("fa-IR") : "");
      var message = document.createElement("p");
      message.className = "pending-message";
      message.textContent = item.message || "";
      var actions = document.createElement("div");
      actions.className = "pending-actions";
      actions.appendChild(makeButton("تأیید و نمایش در سایت", async function () {
        if (!window.confirm("این کامنت در سایت عمومی نمایش داده شود؟")) return;
        await moderate(item.id, "approve");
      }));
      actions.appendChild(makeButton("رد کردن", async function () {
        if (!window.confirm("این کامنت رد شود و نمایش داده نشود؟")) return;
        await moderate(item.id, "reject");
      }, true));
      card.append(title, meta, message, actions);
      list.appendChild(card);
    });
  }
  async function moderate(id, action) {
    try {
      say("در حال انجام…");
      await api("/admin/comments/" + action, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
      });
      say(action === "approve" ? "کامنت تأیید و منتشر شد." : "کامنت رد شد.", "success");
      await loadPending();
    } catch (error) {
      say(error.message || "خطایی رخ داد.", "error");
    }
  }
  async function loadPending() {
    if (!tokenInput.value.trim()) {
      say("ابتدا توکن مدیریت را وارد کن.", "error");
      tokenInput.focus();
      return;
    }
    loadButton.disabled = true;
    say("در حال دریافت کامنت‌های در انتظار…");
    try {
      var data = await api("/admin/comments");
      render(Array.isArray(data.comments) ? data.comments : []);
      say("فهرست به‌روز شد.", "success");
    } catch (error) {
      say(error.message || "دریافت کامنت‌ها ناموفق بود.", "error");
    } finally {
      loadButton.disabled = false;
    }
  }
  loadButton.addEventListener("click", loadPending);
  tokenInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") loadPending();
  });
})();