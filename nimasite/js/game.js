document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('memoryGrid');
  if (!grid) return;

  const symbols = ['◆', '◆', '●', '●', '▲', '▲', '★', '★', '■', '■', '✚', '✚', '❖', '❖', '☾', '☾'];
  const movesEl = document.getElementById('memMoves');
  const winEl = document.getElementById('memWin');
  const resetBtn = document.getElementById('memReset');

  let deck = [];
  let first = null;
  let second = null;
  let lock = false;
  let moves = 0;
  let matched = 0;

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function render() {
    grid.innerHTML = '';
    deck.forEach((sym, idx) => {
      const cell = document.createElement('button');
      cell.className = 'memory-card';
      cell.type = 'button';
      cell.dataset.index = idx;
      cell.textContent = sym;
      cell.addEventListener('click', () => handleFlip(cell, idx));
      grid.appendChild(cell);
    });
  }

  function handleFlip(cell, idx) {
    if (lock || cell.classList.contains('flipped') || cell.classList.contains('matched')) return;
    cell.classList.add('flipped');
    if (first === null) {
      first = { cell, idx };
      return;
    }
    second = { cell, idx };
    lock = true;
    moves++;
    movesEl.textContent = 'Moves: ' + moves;

    if (deck[first.idx] === deck[second.idx]) {
      first.cell.classList.add('matched');
      second.cell.classList.add('matched');
      matched += 2;
      first = null; second = null; lock = false;
      if (matched === deck.length) {
        winEl.classList.add('show');
      }
    } else {
      setTimeout(() => {
        first.cell.classList.remove('flipped');
        second.cell.classList.remove('flipped');
        first = null; second = null; lock = false;
      }, 700);
    }
  }

  function init() {
    deck = shuffle(symbols);
    first = null; second = null; lock = false; moves = 0; matched = 0;
    movesEl.textContent = 'Moves: 0';
    winEl.classList.remove('show');
    render();
  }

  resetBtn.addEventListener('click', init);
  init();
});
