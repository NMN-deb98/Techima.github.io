// Hero laptop coding animation: green terminal-style code scrolling upward,
// characters typed progressively then the whole block drifts up like a live editor.
(function () {
  const canvas = document.getElementById('codeCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const codeLines = [
    "const project = new Website();",
    "project.seo.optimize('title', 'meta', 'schema');",
    "function renderHero(user) {",
    "  const canvas = document.querySelector('#hero');",
    "  canvas.animate({ opacity: 1, y: 0 });",
    "}",
    "class ContentEngine {",
    "  constructor(topic) { this.topic = topic; }",
    "  publish() { return `${this.topic} :: ready`; }",
    "}",
    "export async function optimizeImage(file) {",
    "  const buffer = await file.arrayBuffer();",
    "  return compress(buffer, { quality: 0.86 });",
    "}",
    "// keywords ranked by search volume",
    "const keywords = ['seo', 'content', 'editing'];",
    "if (traffic.trend === 'up') deploy();",
    "print('Nima Madadi Nemati :: building.')",
    "git commit -m 'polish landing animation'",
    "npm run build && npm run deploy",
  ];

  let fontSize = 14;
  let lineHeight = 22;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);

  function resize() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    fontSize = rect.width < 340 ? 12 : 14;
    lineHeight = fontSize + 8;
  }
  resize();
  window.addEventListener('resize', resize);

  const state = {
    lineIndex: 0,
    charIndex: 0,
    renderedLines: [],
    scrollOffset: 0,
    frame: 0,
  };

  function typingSpeedFor(char) {
    return char === ' ' ? 1 : 2 + Math.random() * 2;
  }

  let charTimer = 0;

  function step() {
    state.frame++;
    charTimer++;
    const typeEvery = 2; // frames per character tick baseline

    if (charTimer >= typeEvery) {
      charTimer = 0;
      const currentLine = codeLines[state.lineIndex % codeLines.length];
      if (state.charIndex <= currentLine.length) {
        state.charIndex += 1;
      } else {
        state.renderedLines.push(currentLine);
        state.lineIndex++;
        state.charIndex = 0;
        const rect = canvas.getBoundingClientRect();
        const maxVisible = Math.floor(rect.height / lineHeight) + 2;
        if (state.renderedLines.length > maxVisible) {
          state.scrollOffset += lineHeight;
        }
      }
    }
  }

  function draw() {
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);

    // subtle scanline background
    ctx.fillStyle = '#060a10';
    ctx.fillRect(0, 0, rect.width, rect.height);

    ctx.font = `${fontSize}px "JetBrains Mono", monospace`;
    ctx.textBaseline = 'top';

    const paddingTop = 14;
    const paddingLeft = 16;

    // smooth scroll toward target
    state.displayOffset = state.displayOffset || 0;
    state.displayOffset += (state.scrollOffset - state.displayOffset) * 0.12;

    let y = paddingTop - state.displayOffset;

    state.renderedLines.forEach((line, i) => {
      drawLine(line, paddingLeft, y, 1);
      y += lineHeight;
    });

    // current typing line
    const currentLine = codeLines[state.lineIndex % codeLines.length];
    const visiblePart = currentLine.slice(0, state.charIndex);
    drawLine(visiblePart, paddingLeft, y, 1);

    // blinking cursor
    if (Math.floor(state.frame / 30) % 2 === 0) {
      const w = ctx.measureText(visiblePart).width;
      ctx.fillStyle = '#3ddc97';
      ctx.fillRect(paddingLeft + w + 2, y + 2, 7, fontSize);
    }
  }

  function drawLine(text, x, y, alpha) {
    // color hint: comments dim, keywords brighter green-gold
    let color = 'rgba(61, 220, 151,' + alpha + ')';
    if (text.trim().startsWith('//')) color = 'rgba(92, 105, 128,' + alpha + ')';
    ctx.fillStyle = color;
    ctx.fillText(text, x, y);
  }

  function loop() {
    step();
    draw();
    requestAnimationFrame(loop);
  }

  // load font then start to avoid metric jump
  if (document.fonts && document.fonts.load) {
    document.fonts.load('14px "JetBrains Mono"').finally(loop);
  } else {
    loop();
  }
})();
