(function () {
  "use strict";
  var API_BASE = "https://techima-comments-api.nimamadadinemati.workers.dev";
  var usernameInput = document.querySelector("#admin-username");
  var passwordInput = document.querySelector("#admin-password");
  var loginButton = document.querySelector("#login-admin");
  var sessionToken = "";
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
      headers: Object.assign({ "Accept": "application/json", "Authorization": "Bearer " + sessionToken }, options && options.headers || {})
    }));
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      if (response.status === 401) { sessionToken = ""; throw new Error("نشست ورود منقضی شده یا اطلاعات ورود معتبر نیست؛ دوباره وارد شو."); }
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
    if (!sessionToken) {
      say("ابتدا با نام کاربری و رمز عبور وارد شو.", "error");
      usernameInput.focus();
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
  async function login() {
    loginButton.disabled = true;
    say("در حال بررسی اطلاعات ورود…");
    try {
      var response = await fetch(API_BASE + "/admin/login", {
        method: "POST",
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ username: usernameInput.value.trim(), password: passwordInput.value })
      });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok || !data.token) {
        if (response.status === 429) {
          loginButton.disabled = true;
          throw new Error("این IP به دلیل ۶ تلاش ناموفق به مدت ۵ ساعت مسدود شده است. درخواست‌های بیشتر پذیرفته نمی‌شوند.");
        }
        if (response.status === 503) throw new Error("بررسی امنیتی ورود در دسترس نیست؛ بعداً دوباره امتحان کن.");
        throw new Error(response.status === 401 ? "نام کاربری یا رمز عبور اشتباه است." : "ورود ناموفق بود؛ تنظیمات Worker را بررسی کن.");
      }
      sessionToken = data.token;
      passwordInput.value = "";
      loadButton.disabled = false;
      say("ورود موفق بود؛ نشست مدیریت تا ۳۰ دقیقه اعتبار دارد.", "success");
      await loadPending();
    } catch (error) {
      sessionToken = "";
      say(error.message || "ورود ناموفق بود.", "error");
    } finally {
      if (!/مسدود شده است/.test(statusNode.textContent || "")) loginButton.disabled = false;
    }
  }
  loginButton.addEventListener("click", login);
  loadButton.addEventListener("click", loadPending);
  [usernameInput, passwordInput].forEach(function (input) {
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") login();
    });
  });
})();