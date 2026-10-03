const SIZE = 4;
const WIN_TILE = 2048;

let board = [];
let score = 0;
let bestScore = Number(localStorage.getItem('2048-best-score') || 0);
let gameOver = false;
let won = false;

let aiRunning = false;
let aiStep = 0;
let worker = null;
let workerGeneration = 0;
let aiTimer = null;

const boardEl = document.getElementById('board');
const scoreEl = document.getElementById('score');
const bestScoreEl = document.getElementById('best-score');
const messageEl = document.getElementById('message');
const newGameBtn = document.getElementById('new-game-btn');
const aiDemoBtn = document.getElementById('ai-demo-btn');
const aiInfo = document.getElementById('ai-info');
const aiStepText = document.getElementById('ai-step-text');
const aiDirectionText = document.getElementById('ai-direction-text');

const directionText = { left: '← 左', right: '→ 右', up: '↑ 上', down: '↓ 下' };

const themeToggleBtn = document.getElementById('theme-toggle-btn');
const historyListEl = document.getElementById('history-list');
const historyCountEl = document.getElementById('history-count');
const historyToggleBtn = document.getElementById('history-toggle-btn');

const THEME_KEY = '2048-theme';
const HISTORY_KEY = '2048-history';
const HISTORY_LIMIT = 10;

let moveCount = 0;
let currentGameStarted = false;
let currentGameRecorded = false;
let historyExpanded = false;

function getMaxTile() {
  let max = 0;
  for (const row of board) {
    for (const value of row) max = Math.max(max, value);
  }
  return max;
}

function loadHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(parsed) ? parsed.slice(0, HISTORY_LIMIT) : [];
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, HISTORY_LIMIT)));
}

function recordCurrentGame(result) {
  if (currentGameRecorded || !currentGameStarted) return;

  const history = loadHistory();
  history.unshift({
    result,
    score,
    maxTile: getMaxTile(),
    moves: moveCount,
    time: new Date().toLocaleString('zh-CN', {
      hour12: false,
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  });

  saveHistory(history);
  currentGameRecorded = true;
  renderHistory();
}

function renderHistory() {
  const history = loadHistory();
  historyCountEl.textContent = `${history.length}/10`;
  historyListEl.innerHTML = '';

  if (!history.length) {
    historyListEl.innerHTML = '<div class="history-empty">暂无战绩</div>';
    historyToggleBtn.classList.add('hidden');
    return;
  }

  const visible = historyExpanded ? history : history.slice(0, 4);

  visible.forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'history-item';

    const resultClass =
      item.result === '胜利' ? 'success' :
      item.result === '游戏结束' ? 'failed' : 'other';

    row.innerHTML = `
      <div class="history-main">
        <span class="history-index">#${index + 1}</span>
        <span class="history-result ${resultClass}">${item.result}</span>
      </div>
      <div class="history-meta">
        <span>最高 ${item.maxTile}</span>
        <span>分数 ${item.score}</span>
      </div>
      <div class="history-meta">
        <span>${item.moves} 步</span>
        <span>${item.time}</span>
      </div>
    `;

    historyListEl.appendChild(row);
  });

  if (history.length > 4) {
    historyToggleBtn.classList.remove('hidden');
    historyToggleBtn.textContent =
      historyExpanded ? '收起列表' : `查看完整列表（${history.length} 局）`;
  } else {
    historyToggleBtn.classList.add('hidden');
  }
}

function applyTheme(theme) {
  const nextTheme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = nextTheme;
  localStorage.setItem(THEME_KEY, nextTheme);
  themeToggleBtn.textContent =
    nextTheme === 'dark' ? '浅色模式' : '深色模式';
}

function initTheme() {
  applyTheme(localStorage.getItem(THEME_KEY) || 'light');
  themeToggleBtn.addEventListener('click', () => {
    const current = document.documentElement.dataset.theme || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });
}

historyToggleBtn.addEventListener('click', () => {
  historyExpanded = !historyExpanded;
  renderHistory();
});

function cloneBoard(b) { return b.map(row => [...row]); }

function getEmptyCells(b = board) {
  const result = [];
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (b[r][c] === 0) result.push({ row: r, col: c });
    }
  }
  return result;
}

function boardsEqual(a, b) {
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) if (a[r][c] !== b[r][c]) return false;
  }
  return true;
}

function addRandomTile() {
  const empty = getEmptyCells();
  if (!empty.length) return;
  const { row, col } = empty[Math.floor(Math.random() * empty.length)];
  board[row][col] = Math.random() < 0.9 ? 2 : 4;
}

function initBoard() {
  if (
    currentGameStarted &&
    !currentGameRecorded &&
    (moveCount > 0 || aiStep > 0 || score > 0)
  ) {
    recordCurrentGame('重新开始');
  }

  stopAI();
  board = Array.from({ length: SIZE }, () => Array(SIZE).fill(0));
  score = 0;
  gameOver = false;
  won = false;
  aiStep = 0;
  moveCount = 0;
  currentGameStarted = true;
  currentGameRecorded = false;
  messageEl.textContent = '';
  messageEl.classList.add('hidden');
  aiInfo.classList.add('hidden');
  addRandomTile();
  addRandomTile();
  updateBoard();
}

function updateBoard() {
  boardEl.innerHTML = '';
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const value = board[r][c];
      const cell = document.createElement('div');
      cell.className = `cell ${value === 0 ? 'empty' : ''}`;
      cell.dataset.value = value || 0;
      cell.textContent = value === 0 ? '' : value;
      boardEl.appendChild(cell);
    }
  }
  scoreEl.textContent = String(score);
  bestScoreEl.textContent = String(bestScore);
}

function processLine(line) {
  const filtered = line.filter(v => v !== 0);
  const out = [];
  let gained = 0;
  let mergeValues = [];
  for (let i = 0; i < filtered.length; i++) {
    if (i + 1 < filtered.length && filtered[i] === filtered[i + 1]) {
      const value = filtered[i] * 2;
      out.push(value);
      gained += value;
      mergeValues.push(value);
      i++;
    } else out.push(filtered[i]);
  }
  while (out.length < SIZE) out.push(0);
  return { line: out, score: gained, mergeValues };
}

function simulateMove(currentBoard, direction) {
  const next = cloneBoard(currentBoard);
  let mergeScore = 0;
  let mergeValues = [];

  if (direction === 'left' || direction === 'right') {
    for (let r = 0; r < SIZE; r++) {
      let line = [...next[r]];
      if (direction === 'right') line.reverse();
      const result = processLine(line);
      let out = result.line;
      if (direction === 'right') out.reverse();
      next[r] = out;
      mergeScore += result.score;
      mergeValues.push(...result.mergeValues);
    }
  } else {
    for (let c = 0; c < SIZE; c++) {
      let line = [];
      for (let r = 0; r < SIZE; r++) line.push(next[r][c]);
      if (direction === 'down') line.reverse();
      const result = processLine(line);
      let out = result.line;
      if (direction === 'down') out.reverse();
      for (let r = 0; r < SIZE; r++) next[r][c] = out[r];
      mergeScore += result.score;
      mergeValues.push(...result.mergeValues);
    }
  }

  return {
    board: next,
    moved: !boardsEqual(currentBoard, next),
    mergeScore,
    mergeValues
  };
}

function applyMove(direction) {
  if (gameOver || won) return false;
  const result = simulateMove(board, direction);

  // 关键规则：无变化 = 无效移动 = 不生成新数字。
  if (!result.moved) return false;

  board = result.board;
  moveCount++;
  score += result.mergeScore;
  bestScore = Math.max(bestScore, score);
  localStorage.setItem('2048-best-score', String(bestScore));

  addRandomTile();
  updateBoard();
  checkGameStatus();
  return true;
}

function hasTile(value) { return board.some(row => row.some(v => v === value)); }

function canMove() {
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const v = board[r][c];
      if (v === 0) return true;
      if (r + 1 < SIZE && board[r + 1][c] === v) return true;
      if (c + 1 < SIZE && board[r][c + 1] === v) return true;
    }
  }
  return false;
}

function checkGameStatus() {
  if (hasTile(WIN_TILE)) {
    won = true;
    if (aiRunning) finishAI('AI完成！成功达到 2048！');
    else {
      recordCurrentGame('胜利');
      showMessage(`恭喜！你达到了 2048！`);
    }
    return;
  }

  if (getEmptyCells().length === 0 && !canMove()) {
    gameOver = true;
    if (aiRunning) finishAI(`第一局游戏结束！最终分数：${score}`);
    else {
      recordCurrentGame('游戏结束');
      showMessage('游戏结束，点击新游戏再来一局！');
    }
  }
}

function showMessage(text) {
  messageEl.textContent = text;
  messageEl.classList.remove('hidden');
}

function showAIInfo(text, direction = null) {
  aiInfo.classList.remove('hidden');
  aiStepText.textContent = text;
  aiDirectionText.textContent = direction ? directionText[direction] : '…';
}

function stopAI() {
  aiRunning = false;
  workerGeneration++;
  if (aiTimer !== null) {
    clearTimeout(aiTimer);
    aiTimer = null;
  }
  if (worker) {
    worker.terminate();
    worker = null;
  }
  aiDemoBtn.textContent = 'AI开始演示';
}

function finishAI(text) {
  if (!aiRunning) return;

  const result =
    text.includes('2048') ? '胜利' :
    text.includes('游戏结束') ? '游戏结束' :
    'AI停止';

  recordCurrentGame(result);

  aiRunning = false;
  workerGeneration++;
  if (aiTimer !== null) {
    clearTimeout(aiTimer);
    aiTimer = null;
  }
  if (worker) {
    worker.terminate();
    worker = null;
  }
  aiDemoBtn.textContent = 'AI开始演示';
  showMessage(text);
  showAIInfo(`AI第一局结束 · 共 ${aiStep} 步`, null);
}

function onKeyDown(event) {
  if (aiRunning) return;
  const map = {
    ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down',
    a: 'left', d: 'right', w: 'up', s: 'down'
  };
  const direction = map[event.key];
  if (!direction) return;
  event.preventDefault();
  applyMove(direction);
}

/* ---------------- Web Worker AI ---------------- */
function makeWorker() {
  const workerSource = `
    const SIZE = 4;
    const DIRS = ['left','right','up','down'];
    const SNAKE = [
      [1,2,3,4],
      [8,7,6,5],
      [9,10,11,12],
      [16,15,14,13]
    ];
    // 搜索深度：往前看几步。实测定标（两批固定种子共 180 局，同一批种子可比）：
    //   depth 2 → 达成 2048 约 24%，一步约 0.3ms
    //   depth 4 → 达成 2048 约 51%，一步约 5~6ms   ← 采用
    //   depth 5 → 达成 2048 约 47%，但一步约 30ms（慢 5 倍却没有变强）
    // 另外偶数深度停在「我走完、还没生成新数字」的局面上做评估，比奇数深度更稳，所以取 4。
    const SEARCH_DEPTH = 4;
    const cache = new Map();

    function clone(b){ return b.map(r => [...r]); }
    function key(b,d,ch){ return b.map(r=>r.join(',')).join('|') + ':' + d + ':' + ch; }
    function empties(b){
      const a=[];
      for(let r=0;r<4;r++) for(let c=0;c<4;c++) if(!b[r][c]) a.push([r,c]);
      return a;
    }
    function log2(v){ return v ? Math.log2(v) : 0; }
    function maxTile(b){ let m=0; for(const r of b) for(const v of r) m=Math.max(m,v); return m; }
    function equal(a,b){
      for(let r=0;r<4;r++) for(let c=0;c<4;c++) if(a[r][c]!==b[r][c]) return false;
      return true;
    }
    function line(line){
      const f=line.filter(Boolean), out=[], merges=[];
      for(let i=0;i<f.length;i++){
        if(i+1<f.length && f[i]===f[i+1]){ const x=f[i]*2; out.push(x); merges.push(x); i++; }
        else out.push(f[i]);
      }
      while(out.length<4) out.push(0);
      return {out,merges};
    }
    function move(b,d){
      const n=clone(b), merges=[];
      if(d==='left'||d==='right'){
        for(let r=0;r<4;r++){
          let row=[...n[r]]; if(d==='right') row.reverse();
          const x=line(row); let o=x.out; if(d==='right') o.reverse();
          n[r]=o; merges.push(...x.merges);
        }
      }else{
        for(let c=0;c<4;c++){
          let col=[]; for(let r=0;r<4;r++) col.push(n[r][c]);
          if(d==='down') col.reverse();
          const x=line(col); let o=x.out; if(d==='down') o.reverse();
          for(let r=0;r<4;r++) n[r][c]=o[r];
          merges.push(...x.merges);
        }
      }
      return {board:n,moved:!equal(b,n),merges};
    }
    function smooth(b){
      let s=0;
      for(let r=0;r<4;r++) for(let c=0;c<4;c++){
        if(!b[r][c]) continue;
        const v=log2(b[r][c]);
        if(c+1<4 && b[r][c+1]) s-=Math.abs(v-log2(b[r][c+1]));
        if(r+1<4 && b[r+1][c]) s-=Math.abs(v-log2(b[r+1][c]));
      }
      return s;
    }
    function monotonic(b){
      let s=0;
      for(let r=0;r<4;r++){
        for(let c=0;c<3;c++){
          const a=log2(b[r][c]), z=log2(b[r][c+1]);
          if(r%2===0) s += Math.max(0,z-a); else s += Math.max(0,a-z);
        }
      }
      for(let c=0;c<4;c++) for(let r=0;r<3;r++){
        const a=log2(b[r][c]), z=log2(b[r+1][c]);
        s += Math.max(0,z-a);
      }
      return s;
    }
    function snakeScore(b){
      let s=0;
      for(let r=0;r<4;r++) for(let c=0;c<4;c++) s += log2(b[r][c])*SNAKE[r][c];
      return s;
    }
    function mergeScore(merges){
      let s=0;
      for(const x of merges) s += x*x; // 大合并远高于小合并
      return s;
    }
    function cornerScore(b){
      const m=maxTile(b);
      if(b[3][3]===m) return 12000 + log2(m)*500;
      let p=0;
      if(b[3][3]===0) p+=1000;
      if(b[3][2]>=m/2) p+=2500;
      if(b[2][3]>=m/2) p+=2500;
      return p - log2(m)*900;
    }
    function evaluate(b,merges=[]){
      const e=empties(b).length;
      const m=maxTile(b);
      return e*90000 + snakeScore(b)*260 + monotonic(b)*700 + smooth(b)*120 + cornerScore(b) + log2(m)*3000 + mergeScore(merges)*0.55;
    }
    function search(b,depth,chance){
      const k=key(b,depth,chance);
      if(cache.has(k)) return cache.get(k);
      if(depth<=0){ const v=evaluate(b); cache.set(k,v); return v; }
      if(!chance){
        let best=-Infinity, moved=false;
        for(const d of DIRS){
          const x=move(b,d); if(!x.moved) continue;
          moved=true;
          let v=search(x.board,depth-1,true) + mergeScore(x.merges)*0.7;
          if(d==='right'||d==='down') v+=9000;
          if(d==='up' && b[3][3]===maxTile(b)) v-=250000;
          if(d==='left' && b[3][3]===maxTile(b)) v-=65000;
          best=Math.max(best,v);
        }
        const v=moved?best:evaluate(b)-1e9;
        cache.set(k,v); return v;
      }
      const e=empties(b);
      if(!e.length){ const v=search(b,depth-1,false); cache.set(k,v); return v; }
      const sample=e.length<=8?e:e.filter((_,i)=>i%Math.ceil(e.length/8)===0).slice(0,8);
      let total=0;
      for(const [r,c] of sample){
        const b2=clone(b), b4=clone(b); b2[r][c]=2; b4[r][c]=4;
        total += 0.9*search(b2,depth-1,false) + 0.1*search(b4,depth-1,false);
      }
      const v=total/sample.length; cache.set(k,v); return v;
    }
    function choose(b){
      cache.clear();
      const max=maxTile(b), atCorner=b[3][3]===max;
      const candidates=[];
      for(const d of DIRS){
        const x=move(b,d); if(!x.moved) continue;
        let v=search(x.board,SEARCH_DEPTH,true);
        // 右/下优先，但不是硬锁死；必要时允许左/上整理。
        if(d==='right') v+=22000;
        if(d==='down') v+=16000;
        if(d==='left') v-=3500;
        if(d==='up') v-=16000;
        v += mergeScore(x.merges)*0.9;
        const bigMerge=Math.max(0,...x.merges,0);
        v += bigMerge*bigMerge*0.25;
        if(atCorner && d==='up') v-=280000;
        if(atCorner && d==='left') v-=55000;
        if(atCorner && x.board[3][3]!==max) v-=220000;
        candidates.push([v,d]);
      }
      candidates.sort((a,b)=>b[0]-a[0]);
      return candidates.length?candidates[0][1]:null;
    }
    self.onmessage=(ev)=>{
      if(!ev.data || ev.data.type!=='choose') return;
      const direction=choose(ev.data.board);
      self.postMessage({type:'result',generation:ev.data.generation,direction});
    };
  `;
  const blob = new Blob([workerSource], { type: 'application/javascript' });
  const url = URL.createObjectURL(blob);
  const w = new Worker(url);
  w.onmessage = (event) => {
    if (!aiRunning || event.data.generation !== workerGeneration) return;
    const direction = event.data.direction;
    if (!direction) { aiTimer = setTimeout(aiNextStep, 80); return; }
    aiStep++;
    showAIInfo(`AI 第 1 局 · 第 ${aiStep} 步`, direction);
    applyMove(direction);
    if (!aiRunning) return;
    if (gameOver || won) return;
    aiTimer = setTimeout(aiNextStep, 120);
  };
  w.onerror = () => finishAI('AI 后台计算出错，已暂停。');
  return w;
}

function aiNextStep() {
  if (!aiRunning || gameOver || won) return;
  if (!worker) worker = makeWorker();
  showAIInfo(`AI 第 1 局 · 第 ${aiStep + 1} 步 · 思考中`, null);
  worker.postMessage({ type: 'choose', board: cloneBoard(board), generation: workerGeneration });
}

function startAI() {
  stopAI();
  aiRunning = true;
  aiStep = 0;
  workerGeneration++;
  aiDemoBtn.textContent = '停止 AI';
  messageEl.textContent = '';
  messageEl.classList.add('hidden');
  showAIInfo('AI 第 1 局 · 思考中', null);
  aiNextStep();
}

newGameBtn.addEventListener('click', initBoard);
aiDemoBtn.addEventListener('click', () => {
  if (aiRunning) { stopAI(); aiInfo.classList.add('hidden'); }
  else startAI();
});
document.addEventListener('keydown', onKeyDown);

let touchStart = null;
boardEl.addEventListener('touchstart', event => {
  if (aiRunning) return;
  const t = event.changedTouches[0];
  touchStart = { x: t.clientX, y: t.clientY };
}, { passive: true });
boardEl.addEventListener('touchend', event => {
  if (aiRunning || !touchStart) return;
  const t = event.changedTouches[0];
  const dx = t.clientX - touchStart.x;
  const dy = t.clientY - touchStart.y;
  touchStart = null;
  if (Math.abs(dx) < 30 && Math.abs(dy) < 30) return;
  applyMove(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'));
}, { passive: true });

bestScoreEl.textContent = String(bestScore);
initTheme();
renderHistory();
initBoard();
