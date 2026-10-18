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
})();
