import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const BASE_DATA_URL = '/data/gobench_data/paper_results.json';
const SUPPLEMENT_DATA_URL = '/data/goplay_players.json';
const ENGINE_WORKER_URL = '/goplay/kata-worker.js';
const BOARD_SIZE = 9;
const KOMI = 7;
const NUM_VISITS = 1;
const GO_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'];
const DEFAULT_ELO = 1523;
const TEMPERATURE_SUFFIX = /-temp-(\d+(?:\.\d+)?)$/;
const HISTORY_STORAGE_KEY = 'goplay.game-history.v1';
const RATING_PRIOR_MEAN = 1000;
const RATING_PRIOR_STANDARD_DEVIATION = 2000;
const ELO_LOGISTIC_SCALE = Math.log(10) / 400;
const CONFIDENCE_95_Z_SCORE = 1.96;
const KATAGO_RESIGN_VALUE = -0.95;
const KATAGO_RESIGN_TURNS = 3;

const emptyBoard = () => new Array(BOARD_SIZE * BOARD_SIZE).fill(0);
const boardSignature = board => board.join('');
const otherColor = color => (color === 1 ? 2 : 1);
const colorName = color => (color === 1 ? 'Black' : 'White');

const toCoordinate = location => {
  if (location < 0) {
    return 'Pass';
  }

  const x = location % BOARD_SIZE;
  const y = Math.floor(location / BOARD_SIZE);
  return GO_COLUMNS[x] + String(BOARD_SIZE - y);
};

const getNeighbors = location => {
  const x = location % BOARD_SIZE;
  const y = Math.floor(location / BOARD_SIZE);
  const neighbors = [];

  if (x > 0) neighbors.push(location - 1);
  if (x < BOARD_SIZE - 1) neighbors.push(location + 1);
  if (y > 0) neighbors.push(location - BOARD_SIZE);
  if (y < BOARD_SIZE - 1) neighbors.push(location + BOARD_SIZE);

  return neighbors;
};

const getGroup = (board, start) => {
  const color = board[start];
  const stones = [];
  const liberties = new Set();
  const seen = new Set([start]);
  const queue = [start];

  while (queue.length) {
    const location = queue.pop();
    stones.push(location);

    getNeighbors(location).forEach(neighbor => {
      if (board[neighbor] === 0) {
        liberties.add(neighbor);
      } else if (board[neighbor] === color && !seen.has(neighbor)) {
        seen.add(neighbor);
        queue.push(neighbor);
      }
    });
  }

  return { stones, liberties };
};

const playOnBoard = (board, location, color, positionHistory) => {
  if (location < 0) {
    return {
      board: board.slice(),
      captures: 0,
      signature: boardSignature(board),
    };
  }

  if (board[location] !== 0) {
    return null;
  }

  const nextBoard = board.slice();
  nextBoard[location] = color;
  let captures = 0;

  getNeighbors(location).forEach(neighbor => {
    if (nextBoard[neighbor] !== otherColor(color)) {
      return;
    }

    const group = getGroup(nextBoard, neighbor);
    if (group.liberties.size === 0) {
      group.stones.forEach(stone => {
        nextBoard[stone] = 0;
        captures += 1;
      });
    }
  });

  if (getGroup(nextBoard, location).liberties.size === 0) {
    return null;
  }

  const signature = boardSignature(nextBoard);
  if (positionHistory.has(signature)) {
    return null;
  }

  return { board: nextBoard, captures, signature };
};

const scoreBoard = board => {
  let black = 0;
  let white = KOMI;
  const visited = new Set();

  board.forEach((stone, location) => {
    if (stone === 1) black += 1;
    if (stone === 2) white += 1;
    if (stone !== 0 || visited.has(location)) return;

    const region = [];
    const borders = new Set();
    const queue = [location];
    visited.add(location);

    while (queue.length) {
      const point = queue.pop();
      region.push(point);

      getNeighbors(point).forEach(neighbor => {
        if (board[neighbor] === 0 && !visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        } else if (board[neighbor] !== 0) {
          borders.add(board[neighbor]);
        }
      });
    }

    if (borders.size === 1) {
      if (borders.has(1)) black += region.length;
      if (borders.has(2)) white += region.length;
    }
  });

  return { black, white };
};

const scoreGame = board => {
  const score = scoreBoard(board);
  const difference = Math.abs(score.black - score.white);

  if (difference === 0) {
    return {
      blackScore: score.black,
      whiteScore: score.white,
      label: `Draw · ${score.black}–${score.white}`,
      margin: 0,
      reason: 'score',
      winnerColor: null,
    };
  }

  const winnerColor = score.black > score.white ? 1 : 2;
  return {
    blackScore: score.black,
    whiteScore: score.white,
    label: `${colorName(winnerColor)} wins by ${difference} · ${score.black}–${score.white}`,
    margin: difference,
    reason: 'score',
    winnerColor,
  };
};

const formatElo = value =>
  new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);

const formatHistoryDate = value => new Intl.DateTimeFormat('en-US', {
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  month: 'short',
  year: 'numeric',
}).format(new Date(value));

const createGameId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const gameScoreForRating = game => {
  if (game?.result?.outcome === 'win') return 1;
  if (game?.result?.outcome === 'loss') return 0;
  if (game?.result?.outcome === 'draw') return 0.5;
  return null;
};

const bradleyTerryWinProbability = (rating, opponentElo) => {
  const exponent = ELO_LOGISTIC_SCALE * (rating - opponentElo);
  const exponential = Math.exp(exponent >= 0 ? -exponent : exponent);
  return exponent >= 0
    ? 1 / (1 + exponential)
    : exponential / (1 + exponential);
};

const estimatePlayerElo = games => {
  const ratedGames = games.filter(game => (
    Number.isFinite(game?.opponent?.elo) && gameScoreForRating(game) !== null
  ));
  const priorVariance = RATING_PRIOR_STANDARD_DEVIATION ** 2;
  const ratingGradient = rating => {
    let gradient = -(rating - RATING_PRIOR_MEAN) / priorVariance;
    ratedGames.forEach(game => {
      const winProbability = bradleyTerryWinProbability(rating, game.opponent.elo);
      gradient += ELO_LOGISTIC_SCALE * (gameScoreForRating(game) - winProbability);
    });
    return gradient;
  };

  let lower = RATING_PRIOR_MEAN - 4000;
  let upper = RATING_PRIOR_MEAN + 4000;
  while (ratingGradient(lower) < 0) lower -= 4000;
  while (ratingGradient(upper) > 0) upper += 4000;

  for (let iteration = 0; iteration < 80; iteration += 1) {
    const midpoint = (lower + upper) / 2;
    if (ratingGradient(midpoint) > 0) {
      lower = midpoint;
    } else {
      upper = midpoint;
    }
  }
  const rating = (lower + upper) / 2;

  let precision = 1 / priorVariance;
  ratedGames.forEach(game => {
    const winProbability = bradleyTerryWinProbability(rating, game.opponent.elo);
    precision += (ELO_LOGISTIC_SCALE ** 2) * winProbability * (1 - winProbability);
  });

  return {
    games: ratedGames.length,
    rating,
    standardDeviation: Math.sqrt(1 / precision),
  };
};

const basePlayerName = player => player.replace(TEMPERATURE_SUFFIX, '');

const temperatureTarget = player => {
  const match = player.match(TEMPERATURE_SUFFIX);
  return match ? Number(match[1]) : 0.1;
};

const thinOpponents = players => {
  const sorted = players.slice().sort((left, right) => left.elo - right.elo);
  const thinned = [];

  sorted.forEach(player => {
    const previous = thinned[thinned.length - 1];
    if (!previous || player.elo - previous.elo >= 50) thinned.push(player);
  });

  const strongest = sorted[sorted.length - 1];
  if (strongest && !thinned.some(player => player.player === strongest.player)) {
    thinned.push(strongest);
  }

  return thinned.sort((left, right) => left.elo - right.elo);
};

const getLegalMoves = (board, color, positionHistory) => {
  const legalMoves = [-1];
  board.forEach((_, location) => {
    if (playOnBoard(board, location, color, positionHistory)) legalMoves.push(location);
  });
  return legalMoves;
};

const replayMoves = moves => {
  let board = emptyBoard();
  const positionHistory = new Set([boardSignature(board)]);
  let consecutivePasses = 0;

  moves.forEach(move => {
    const played = playOnBoard(board, move.loc, move.col, positionHistory);
    if (!played) throw new Error('Unable to restore the previous position');

    board = played.board;
    consecutivePasses = move.loc < 0 ? consecutivePasses + 1 : 0;
    if (move.loc >= 0) positionHistory.add(played.signature);
  });

  return {
    board,
    consecutivePasses,
    lastMove: moves.length ? moves[moves.length - 1].loc : null,
    positionHistory,
    toPlay: moves.length ? otherColor(moves[moves.length - 1].col) : 1,
  };
};

const createEngine = (worker, onProgress) => {
  const pending = new Map();
  let requestId = 0;

  worker.onmessage = event => {
    if (event.data.type === 'progress') {
      onProgress(event.data);
      return;
    }

    const request = pending.get(event.data.id);
    if (!request) return;

    pending.delete(event.data.id);
    if (event.data.ok) {
      request.resolve(event.data);
    } else {
      request.reject(new Error(event.data.error || 'KataGo worker error'));
    }
  };

  const call = payload =>
    new Promise((resolve, reject) => {
      const id = ++requestId;
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, ...payload });
    });

  const destroy = () => {
    pending.forEach(request => request.reject(new Error('KataGo model unloaded')));
    pending.clear();
    worker.terminate();
  };

  return { call, destroy };
};

const GoBoard = ({ board, disabled, lastMove, onPlay }) => {
  const viewSize = 500;
  const margin = 50;
  const spacing = (viewSize - margin * 2) / (BOARD_SIZE - 1);
  const points = Array.from({ length: BOARD_SIZE }, (_, index) => index);
  const starPoints = [
    [2, 2], [6, 2], [4, 4], [2, 6], [6, 6],
  ];

  return (
    <svg
      className="goplay-board"
      viewBox={`0 0 ${viewSize} ${viewSize}`}
      role="grid"
      aria-label="Interactive 9 by 9 Go board"
    >
      <defs>
        <radialGradient id="goplay-white-stone" cx="34%" cy="27%" r="72%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="70%" stopColor="#f2f0eb" />
          <stop offset="100%" stopColor="#c9c5bd" />
        </radialGradient>
        <radialGradient id="goplay-black-stone" cx="34%" cy="27%" r="72%">
          <stop offset="0%" stopColor="#5b5b58" />
          <stop offset="52%" stopColor="#242422" />
          <stop offset="100%" stopColor="#050505" />
        </radialGradient>
      </defs>

      <rect className="goplay-board-background" width={viewSize} height={viewSize} rx="7" />

      {points.map(index => {
        const offset = margin + index * spacing;
        return (
          <g key={`line-${index}`}>
            <line className="goplay-board-line" x1={margin} x2={viewSize - margin} y1={offset} y2={offset} />
            <line className="goplay-board-line" x1={offset} x2={offset} y1={margin} y2={viewSize - margin} />
            <text className="goplay-board-coordinate" x={offset} y={viewSize - 12} textAnchor="middle">
              {GO_COLUMNS[index]}
            </text>
            <text className="goplay-board-coordinate" x="20" y={offset + 5} textAnchor="middle">
              {BOARD_SIZE - index}
            </text>
          </g>
        );
      })}

      {starPoints.map(([x, y]) => (
        <circle
          key={`star-${x}-${y}`}
          className="goplay-board-star"
          cx={margin + x * spacing}
          cy={margin + y * spacing}
          r="4.5"
        />
      ))}

      {board.map((stone, location) => {
        if (!stone) return null;
        const x = location % BOARD_SIZE;
        const y = Math.floor(location / BOARD_SIZE);
        const cx = margin + x * spacing;
        const cy = margin + y * spacing;

        return (
          <g key={`stone-${location}`}>
            <circle
              className="goplay-stone"
              cx={cx}
              cy={cy}
              r={spacing * 0.45}
              fill={stone === 1 ? 'url(#goplay-black-stone)' : 'url(#goplay-white-stone)'}
            />
            {lastMove === location ? (
              <circle
                className={stone === 1 ? 'goplay-last-move is-black' : 'goplay-last-move is-white'}
                cx={cx}
                cy={cy}
                r={spacing * 0.12}
              />
            ) : null}
          </g>
        );
      })}

      {board.map((stone, location) => {
        if (stone) return null;
        const x = location % BOARD_SIZE;
        const y = Math.floor(location / BOARD_SIZE);
        const cx = margin + x * spacing;
        const cy = margin + y * spacing;
        const label = `Play ${toCoordinate(location)}`;

        return (
          <circle
            key={`hit-${location}`}
            className="goplay-board-hit"
            cx={cx}
            cy={cy}
            r={spacing * 0.42}
            role="gridcell"
            aria-label={label}
            aria-disabled={disabled}
            tabIndex={disabled ? -1 : 0}
            onClick={() => {
              if (!disabled) onPlay(location);
            }}
            onKeyDown={event => {
              if (!disabled && (event.key === 'Enter' || event.key === ' ')) {
                event.preventDefault();
                onPlay(location);
              }
            }}
          />
        );
      })}
    </svg>
  );
};

const GoPlay = () => {
  const [opponents, setOpponents] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [dataError, setDataError] = useState('');
  const [engineState, setEngineState] = useState({ status: 'idle', progress: 0, error: '' });
  const [humanColor, setHumanColor] = useState(1);
  const [board, setBoard] = useState(() => emptyBoard());
  const [moves, setMoves] = useState([]);
  const [toPlay, setToPlay] = useState(1);
  const [positionHistory, setPositionHistory] = useState(
    () => new Set([boardSignature(emptyBoard())]),
  );
  const [consecutivePasses, setConsecutivePasses] = useState(0);
  const [lastMove, setLastMove] = useState(null);
  const [gameState, setGameState] = useState('playing');
  const [result, setResult] = useState('');
  const [thinking, setThinking] = useState(false);
  const [moveError, setMoveError] = useState('');
  const [gameHistory, setGameHistory] = useState([]);
  const [historyReady, setHistoryReady] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const engineRef = useRef(null);
  const thinkingRef = useRef(false);
  const gameTokenRef = useRef(0);
  const completedGameIdRef = useRef(null);
  const katagoLosingTurnsRef = useRef(0);
  const selectedModel = basePlayerName(selectedPlayer);
  const selectedTemperatureTarget = temperatureTarget(selectedPlayer);

  const ratingEstimate = useMemo(() => estimatePlayerElo(gameHistory), [gameHistory]);
  const ratingConfidenceInterval = CONFIDENCE_95_Z_SCORE * ratingEstimate.standardDeviation;

  const lastHumanMoveIndex = useMemo(() => {
    for (let index = moves.length - 1; index >= 0; index -= 1) {
      if (moves[index].col === humanColor) return index;
    }
    return -1;
  }, [humanColor, moves]);

  const resetGame = useCallback(() => {
    gameTokenRef.current += 1;
    completedGameIdRef.current = null;
    katagoLosingTurnsRef.current = 0;
    thinkingRef.current = false;
    setThinking(false);
    setBoard(emptyBoard());
    setMoves([]);
    setToPlay(1);
    setPositionHistory(new Set([boardSignature(emptyBoard())]));
    setConsecutivePasses(0);
    setLastMove(null);
    setGameState('playing');
    setResult('');
    setMoveError('');
  }, []);

  useEffect(() => {
    try {
      const savedHistory = window.localStorage.getItem(HISTORY_STORAGE_KEY);
      if (savedHistory) {
        const parsedHistory = JSON.parse(savedHistory);
        if (!Array.isArray(parsedHistory)) throw new Error('saved data is not a game list');
        setGameHistory(currentHistory => {
          const currentIds = new Set(currentHistory.map(game => game.id));
          return [
            ...currentHistory,
            ...parsedHistory.filter(game => (
              game && typeof game.id === 'string' && !currentIds.has(game.id)
            )),
          ];
        });
      }
    } catch (error) {
      setHistoryError(`Saved game history could not be read: ${error.message}`);
    } finally {
      setHistoryReady(true);
    }
  }, []);

  useEffect(() => {
    if (!historyReady) return;
    try {
      window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(gameHistory));
      setHistoryError('');
    } catch (error) {
      setHistoryError(`Game history could not be saved: ${error.message}`);
    }
  }, [gameHistory, historyReady]);

  const recordCompletedGame = useCallback((details, completedMoves) => {
    const opponent = opponents.find(player => player.player === selectedPlayer);
    if (!opponent) return;

    const id = createGameId();
    const outcome = details.winnerColor === null
      ? 'draw'
      : details.winnerColor === humanColor ? 'win' : 'loss';
    const completedAt = new Date().toISOString();
    const game = {
      id,
      completedAt,
      boardSize: BOARD_SIZE,
      rules: 'Tromp–Taylor area scoring',
      komi: KOMI,
      humanColor: colorName(humanColor).toLowerCase(),
      opponent: {
        player: opponent.player,
        elo: opponent.elo,
        temperatureTarget: selectedTemperatureTarget,
      },
      result: {
        outcome,
        winner: details.winnerColor === null
          ? null
          : colorName(details.winnerColor).toLowerCase(),
        reason: details.reason,
        label: details.label,
        margin: details.margin ?? null,
        blackScore: details.blackScore ?? null,
        whiteScore: details.whiteScore ?? null,
        resignedBy: details.resignedBy ?? null,
      },
      moves: completedMoves.map((move, index) => ({
        number: index + 1,
        color: colorName(move.col).toLowerCase(),
        location: move.loc,
        coordinate: toCoordinate(move.loc),
      })),
    };

    completedGameIdRef.current = id;
    setGameHistory(currentHistory => [game, ...currentHistory]);
  }, [humanColor, opponents, selectedPlayer, selectedTemperatureTarget]);

  const undoLastTurn = useCallback(() => {
    gameTokenRef.current += 1;
    thinkingRef.current = false;
    katagoLosingTurnsRef.current = 0;
    setThinking(false);
    setMoveError('');

    if (gameState === 'finished' && completedGameIdRef.current) {
      const completedGameId = completedGameIdRef.current;
      completedGameIdRef.current = null;
      setGameHistory(currentHistory => (
        currentHistory.filter(game => game.id !== completedGameId)
      ));
    }

    if (gameState === 'finished' && result.includes('resignation')) {
      setGameState('playing');
      setResult('');
      return;
    }

    if (lastHumanMoveIndex < 0) return;

    try {
      const retainedMoves = moves.slice(0, lastHumanMoveIndex);
      const restored = replayMoves(retainedMoves);
      setBoard(restored.board);
      setMoves(retainedMoves);
      setToPlay(restored.toPlay);
      setPositionHistory(restored.positionHistory);
      setConsecutivePasses(restored.consecutivePasses);
      setLastMove(restored.lastMove);
      setGameState('playing');
      setResult('');
    } catch (error) {
      setMoveError(error.message);
    }
  }, [gameState, lastHumanMoveIndex, moves, result]);

  useEffect(() => {
    const controller = new AbortController();
    const fetchRatings = url => fetch(url, { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error(`ratings request failed (${response.status})`);
      return response.json();
    });

    Promise.all([
      fetchRatings(BASE_DATA_URL),
      fetchRatings(SUPPLEMENT_DATA_URL),
    ])
      .then(([baseData, supplementData]) => {
        const mergedPlayers = new Map();
        baseData.datasets.katago_players
          .filter(player => /^kata1-b6c96-/.test(player.player))
          .forEach(player => mergedPlayers.set(player.player, player));
        supplementData.players
          .filter(player => /^kata1-b6c96-/.test(player.player))
          .forEach(player => mergedPlayers.set(player.player, player));

        const b6c96Players = thinOpponents(
          Array.from(mergedPlayers.values()),
        );

        setOpponents(b6c96Players);
        const defaultOpponent = b6c96Players.reduce((closest, player) => (
          !closest || Math.abs(player.elo - DEFAULT_ELO) < Math.abs(closest.elo - DEFAULT_ELO)
            ? player
            : closest
        ), null);
        setSelectedPlayer(defaultOpponent?.player || '');
      })
      .catch(error => {
        if (error.name !== 'AbortError') {
          setDataError(`Unable to load KataGo ratings: ${error.message}`);
        }
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedModel) return undefined;

    let active = true;
    const worker = new Worker(ENGINE_WORKER_URL);
    const engine = createEngine(worker, progress => {
      if (!active) return;
      const ratio = progress.total > 0 ? progress.loaded / progress.total : 0;
      setEngineState({ status: 'loading', progress: ratio, error: '' });
    });

    engineRef.current = engine;
    setEngineState({ status: 'loading', progress: 0, error: '' });

    engine.call({
      type: 'init',
      modelUrl: `/goplay/networks/${selectedModel}.txt.gz`,
      boardSize: BOARD_SIZE,
    }).then(() => {
      if (active) {
        setEngineState({ status: 'ready', progress: 1, error: '' });
      }
    }).catch(error => {
      if (active) {
        setEngineState({ status: 'error', progress: 0, error: error.message });
      }
    });

    return () => {
      active = false;
      if (engineRef.current === engine) engineRef.current = null;
      engine.destroy();
    };
  }, [selectedModel]);

  const commitMove = useCallback((location, color) => {
    const played = playOnBoard(board, location, color, positionHistory);
    if (!played) {
      setMoveError('That move is illegal (occupied, suicide, ko, or superko).');
      return false;
    }

    const nextMoves = [...moves, { loc: location, col: color }];
    const nextPasses = location < 0 ? consecutivePasses + 1 : 0;
    const nextHistory = new Set(positionHistory);
    if (location >= 0) nextHistory.add(played.signature);

    setBoard(played.board);
    setMoves(nextMoves);
    setPositionHistory(nextHistory);
    setConsecutivePasses(nextPasses);
    setLastMove(location);
    setMoveError('');

    if (nextPasses >= 2) {
      const details = scoreGame(played.board);
      setGameState('finished');
      setResult(details.label);
      recordCompletedGame(details, nextMoves);
    } else {
      setToPlay(otherColor(color));
    }

    return true;
  }, [board, consecutivePasses, moves, positionHistory, recordCompletedGame]);

  useEffect(() => {
    if (
      engineState.status !== 'ready' ||
      gameState !== 'playing' ||
      toPlay === humanColor ||
      thinkingRef.current
    ) {
      return undefined;
    }

    const engine = engineRef.current;
    if (!engine) return undefined;

    const gameToken = gameTokenRef.current;
    thinkingRef.current = true;
    setThinking(true);

    engine.call({
      type: 'genmove',
      moves,
      toPlay,
      komi: KOMI,
      numVisits: NUM_VISITS,
      legalMoves: getLegalMoves(board, toPlay, positionHistory),
      temperatureTarget: selectedTemperatureTarget,
    }).then(response => {
      if (gameTokenRef.current !== gameToken) return;

      if (Number.isFinite(response.value) && response.value < KATAGO_RESIGN_VALUE) {
        katagoLosingTurnsRef.current += 1;
      } else {
        katagoLosingTurnsRef.current = 0;
      }

      if (katagoLosingTurnsRef.current >= KATAGO_RESIGN_TURNS) {
        const details = {
          winnerColor: humanColor,
          reason: 'resignation',
          resignedBy: 'katago',
          label: `${colorName(humanColor)} wins · KataGo resigns`,
        };
        setGameState('finished');
        setResult(details.label);
        recordCompletedGame(details, moves);
        return;
      }

      commitMove(response.move, toPlay);
    }).catch(error => {
      if (gameTokenRef.current === gameToken) {
        setMoveError(`KataGo could not move: ${error.message}`);
      }
    }).finally(() => {
      if (gameTokenRef.current === gameToken) {
        thinkingRef.current = false;
        setThinking(false);
      }
    });

    return undefined;
  }, [
    board,
    commitMove,
    engineState.status,
    gameState,
    humanColor,
    moves,
    positionHistory,
    recordCompletedGame,
    selectedTemperatureTarget,
    toPlay,
  ]);

  const isHumanTurn = gameState === 'playing' && toPlay === humanColor;
  const boardDisabled = engineState.status !== 'ready' || thinking || !isHumanTurn;

  const downloadGameHistory = useCallback(() => {
    const exportData = {
      schemaVersion: 1,
      exportedAt: new Date().toISOString(),
      game: 'GoPlay',
      ratingModel: {
        model: 'Bradley–Terry',
        eloScale: 400,
        prior: {
          distribution: 'normal',
          mean: RATING_PRIOR_MEAN,
          standardDeviation: RATING_PRIOR_STANDARD_DEVIATION,
        },
        estimate: {
          method: 'maximum a posteriori',
          elo: ratingEstimate.rating,
          approximatePosteriorStandardDeviation: ratingEstimate.standardDeviation,
          approximate95PercentConfidenceInterval: {
            plusOrMinus: ratingConfidenceInterval,
            lower: ratingEstimate.rating - ratingConfidenceInterval,
            upper: ratingEstimate.rating + ratingConfidenceInterval,
          },
          games: ratingEstimate.games,
        },
      },
      games: gameHistory,
    };
    const blob = new Blob([`${JSON.stringify(exportData, null, 2)}\n`], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `goplay-games-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }, [gameHistory, ratingConfidenceInterval, ratingEstimate]);

  const deleteHistoryGame = useCallback(gameId => {
    if (completedGameIdRef.current === gameId) {
      completedGameIdRef.current = null;
    }
    setGameHistory(currentHistory => (
      currentHistory.filter(game => game.id !== gameId)
    ));
  }, []);

  const statusText = (() => {
    if (engineState.status === 'loading') {
      const percentage = Math.round(engineState.progress * 100);
      return `Loading selected model${percentage ? ` · ${percentage}%` : '…'}`;
    }
    if (engineState.status === 'error') return 'Engine failed to load';
    if (gameState !== 'playing') return result;
    if (thinking) return 'KataGo is choosing a move…';
    return 'Waiting for KataGo…';
  })();
  const showStatus = (
    engineState.status !== 'ready' ||
    gameState !== 'playing' ||
    thinking ||
    !isHumanTurn
  );

  if (dataError) {
    return <div className="goplay-error" role="alert">{dataError}</div>;
  }

  if (!opponents.length) {
    return (
      <div className="goplay-loading" role="status">
        <span />
        <p>Loading GoPlay…</p>
      </div>
    );
  }

  return (
    <section className="goplay-root" aria-label="Play 9 by 9 Go against KataGo">
      <div className="goplay-game">
        <div className="goplay-settings">
          <div className="goplay-field">
            <label htmlFor="goplay-opponent">KataGo opponent</label>
            <select
              id="goplay-opponent"
              value={selectedPlayer}
              disabled={thinking}
              onChange={event => {
                const nextPlayer = event.target.value;
                if (basePlayerName(nextPlayer) !== selectedModel) {
                  setEngineState({ status: 'loading', progress: 0, error: '' });
                }
                resetGame();
                setSelectedPlayer(nextPlayer);
              }}
            >
              {opponents.map(opponent => (
                <option key={opponent.player} value={opponent.player}>
                  {formatElo(opponent.elo)} Elo
                </option>
              ))}
            </select>
          </div>

          <div className="goplay-field">
            <span className="goplay-field-label">Play as</span>
            <div className="goplay-color-picker" role="group" aria-label="Choose your stone color">
              {[1, 2].map(color => (
                <button
                  key={color}
                  type="button"
                  className={humanColor === color ? 'is-active' : ''}
                  disabled={thinking}
                  onClick={() => {
                    setHumanColor(color);
                    resetGame();
                  }}
                >
                  <span className={color === 1 ? 'goplay-color-dot is-black' : 'goplay-color-dot is-white'} />
                  {colorName(color)}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="goplay-board-shell">
          <GoBoard
            board={board}
            disabled={boardDisabled}
            lastMove={lastMove}
            onPlay={location => commitMove(location, humanColor)}
          />
        </div>

        <div className="goplay-controls">
          {showStatus ? (
            <div className={gameState === 'playing' ? 'goplay-status' : 'goplay-status is-finished'} aria-live="polite">
              <span>{statusText}</span>
              {engineState.status === 'loading' ? (
                <span className="goplay-progress" aria-hidden="true">
                  <span style={{ width: `${Math.max(4, engineState.progress * 100)}%` }} />
                </span>
              ) : null}
            </div>
          ) : null}

          {engineState.error ? <p className="goplay-inline-error">{engineState.error}</p> : null}
          {moveError ? <p className="goplay-inline-error">{moveError}</p> : null}

          <div className="goplay-actions">
            <button
              type="button"
              disabled={
                engineState.status !== 'ready' ||
                (lastHumanMoveIndex < 0 && !result.includes('resignation'))
              }
              onClick={undoLastTurn}
            >
              Undo
            </button>
            <button
              type="button"
              disabled={!isHumanTurn || thinking || engineState.status !== 'ready'}
              onClick={() => commitMove(-1, humanColor)}
            >
              Pass
            </button>
            <button
              type="button"
              disabled={!isHumanTurn || thinking || gameState !== 'playing'}
              onClick={() => {
                const winnerColor = otherColor(humanColor);
                const details = {
                  winnerColor,
                  reason: 'resignation',
                  resignedBy: 'human',
                  label: `${colorName(winnerColor)} wins by resignation`,
                };
                gameTokenRef.current += 1;
                setGameState('finished');
                setResult(details.label);
                recordCompletedGame(details, moves);
              }}
            >
              Resign
            </button>
            <button type="button" className="is-primary" disabled={thinking} onClick={resetGame}>
              New game
            </button>
          </div>

          <div className="goplay-moves" aria-label="Recent moves">
            <span>Recent moves</span>
            <div>
              {moves.length ? moves.slice(-8).map((move, index) => (
                <span key={`${moves.length - 8 + index}-${move.loc}`}>
                  {moves.length - Math.min(8, moves.length) + index + 1}. {move.col === 1 ? 'B' : 'W'} {toCoordinate(move.loc)}
                </span>
              )) : <em>No moves yet</em>}
            </div>
          </div>
        </div>
      </div>

      <section className="goplay-history" aria-labelledby="goplay-history-heading">
        <header className="goplay-history-header">
          <div>
            <h3 id="goplay-history-heading">Past games</h3>
            <p>Saved in this browser.</p>
          </div>
          <div className="goplay-history-actions">
            <button
              type="button"
              disabled={!gameHistory.length}
              onClick={downloadGameHistory}
            >
              Download JSON
            </button>
            <button
              type="button"
              className="is-danger"
              disabled={!gameHistory.length}
              onClick={() => {
                if (!window.confirm('Clear all saved GoPlay games from this browser?')) return;
                completedGameIdRef.current = null;
                setGameHistory([]);
              }}
            >
              Clear games
            </button>
          </div>
        </header>

        <div className="goplay-history-summary">
          <div className="goplay-estimated-elo">
            <span>Your estimated Elo</span>
            <strong aria-label={`${formatElo(ratingEstimate.rating)} plus or minus ${formatElo(ratingConfidenceInterval)} Elo at 95 percent confidence`}>
              {formatElo(ratingEstimate.rating)}
              <span>± {formatElo(ratingConfidenceInterval)}</span>
            </strong>
          </div>
        </div>

        {historyError ? <p className="goplay-inline-error">{historyError}</p> : null}

        {gameHistory.length ? (
          <div className="goplay-history-table-wrap">
            <table className="goplay-history-table">
              <thead>
                <tr>
                  <th scope="col">Completed</th>
                  <th scope="col">Opponent</th>
                  <th scope="col">You</th>
                  <th scope="col">Result</th>
                  <th scope="col" className="goplay-history-action-cell">Actions</th>
                </tr>
              </thead>
              <tbody>
                {gameHistory.map(game => (
                  <tr key={game.id}>
                    <td title={game.completedAt}>{formatHistoryDate(game.completedAt)}</td>
                    <td>{formatElo(game.opponent.elo)} Elo</td>
                    <td>{game.humanColor === 'black' ? 'Black' : 'White'}</td>
                    <td>
                      <span className="goplay-history-result">
                        <strong className={`is-${game.result.outcome}`}>
                          {game.result.outcome === 'win'
                            ? 'Win'
                            : game.result.outcome === 'loss' ? 'Loss' : 'Draw'}
                        </strong>
                        <span>{game.result.label}</span>
                      </span>
                    </td>
                    <td className="goplay-history-action-cell">
                      <button
                        type="button"
                        className="goplay-history-delete"
                        aria-label={`Delete game against ${formatElo(game.opponent.elo)} Elo from ${formatHistoryDate(game.completedAt)}`}
                        onClick={() => deleteHistoryGame(game.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="goplay-history-empty">Completed games will appear here.</p>
        )}
      </section>
    </section>
  );
};

export default GoPlay;
