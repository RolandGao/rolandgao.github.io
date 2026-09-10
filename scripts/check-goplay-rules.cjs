const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

// Run the component's actual pure helpers, without mounting React or mocking
// the rules implementation. Keep the slice bounded by its existing declarations.
const source = fs.readFileSync(path.join(__dirname, '../components/GoPlay.js'), 'utf8');
const start = source.indexOf('const BOARD_SIZE =');
const end = source.indexOf('const createEngine =');
assert.ok(start >= 0 && end > start);
const rules = vm.runInNewContext(`${source.slice(start, end)}\n({
  emptyBoard, boardSignature, playOnBoard, getLegalMoves, getKataGoLegalMoves, replayMoves,
})`, { goplayPlayerData: require('../public/data/goplay_opponents.json') });
const { emptyBoard, boardSignature, playOnBoard, replayMoves } = rules;

for (const color of [1, 2]) {
  test(`self capture removes the entire connected group for color ${color}`, () => {
    const board = emptyBoard();
    board[0] = color;
    for (const point of [2, 9, 10]) board[point] = 3 - color;
    const original = Array.from(board);
    const history = new Set([boardSignature(board)]);
    const result = playOnBoard(board, 1, color, history);
    assert.ok(result);
    assert.equal(result.board[0], 0);
    assert.equal(result.board[1], 0);
    for (const point of [2, 9, 10]) assert.equal(result.board[point], 3 - color);
    assert.deepEqual(Array.from(board), original, 'the input board must not change');
    assert.equal(result.captures, 0, 'self capture must not count as capturing an opponent');
    assert.ok(rules.getLegalMoves(board, color, history).includes(1));
    assert.ok(rules.getKataGoLegalMoves(board, color, history).includes(1));
    history.add(result.signature);
    assert.equal(playOnBoard(board, 1, color, history), null, 'positional superko still applies');
  });
}

test('a single-stone self capture that leaves the board unchanged violates superko', () => {
  const board = emptyBoard();
  board[1] = board[9] = 2;
  const history = new Set([boardSignature(board)]);
  assert.equal(playOnBoard(board, 0, 1, history), null);
  assert.equal(playOnBoard(board, 1, 1, history), null, 'occupied points remain illegal');
  assert.ok(playOnBoard(board, -1, 1, history), 'a pass is exempt from superko');
});

test('opponent captures create liberties before considering self capture', () => {
  const board = emptyBoard();
  board[1] = board[9] = 2;
  board[2] = board[10] = board[18] = 1;
  const result = playOnBoard(board, 0, 1, new Set([boardSignature(board)]));
  assert.ok(result);
  assert.equal(result.board[0], 1);
  assert.equal(result.board[1], 0);
  assert.equal(result.board[9], 0);
  assert.equal(result.captures, 2);
});

const sequence = [0, 9, 80, 10, 79, 2, 1].map((loc, i) => ({ loc, col: i % 2 + 1 }));

test('replay and undo preserve self capture and its resulting position history', () => {
  const result = replayMoves(sequence);
  assert.equal(result.board[0], 0);
  assert.equal(result.board[1], 0);
  assert.equal(result.board[79], 1);
  assert.equal(result.board[80], 1);
  assert.equal(result.toPlay, 2);
  assert.equal(result.consecutivePasses, 0);
  assert.ok(result.positionHistory.has(boardSignature(result.board)));
  assert.equal(replayMoves(sequence.slice(0, -1)).board[0], 1);
});

test('the actual KataGo WASM engine reconstructs the same board after self capture', async () => {
  const assetFolder = path.join(__dirname, '../public/goplay');
  const engine = await require('../public/goplay/kataeval.js')({
    locateFile: file => path.join(assetFolder, file),
  });
  engine.ccall('kgeSetForceCpu', null, ['number'], [1]);
  const modelPath = '/rules-test.txt.gz';
  engine.FS.writeFile(modelPath, fs.readFileSync(path.join(
    __dirname, '../networks/goplay/kata1-b6c96-s938496-d1208807.txt.gz',
  )));
  assert.equal(await engine.ccall('kgeLoad', 'number', ['string', 'number'], [modelPath, 9], { async: true }), 1);
  const moveLocs = engine._malloc(8 * 4);
  const moveCols = engine._malloc(8 * 4);
  const boardOut = engine._malloc(81 * 4);
  const policyOut = engine._malloc(82 * 4);
  const valueOut = engine._malloc(5 * 4);
  for (const moves of [sequence, [...sequence, { loc: 0, col: 2 }]]) {
    moves.forEach((move, i) => {
      engine.HEAP32[(moveLocs >> 2) + i] = move.loc;
      engine.HEAP32[(moveCols >> 2) + i] = move.col;
    });
    const expected = replayMoves(moves);
    const ok = await engine.ccall('kgeEvalSeq', 'number', Array(9).fill('number'), [
      moveLocs, moveCols, moves.length, expected.toPlay, 7, boardOut, policyOut, valueOut, 0,
    ], { async: true });
    assert.equal(ok, 1, engine.ccall('kgeError', 'string', [], []));
    assert.deepEqual(Array.from(engine.HEAP32.slice(boardOut >> 2, (boardOut >> 2) + 81)), Array.from(expected.board));
  }
  for (const pointer of [moveLocs, moveCols, boardOut, policyOut, valueOut]) engine._free(pointer);
  engine.FS.unlink(modelPath);
});
