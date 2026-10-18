document.addEventListener('DOMContentLoaded', () => {
  const screen = document.getElementById('calcScreen');
  if (!screen) return;
  let expression = '';

  function sanitizeDisplay(v) {
    return v === '' ? '0' : v;
  }

  document.querySelectorAll('.calc-keys button').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = btn.dataset.val;
      if (btn.classList.contains('clear')) {
        expression = '';
      } else if (btn.classList.contains('eq')) {
        try {
          // eslint-disable-next-line no-eval
          const result = Function('"use strict"; return (' + expression.replace(/x/g, '*') + ')')();
          expression = String(Number(result.toFixed(8)));
        } catch (e) {
          expression = 'Error';
        }
      } else {
        if (expression === 'Error') expression = '';
        expression += val;
      }
      screen.textContent = sanitizeDisplay(expression);
    });
  });
});
