// Exercise the actual GoPlay worker and WASM engine in Node, using the
// GitHub-hosted files' local equivalents so this also works before a push.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { Readable } = require('node:stream');
const { spawnSync } = require('node:child_process');
const catalog = require('../data/goplay_catalog.json');

const requested = process.argv[2];
if (!requested) {
  for (const name of Object.keys(catalog.networks)) {
    const result = spawnSync(process.execPath, [__filename, name], { stdio: 'inherit' });
    if (result.status !== 0) process.exit(result.status || 1);
  }
  console.log(`Passed: ${Object.keys(catalog.networks).length} networks loaded and played on CPU.`);
} else {
  checkNetwork(requested).catch(error => {
    console.error(error);
    process.exitCode = 1;
  });
}

async function checkNetwork(name) {
  const network = catalog.networks[name];
  assert.ok(network, `Unknown network: ${name}`);
  const root = path.resolve(__dirname, '..');
  const filename = path.join(root, 'networks/goplay', network.file);
  const bytes = fs.readFileSync(filename);
  assert.equal(bytes.byteLength, network.size_bytes);
  assert.equal(require('node:crypto').createHash('sha256').update(bytes).digest('hex'), network.sha256);

  let pending;
  let fetchCount = 0;
  let lastProgress = 0;
  const context = vm.createContext({
    createKata: options => require('../public/goplay/kataeval.js')({
      ...options,
      locateFile: file => path.join(root, 'public/goplay', file),
    }),
    importScripts() {},
    URL,
    Uint8Array,
    Uint32Array,
    crypto: require('node:crypto').webcrypto,
    close() {},
    fetch: async (url, options) => {
      assert.equal(new URL(url).hostname, 'raw.githubusercontent.com');
      assert.equal(path.basename(new URL(url).pathname), network.file);
      assert.equal(options.cache, 'no-store');
      assert.equal(options.credentials, 'omit');
      fetchCount += 1;
      return new Response(Readable.toWeb(fs.createReadStream(filename)));
    },
    postMessage(message) {
      if (message.type === 'progress') {
        assert.ok(message.loaded >= lastProgress);
        assert.equal(message.total, network.size_bytes);
        lastProgress = message.loaded;
        return;
      }
      if (message.ok) pending.resolve(message);
      else pending.reject(new Error(message.error));
    },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'public/goplay/kata-worker.js'), 'utf8'), context);
  const call = data => new Promise((resolve, reject) => {
    pending = { resolve, reject };
    context.onmessage({ data: { id: 1, ...data } });
  });
  const start = performance.now();
  const result = await call({
    type: 'init',
    modelUrl: `https://raw.githubusercontent.com/RolandGao/rolandgao.github.io/main/networks/goplay/${network.file}`,
    modelBytes: network.size_bytes,
    boardSize: 9,
  });
  assert.equal(result.backend, 'CPU (Eigen)');
  assert.equal(lastProgress, network.size_bytes);
  assert.equal(vm.runInContext('modelPath', context), '');

  const moves = [];
  for (const temperatureTarget of [0.1, 0.9]) {
    const legalMoves = Array.from({ length: 82 }, (_, i) => i - 1)
      .filter(loc => loc === -1 || !moves.some(move => move.loc === loc));
    const move = await call({
      type: 'genmove', moves, toPlay: moves.length % 2 + 1,
      komi: 7, numVisits: 1, legalMoves, temperatureTarget,
    });
    assert.ok(legalMoves.includes(move.move));
    assert.ok(Number.isFinite(move.value) && Math.abs(move.value) <= 1);
    assert.ok(move.winrate >= 0 && move.winrate <= 1);
    assert.equal(move.visits, 1);
    moves.push({ loc: move.move, col: moves.length % 2 + 1 });
  }
  assert.equal(fetchCount, 1, 'Moves and temperature changes must reuse the loaded weights');
  await call({ type: 'dispose' });
  console.log(`PASS ${name} (${((performance.now() - start) / 1000).toFixed(1)}s)`);
}
