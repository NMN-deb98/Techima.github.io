/* تکیما (Techima) — main.js */
(function () {
  "use strict";


  // Digital rain behind the homepage content, from below the hero to the footer.
  (function initDigitalRain() {
    var canvas = document.getElementById("digital-rain-canvas");
    var main = document.querySelector(".home-page main");
    var hero = document.querySelector(".home-page .hero, .home-page .home-hero, .home-page .hero-section");
    var footer = document.querySelector(".site-footer");
    if (!canvas || !main || !footer) return;
    var ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    var width = 0, height = 0, dpr = 1, fontSize = 12, columns = 0, drops = [];
    var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var lastFrame = 0, frameId = 0;

    function layout() {
      var mainRect = main.getBoundingClientRect();
      var heroBottom = hero ? Math.max(0, hero.getBoundingClientRect().bottom - mainRect.top + main.scrollTop) : 0;
      var footerTop = footer.getBoundingClientRect().top - mainRect.top + main.scrollTop;
      var start = Math.max(0, heroBottom);
      var end = Math.max(start, footerTop);
      canvas.style.top = start + "px";
      canvas.style.height = Math.max(1, end - start) + "px";
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = Math.max(1, main.clientWidth);
      height = Math.max(1, end - start);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      fontSize = width < 600 ? 7 : 8;
      columns = Math.ceil(width / (fontSize * 0.32));
      drops = Array.from({ length: columns }, function () { return Math.random() * (height / fontSize); });
    }

    function draw(now) {
      if (document.hidden) { frameId = 0; return; }
      if (now - lastFrame < 48) { frameId = requestAnimationFrame(draw); return; }
      lastFrame = now;
      ctx.clearRect(0, 0, width, height);
      ctx.font = fontSize + "px monospace";
      for (var c = 0; c < columns; c++) {
        var x = c * fontSize * 0.32;
        var y = drops[c] * fontSize;
        var trail = 16 + (c % 12);
        for (var t = 0; t < trail; t++) {
          var charY = y - t * fontSize;
          if (charY < 0 || charY > height) continue;
          ctx.fillStyle = t === 0 ? "rgba(207,250,254,1)" : "rgba(34,211,238," + ((1 - t / trail) * .98).toFixed(3) + ")";
          ctx.fillText(Math.random() > .5 ? "1" : "0", x, charY);
        }
        drops[c] += 1.0 + Math.random() * 1.15;
        if (y > height && Math.random() > .91) drops[c] = -Math.random() * 24;
      }
      frameId = requestAnimationFrame(draw);
    }

    function refresh() {
      if (frameId) cancelAnimationFrame(frameId);
      frameId = 0;
      layout();
      if (!reducedMotion && !document.hidden) frameId = requestAnimationFrame(draw);
      else {
        ctx.clearRect(0, 0, width, height);
        ctx.font = fontSize + "px monospace";
        for (var c = 0; c < columns; c++) {
          ctx.fillStyle = "rgba(34,211,238,.72)";
          ctx.fillText(Math.random() > .5 ? "1" : "0", c * fontSize * 0.32, Math.random() * height);
        }
      }
    }

    window.addEventListener("resize", refresh, { passive: true });
    window.addEventListener("load", refresh, { once: true });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) { if (frameId) cancelAnimationFrame(frameId); frameId = 0; }
      else if (!reducedMotion && !frameId) frameId = requestAnimationFrame(draw);
    });
    if (window.ResizeObserver) {
      var observer = new ResizeObserver(refresh);
      observer.observe(main);
      observer.observe(footer);
      if (hero) observer.observe(hero);
    }
    refresh();
  })();

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
