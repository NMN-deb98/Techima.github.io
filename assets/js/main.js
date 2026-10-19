/* تکیما (Techima) — main.js */
(function () {
  "use strict";

  var yearElement = document.getElementById("year");
  if (yearElement) {
    try {
      yearElement.textContent = new Date().toLocaleDateString("fa-IR", {
        year: "numeric",
        numberingSystem: "arabext"
      });
    } catch (e) {
      /* مقدار ثابت HTML باقی می‌ماند */
    }
  }

  // Only show the loader if the page has not finished loading after 3 seconds.
  var loader = null;
  var progressInterval = null;
  var progress = 0;
  var loadFinished = document.readyState === "complete";
  var showTimer;

  function updateProgress(value) {
    if (!loader) return;
    var bar = loader.querySelector(".site-loader-progress");
    var percent = loader.querySelector(".site-loader-percent");
    var track = loader.querySelector(".site-loader-track");
    bar.style.width = value + "%";
    percent.textContent = value.toLocaleString("fa-IR") + "٪";
    track.setAttribute("aria-valuenow", String(value));
  }

  function showLoader() {
    if (loadFinished || loader) return;
    loader = document.createElement("div");
    loader.className = "site-loader";
    loader.setAttribute("role", "status");
    loader.setAttribute("aria-live", "polite");
    loader.innerHTML = '<div class="site-loader-inner"><div class="site-loader-brand"><span class="site-loader-mark" aria-hidden="true">ت</span><span>تکیما</span></div><p class="site-loader-caption">در حال آماده‌سازی سایت…</p><div class="site-loader-track" role="progressbar" aria-label="درصد بارگذاری" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="site-loader-progress"></div></div><div class="site-loader-meta"><span>لطفاً کمی صبر کنید</span><span class="site-loader-percent">۰٪</span></div></div>';
    document.body.appendChild(loader);

    progressInterval = window.setInterval(function () {
      if (progress < 90) {
        progress = Math.min(90, progress + Math.max(1, Math.ceil((90 - progress) / 10)));
        updateProgress(progress);
      }
    }, 120);

    // If loading gets stuck, release the visitor after a reasonable maximum wait.
    window.setTimeout(finishLoading, 12000);
  }

  function finishLoading() {
    loadFinished = true;
    window.clearTimeout(showTimer);
    if (!loader) return;
    if (progressInterval) window.clearInterval(progressInterval);
    updateProgress(100);
    loader.querySelector(".site-loader-caption").textContent = "آماده شد!";
    window.setTimeout(function () {
      if (!loader) return;
      loader.classList.add("is-hidden");
      window.setTimeout(function () {
        if (loader) loader.remove();
        loader = null;
      }, 400);
    }, 180);
  }

  window.addEventListener("load", finishLoading, { once: true });
  if (!loadFinished) showTimer = window.setTimeout(showLoader, 3000);
})();
