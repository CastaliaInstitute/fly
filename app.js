(() => {
  'use strict';

  const KC_COUNT = 48;
  const ACTIVE_KCS = 8;
  const LEARNING_RATE = 0.16;
  const DECAY = 0.018;
  const MAX_HISTORY = 32;
  const odorNames = { A: 'Odor A · citrus', B: 'Odor B · floral' };

  const state = {
    patterns: { A: [], B: [] },
    appetitive: [new Float32Array(KC_COUNT), new Float32Array(KC_COUNT)],
    aversive: [new Float32Array(KC_COUNT), new Float32Array(KC_COUNT)],
    history: [],
    trials: 0,
    lastCue: 'A',
    lastEvent: 'ready'
  };

  const elements = {
    odor: document.querySelector('#odor-select'),
    repetitions: document.querySelector('#repetitions'),
    repetitionsValue: document.querySelector('#repetitions-value'),
    train: document.querySelector('#train-button'),
    recall: document.querySelector('#recall-button'),
    extinction: document.querySelector('#extinction-button'),
    reverse: document.querySelector('#reverse-button'),
    reset: document.querySelector('#reset-button'),
    clearTests: document.querySelector('#clear-tests'),
    trialCount: document.querySelector('#trial-count'),
    status: document.querySelector('#status'),
    results: document.querySelector('#memory-results'),
    circuit: document.querySelector('#circuit-canvas'),
    history: document.querySelector('#history-canvas')
  };

  // Deterministic sparse odor-to-Kenyon-cell patterns make the demo repeatable.
  function makePattern(seed) {
    let value = seed >>> 0;
    const random = () => {
      value = (value * 1664525 + 1013904223) >>> 0;
      return value / 4294967296;
    };
    const chosen = new Set();
    while (chosen.size < ACTIVE_KCS) chosen.add(Math.floor(random() * KC_COUNT));
    return [...chosen].sort((a, b) => a - b);
  }

  function setupPatterns() {
    state.patterns = { A: makePattern(4521), B: makePattern(98765) };
  }

  function cueIndex(cue) { return cue === 'A' ? 0 : 1; }
  function outcomeValue() { return Number(document.querySelector('input[name="outcome"]:checked').value); }
  function repetitions() { return Number(elements.repetitions.value); }

  function learn(cue, value) {
    const index = cueIndex(cue);
    const active = state.patterns[cue];
    const target = value > 0 ? state.appetitive[index] : state.aversive[index];
    const opposing = value > 0 ? state.aversive[index] : state.appetitive[index];
    for (const kc of active) {
      target[kc] += LEARNING_RATE * (1 - target[kc]);
      // Opponent learning is a compact abstraction for valence-specific output.
      opposing[kc] *= 1 - LEARNING_RATE * 0.18;
    }
  }

  function extinguish(cue) {
    const index = cueIndex(cue);
    for (const kc of state.patterns[cue]) {
      state.appetitive[index][kc] *= 1 - DECAY * 3;
      state.aversive[index][kc] *= 1 - DECAY * 3;
    }
  }

  function score(cue) {
    const index = cueIndex(cue);
    const active = state.patterns[cue];
    let appetitive = 0;
    let aversive = 0;
    for (const kc of active) {
      appetitive += state.appetitive[index][kc];
      aversive += state.aversive[index][kc];
    }
    return (appetitive - aversive) / active.length;
  }

  function recordRecall() {
    for (const cue of ['A', 'B']) {
      state.history.push({ cue, value: score(cue), trial: state.trials });
    }
    if (state.history.length > MAX_HISTORY) state.history.splice(0, state.history.length - MAX_HISTORY);
    state.lastEvent = 'recall';
    render();
  }

  function decayMemory() {
    for (const bank of [state.appetitive, state.aversive]) {
      for (const odorWeights of bank) {
        for (let i = 0; i < odorWeights.length; i += 1) odorWeights[i] *= 1 - DECAY;
      }
    }
  }

  function renderResults() {
    elements.results.innerHTML = ['A', 'B'].map((cue) => {
      const value = score(cue);
      const percent = Math.min(100, Math.max(0, 50 + value * 50));
      const tone = value > 0.025 ? 'approach' : value < -0.025 ? 'avoid' : 'neutral';
      const color = tone === 'approach' ? 'var(--green)' : tone === 'avoid' ? 'var(--orange)' : '#a6a69c';
      const words = tone === 'approach' ? 'approach' : tone === 'avoid' ? 'avoid' : 'no strong prediction';
      return `<article class="memory-card"><div class="memory-card-head"><span>${odorNames[cue]}</span><small>${words}</small></div><div class="meter" role="img" aria-label="${odorNames[cue]} predicted value ${value.toFixed(2)}"><div class="meter-fill" style="width:${percent}%;background:${color}"></div></div><div class="meter-labels"><span>AVOID</span><span>NEUTRAL</span><span>APPROACH</span></div><div class="memory-value" style="color:${color}">${value >= 0 ? '+' : ''}${value.toFixed(2)}</div></article>`;
    }).join('');
  }

  function fitCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.max(1, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.floor(rect.width * ratio));
    const height = Math.max(1, Math.floor(rect.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    const context = canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { context, width: rect.width, height: rect.height };
  }

  function drawCircuit() {
    const { context: ctx, width, height } = fitCanvas(elements.circuit);
    ctx.clearRect(0, 0, width, height);
    const columns = [width * 0.12, width * 0.39, width * 0.69, width * 0.9];
    const mid = height * 0.5;
    const selected = state.lastCue;
    const active = new Set(state.patterns[selected]);
    const appetitive = state.appetitive[cueIndex(selected)];
    const aversive = state.aversive[cueIndex(selected)];
    const nodes = Array.from({ length: KC_COUNT }, (_, i) => ({ x: columns[1], y: 18 + i * (height - 36) / (KC_COUNT - 1), i }));

    // Draw sparse cue-to-KC paths.
    for (const node of nodes) {
      if (!active.has(node.i)) continue;
      ctx.beginPath(); ctx.moveTo(columns[0] + 13, mid); ctx.lineTo(node.x - 4, node.y);
      ctx.strokeStyle = 'rgba(107,130,145,.30)'; ctx.lineWidth = 1; ctx.stroke();
    }
    // Draw learned KC-to-output links with thickness and opacity proportional to weight.
    for (const node of nodes) {
      const app = appetitive[node.i];
      const av = aversive[node.i];
      if (app > 0.025) {
        ctx.beginPath(); ctx.moveTo(node.x + 4, node.y); ctx.lineTo(columns[2] - 12, mid - 22);
        ctx.strokeStyle = `rgba(82,105,79,${0.12 + app * 0.72})`; ctx.lineWidth = 0.6 + app * 2.4; ctx.stroke();
      }
      if (av > 0.025) {
        ctx.beginPath(); ctx.moveTo(node.x + 4, node.y); ctx.lineTo(columns[2] - 12, mid + 22);
        ctx.strokeStyle = `rgba(189,112,75,${0.12 + av * 0.72})`; ctx.lineWidth = 0.6 + av * 2.4; ctx.stroke();
      }
    }

    drawNode(ctx, columns[0], mid, 'CS', selected === 'A' ? 'citrus' : 'floral', '#6b8291');
    for (const node of nodes) {
      ctx.beginPath(); ctx.arc(node.x, node.y, active.has(node.i) ? 3 : 1.7, 0, Math.PI * 2);
      ctx.fillStyle = active.has(node.i) ? '#6b8291' : '#c9c7be'; ctx.fill();
    }
    drawNode(ctx, columns[2], mid - 22, 'MBON+', 'approach', '#52694f');
    drawNode(ctx, columns[2], mid + 22, 'MBON−', 'avoid', '#bd704b');
    drawNode(ctx, columns[3], mid, 'DAN', state.lastEvent === 'reward' ? 'sugar' : state.lastEvent === 'aversive' ? 'bitter' : 'teaching', state.lastEvent === 'aversive' ? '#bd704b' : '#d39a52');
    ctx.fillStyle = '#7d8076'; ctx.font = '9px "DM Mono", monospace'; ctx.textAlign = 'center';
    ctx.fillText('odor cue', columns[0], height - 5); ctx.fillText('Kenyon cells', columns[1], height - 5);
    ctx.fillText('output', columns[2], height - 5); ctx.fillText('teaching', columns[3], height - 5);
  }

  function drawNode(ctx, x, y, title, subtitle, color) {
    ctx.beginPath(); ctx.arc(x, y, 13, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
    ctx.textAlign = 'center'; ctx.fillStyle = '#283027'; ctx.font = '600 9px "DM Sans", sans-serif'; ctx.fillText(title, x, y + 29);
    ctx.fillStyle = '#83867c'; ctx.font = '8px "DM Sans", sans-serif'; ctx.fillText(subtitle, x, y + 40);
  }

  function drawHistory() {
    const { context: ctx, width, height } = fitCanvas(elements.history);
    ctx.clearRect(0, 0, width, height);
    const left = 23; const right = width - 9; const top = 11; const bottom = height - 15;
    ctx.strokeStyle = '#e1dfd6'; ctx.lineWidth = 1;
    for (const level of [-1, 0, 1]) {
      const y = top + (1 - level) * (bottom - top) / 2;
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
      ctx.fillStyle = '#95978d'; ctx.font = '8px "DM Mono", monospace'; ctx.textAlign = 'right'; ctx.fillText(level.toFixed(0), left - 6, y + 3);
    }
    const perCue = ['A', 'B'].map((cue) => state.history.filter((entry) => entry.cue === cue));
    perCue.forEach((entries, series) => {
      if (!entries.length) return;
      ctx.beginPath();
      entries.forEach((entry, index) => {
        const x = left + (entries.length < 2 ? (right - left) / 2 : index * (right - left) / (entries.length - 1));
        const y = top + (1 - Math.max(-1, Math.min(1, entry.value))) * (bottom - top) / 2;
        if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        ctx.save(); ctx.beginPath(); ctx.arc(x, y, 2.7, 0, Math.PI * 2); ctx.fillStyle = series === 0 ? '#52694f' : '#bd704b'; ctx.fill(); ctx.restore();
      });
      ctx.strokeStyle = series === 0 ? '#52694f' : '#bd704b'; ctx.lineWidth = 1.8; ctx.stroke();
    });
  }

  function render() {
    elements.trialCount.textContent = `${state.trials} ${state.trials === 1 ? 'trial' : 'trials'}`;
    renderResults(); drawCircuit(); drawHistory();
  }

  function train(cue, value, count) {
    for (let i = 0; i < count; i += 1) {
      learn(cue, value);
      state.trials += 1;
    }
    state.lastCue = cue;
    state.lastEvent = value > 0 ? 'reward' : 'aversive';
    const outcome = value > 0 ? 'sugar' : 'bitter';
    elements.status.textContent = `${odorNames[cue]} paired with ${outcome} ${count} ${count === 1 ? 'time' : 'times'}. Recall both cues to test the association.`;
    render();
  }

  elements.repetitions.addEventListener('input', () => { elements.repetitionsValue.value = elements.repetitions.value; });
  document.querySelectorAll('input[name="outcome"]').forEach((input) => input.addEventListener('change', () => {
    document.querySelectorAll('.choice-card').forEach((card) => card.classList.toggle('selected', card.contains(document.querySelector('input[name="outcome"]:checked'))));
  }));
  elements.odor.addEventListener('change', () => { state.lastCue = elements.odor.value; render(); });
  elements.train.addEventListener('click', () => train(elements.odor.value, outcomeValue(), repetitions()));
  elements.recall.addEventListener('click', () => {
    state.trials += 1; recordRecall();
    elements.status.textContent = 'Recall test complete: each odor was presented alone, without a teaching signal.';
  });
  elements.extinction.addEventListener('click', () => {
    const cue = elements.odor.value;
    for (let i = 0; i < repetitions(); i += 1) { extinguish(cue); state.trials += 1; }
    state.lastCue = cue; state.lastEvent = 'extinction';
    elements.status.textContent = `${odorNames[cue]} presented without an outcome ${repetitions()} times. The model’s association weakens.`;
    render();
  });
  elements.reverse.addEventListener('click', () => train(elements.odor.value, -outcomeValue(), repetitions()));
  elements.clearTests.addEventListener('click', () => { state.history = []; render(); });
  elements.reset.addEventListener('click', () => {
    state.appetitive = [new Float32Array(KC_COUNT), new Float32Array(KC_COUNT)];
    state.aversive = [new Float32Array(KC_COUNT), new Float32Array(KC_COUNT)];
    state.history = []; state.trials = 0; state.lastCue = 'A'; state.lastEvent = 'ready';
    elements.odor.value = 'A';
    elements.status.textContent = 'Experiment reset. Pair citrus with an outcome to begin again.';
    render();
  });
  window.addEventListener('resize', render);

  setupPatterns();
  render();
})();
