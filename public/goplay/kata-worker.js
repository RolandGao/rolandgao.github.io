/* global createKata */
importScripts('/goplay/kataeval.js');

const MAX_MOVES = 512;
let moduleInstance = null;
let boardSize = 9;
let modelPath = '';
let moveLocationsPointer = 0;
let moveColorsPointer = 0;
let boardPointer = 0;
let policyPointer = 0;
let valuePointer = 0;

const moveTemperature = (moveCount, target) => {
  if (target > 0.5) return target;
  return target + (0.5 - target) * (2 ** (-moveCount / 9));
};

const randomUnit = () => {
  const sample = new Uint32Array(1);
  crypto.getRandomValues(sample);
  return sample[0] / 0x100000000;
};

const sampleMove = (legalMoves, temperature) => {
  const policyIndex = policyPointer >> 2;
  const boardArea = boardSize * boardSize;
  const candidates = legalMoves.map(move => {
    const policyLocation = move < 0 ? boardArea : move;
    return { move, logit: moduleInstance.HEAPF32[policyIndex + policyLocation] };
  }).filter(candidate => Number.isFinite(candidate.logit));

  if (!candidates.length) throw new Error('the engine returned no legal policy moves');

  const maxScaledLogit = Math.max(...candidates.map(candidate => candidate.logit / temperature));
  const weights = candidates.map(candidate => Math.exp(
    candidate.logit / temperature - maxScaledLogit,
  ));
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
  let draw = randomUnit() * totalWeight;

  for (let index = 0; index < candidates.length; index += 1) {
    draw -= weights[index];
    if (draw <= 0) return candidates[index].move;
  }

  return candidates[candidates.length - 1].move;
};

const readPlayerValue = () => {
  const valueIndex = valuePointer >> 2;
  const logits = [0, 1, 2].map(offset => moduleInstance.HEAPF32[valueIndex + offset]);
  const maxLogit = Math.max(...logits);
  const probabilities = logits.map(logit => Math.exp(logit - maxLogit));
  const total = probabilities.reduce((sum, probability) => sum + probability, 0);
  // The direct evaluator returns raw win/loss/no-result logits from the
  // perspective of the player to move. Unlike NNEvaluator, it has not yet
  // converted them to White's perspective.
  return (probabilities[0] - probabilities[1]) / total;
};

const postProgress = (loaded, total) => {
  postMessage({ type: 'progress', loaded, total });
};

const downloadModel = async (url, expectedBytes) => {
  const response = await fetch(url, { cache: 'no-store', credentials: 'omit' });
  if (!response.ok) {
    throw new Error(`model request failed (${response.status})`);
  }

  const total = expectedBytes;
  if (!Number.isSafeInteger(total) || total <= 0 || total > 100000000) {
    throw new Error('invalid network size in the opponent catalog');
  }
  if (!response.body) {
    const buffer = await response.arrayBuffer();
    if (buffer.byteLength !== total) throw new Error('incomplete network download');
    postProgress(buffer.byteLength, buffer.byteLength);
    return new Uint8Array(buffer);
  }

  const reader = response.body.getReader();
  // Allocate once: retaining chunks and combining them doubles the memory
  // needed for a large compressed network.
  const bytes = new Uint8Array(total);
  let loaded = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (loaded + value.byteLength > total) {
      await reader.cancel();
      throw new Error('network download exceeds its expected size');
    }
    bytes.set(value, loaded);
    loaded += value.byteLength;
    postProgress(loaded, total);
  }

  if (loaded !== total) throw new Error('incomplete network download');
  return bytes;
};

const initialize = async ({ modelUrl, modelBytes: expectedBytes, boardSize: requestedBoardSize }) => {
  boardSize = requestedBoardSize;
  moduleInstance = await createKata({
    locateFile: file => file.endsWith('.wasm')
      ? '/goplay/kataeval.wasm'
      : `/goplay/${file}`,
  });

  moduleInstance.ccall('kgeSetForceCpu', null, ['number'], [1]);
  const modelBytes = await downloadModel(modelUrl, expectedBytes);
  // KataGo selects the text/binary parser from the filename extension.
  const extension = new URL(modelUrl).pathname.endsWith('.bin.gz') ? 'bin.gz' : 'txt.gz';
  modelPath = `/selected-model.${extension}`;
  moduleInstance.FS.writeFile(modelPath, modelBytes, { canOwn: true });

  const loaded = await moduleInstance.ccall(
    'kgeLoad',
    'number',
    ['string', 'number'],
    [modelPath, boardSize],
    { async: true },
  );

  if (!loaded) {
    throw new Error(moduleInstance.ccall('kgeError', 'string', [], []));
  }
  if (moduleInstance.ccall('kgeBackendIsGpu', 'number', [], [])) {
    throw new Error('CPU-only mode could not be enabled');
  }
  // The evaluator now owns the parsed weights; release the compressed file.
  moduleInstance.FS.unlink(modelPath);
  modelPath = '';

  moveLocationsPointer = moduleInstance._malloc(MAX_MOVES * 4);
  moveColorsPointer = moduleInstance._malloc(MAX_MOVES * 4);
  boardPointer = moduleInstance._malloc(boardSize * boardSize * 4);
  policyPointer = moduleInstance._malloc((boardSize * boardSize + 1) * 4);
  valuePointer = moduleInstance._malloc(5 * 4);

  return {
    backend: 'CPU (Eigen)',
    modelVersion: moduleInstance.ccall('kgeModelVersion', 'number', [], []),
  };
};

const generateMove = async ({
  moves = [],
  toPlay,
  komi,
  numVisits,
  legalMoves = [],
  temperatureTarget = 0.1,
}) => {
  if (!moduleInstance) throw new Error('engine is not initialized');
  if (numVisits !== 1) throw new Error('GoPlay only permits numVisits = 1');
  if (moves.length > MAX_MOVES) throw new Error('game is too long for the engine buffer');
  if (!legalMoves.length) throw new Error('no legal moves were provided');
  if (!(temperatureTarget > 0 && temperatureTarget <= 1)) {
    throw new Error('temperature target must be between 0 and 1');
  }

  const locationsIndex = moveLocationsPointer >> 2;
  const colorsIndex = moveColorsPointer >> 2;
  moves.forEach((move, index) => {
    moduleInstance.HEAP32[locationsIndex + index] = move.loc;
    moduleInstance.HEAP32[colorsIndex + index] = move.col;
  });

  const ok = await moduleInstance.ccall(
    'kgeEvalSeq',
    'number',
    [
      'number', 'number', 'number', 'number', 'number', 'number', 'number',
      'number', 'number',
    ],
    [
      moveLocationsPointer,
      moveColorsPointer,
      moves.length,
      toPlay,
      komi,
      boardPointer,
      policyPointer,
      valuePointer,
      0,
    ],
    { async: true },
  );

  if (!ok) {
    throw new Error(moduleInstance.ccall('kgeError', 'string', [], []));
  }

  const temperature = moveTemperature(moves.length, temperatureTarget);
  const value = readPlayerValue();

  return {
    move: sampleMove(legalMoves, temperature),
    value,
    winrate: (value + 1) / 2,
    visits: 1,
    temperature,
  };
};

const dispose = () => {
  if (moduleInstance && modelPath) {
    try {
      moduleInstance.FS.unlink(modelPath);
    } catch (_) {
      // Terminating the worker releases the complete WASM heap either way.
    }
  }
  moduleInstance = null;
  modelPath = '';
};

onmessage = event => {
  const { id, type } = event.data;

  Promise.resolve()
    .then(async () => {
      if (type === 'init') return initialize(event.data);
      if (type === 'genmove') return generateMove(event.data);
      if (type === 'dispose') {
        dispose();
        close();
        return {};
      }
      throw new Error(`unknown worker request: ${type}`);
    })
    .then(result => postMessage({ id, ok: true, ...result }))
    .catch(error => postMessage({
      id,
      ok: false,
      error: String(error?.message || error),
    }));
};
