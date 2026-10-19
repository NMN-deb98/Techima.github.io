/* تکیما (Techima) — main.js
   فقط سال شمسی فوتر را به‌روز می‌کند. سایت بدون جاوااسکریپت هم کامل کار می‌کند. */
(function () {
  "use strict";
  var el = document.getElementById("year");
  if (!el) return;
  try {
    el.textContent = new Date().toLocaleDateString("fa-IR", {
      year: "numeric",
      numberingSystem: "arabext"
    });
  } catch (e) {
    /* در صورت پشتیبانی نشدن، همان مقدار ثابت HTML باقی می‌ماند */
  }

  var loader = document.createElement("div");
  loader.className = "site-loader";
  loader.setAttribute("role", "status");
  loader.setAttribute("aria-live", "polite");
  loader.innerHTML = '<div class="site-loader-inner"><div class="site-loader-brand"><span class="site-loader-mark" aria-hidden="true">ت</span><span>تکیما</span></div><p class="site-loader-caption">در حال آماده‌سازی سایت…</p><div class="site-loader-track" role="progressbar" aria-label="درصد بارگذاری" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="site-loader-progress"></div></div><div class="site-loader-meta"><span>لطفاً کمی صبر کنید</span><span class="site-loader-percent">۰٪</span></div></div>';
  document.body.appendChild(loader);
  var bar = loader.querySelector(".site-loader-progress");
  var percent = loader.querySelector(".site-loader-percent");
  var track = loader.querySelector(".site-loader-track");
  var progress = 0;
  function updateProgress(value) {
    bar.style.width = value + "%";
    percent.textContent = value.toLocaleString("fa-IR") + "٪";
    track.setAttribute("aria-valuenow", String(value));
  }
  var interval = window.setInterval(function () {
    if (progress < 90) {
      progress = Math.min(90, progress + Math.max(1, Math.ceil((90 - progress) / 10)));
      updateProgress(progress);
    }
  }, 120);
  function finishLoading() {
    window.clearInterval(interval);
    updateProgress(100);
    loader.querySelector(".site-loader-caption").textContent = "آماده شد!";
    window.setTimeout(function () {
      loader.classList.add("is-hidden");
      window.setTimeout(function () { loader.remove(); }, 400);
    }, 180);
  }
  if (document.readyState === "complete") window.setTimeout(finishLoading, 250);
  else window.addEventListener("load", finishLoading, { once: true });
  window.setTimeout(function () {
    if (document.body.contains(loader) && !loader.classList.contains("is-hidden")) finishLoading();
  }, 12000);
})();
