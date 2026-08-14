import { useEffect, useMemo, useState } from 'react';

const DATA_URL = '/data/gobench_data/paper_results.json';
const GO_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'];
const CHART_COLORS = [
  '#9b4f32',
  '#356fd4',
  '#6754d9',
  '#e59112',
  '#109b78',
  '#11a783',
  '#e34f88',
  '#167c68',
  '#272727',
  '#3678d8',
];

const TABLE_COLUMNS = [
  {
    key: 'rank',
    label: 'Rank',
    align: 'left',
    value: row => {
      const match = String(row.rank).match(/^\d+/);
      return match ? Number(match[0]) : Number.POSITIVE_INFINITY;
    },
    render: row => row.rank,
  },
  {
    key: 'player',
    label: 'Player',
    align: 'left',
    value: row => row.label.toLowerCase(),
    render: row => row.label,
  },
  {
    key: 'elo',
    label: 'Elo',
    value: row => row.elo,
    render: row => formatInteger(row.elo),
  },
  {
    key: 'elo_ci_95',
    label: '95% CI',
    value: row => row.elo_ci_95,
    render: row => '±' + formatInteger(row.elo_ci_95),
  },
  {
    key: 'games',
    label: 'Games',
    value: row => row.games,
    render: row => formatInteger(row.games),
  },
  {
    key: 'seconds',
    label: 'Seconds / move',
    value: row => row.seconds,
    render: row => formatTwoSignificantFigures(row.seconds) + 's',
  },
  {
    key: 'cost',
    label: 'Cost / move',
    value: row => row.cost,
    render: row => formatCost(row.cost),
  },
];

const formatInteger = value =>
  new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);

const superscript = value => {
  const characters = {
    '-': '⁻',
    '0': '⁰',
    '1': '¹',
    '2': '²',
    '3': '³',
    '4': '⁴',
    '5': '⁵',
    '6': '⁶',
    '7': '⁷',
    '8': '⁸',
    '9': '⁹',
  };

  return String(value)
    .split('')
    .map(character => characters[character] || character)
    .join('');
};

const formatTwoSignificantFigures = value => {
  if (!Number.isFinite(value) || value === 0) {
    return String(value || 0);
  }

  return Number(value.toPrecision(2)).toString();
};

const formatCost = value => {
  if (value > 0 && value < 0.0001) {
    const exponent = Math.floor(Math.log10(value));
    const mantissa = value / 10 ** exponent;
    return '$' + formatTwoSignificantFigures(mantissa) + ' × 10' + superscript(exponent);
  }

  return '$' + formatTwoSignificantFigures(value);
};

const getTableRows = data => {
  const llmRows = data.datasets.llm_players.map(player => ({
    ...player,
    label: player.player,
    seconds: player.api_seconds_per_move,
    cost: player.cost_usd_per_move,
    rowType: 'llm',
  }));
  const references = data.table_2.katago_reference_players.map(player => ({
    ...player,
    rank: '—',
    seconds: player.seconds_per_move,
    cost: player.cost_usd_per_move,
    rowType: 'reference',
  }));

  return [...llmRows, ...references];
};

const Leaderboard = ({ data }) => {
  const rows = useMemo(() => getTableRows(data), [data]);
  const [sort, setSort] = useState(null);

  const displayedRows = useMemo(() => {
    if (!sort) {
      return rows;
    }

    const column = TABLE_COLUMNS.find(candidate => candidate.key === sort.key);
    return rows
      .map((row, index) => ({ row, index }))
      .sort((left, right) => {
        const leftValue = column.value(left.row);
        const rightValue = column.value(right.row);
        let comparison = 0;

        if (typeof leftValue === 'string') {
          comparison = leftValue.localeCompare(rightValue);
        } else {
          comparison = leftValue - rightValue;
        }

        if (comparison === 0) {
          comparison = left.index - right.index;
        }

        return sort.direction === 'ascending' ? comparison : -comparison;
      })
      .map(item => item.row);
  }, [rows, sort]);

  const sortBy = key => {
    setSort(current => ({
      key,
      direction:
        current?.key === key && current.direction === 'ascending'
          ? 'descending'
          : 'ascending',
    }));
  };

  return (
    <section className="gobench-section" aria-labelledby="gobench-leaderboard-title">
      <div className="gobench-section-header">
        <div>
          <p className="gobench-eyebrow">Leaderboard</p>
          <h2 id="gobench-leaderboard-title">GoBench results</h2>
        </div>
        <p className="gobench-section-note">
          Click a column title to sort. Time and cost are rounded to two significant figures.
        </p>
      </div>

      <div className="gobench-table-scroll">
        <table className="gobench-table">
          <thead>
            <tr>
              {TABLE_COLUMNS.map(column => {
                const isActive = sort?.key === column.key;
                const ariaSort = isActive ? sort.direction : 'none';
                const indicator = !isActive
                  ? '↕'
                  : sort.direction === 'ascending'
                    ? '↑'
                    : '↓';

                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={ariaSort}
                    className={column.align === 'left' ? 'is-left' : undefined}
                  >
                    <button type="button" onClick={() => sortBy(column.key)}>
                      <span>{column.label}</span>
                      <span className={isActive ? 'sort-indicator is-active' : 'sort-indicator'}>
                        {indicator}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((row, index) => (
              <tr
                key={row.player}
                className={row.rowType === 'reference' ? 'gobench-reference-row' : undefined}
              >
                {TABLE_COLUMNS.map(column => (
                  <td
                    key={column.key}
                    className={
                      (column.align === 'left' ? 'is-left ' : '') +
                      (column.key === 'player' ? 'is-player' : '')
                    }
                  >
                    {column.render(row, index)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="gobench-caption">{data.table_2.caption}</p>
    </section>
  );
};

const logScale = (value, domainMin, domainMax, rangeMin, rangeMax) => {
  const minimum = Math.log10(domainMin);
  const maximum = Math.log10(domainMax);
  const ratio = (Math.log10(value) - minimum) / (maximum - minimum);
  return rangeMin + ratio * (rangeMax - rangeMin);
};

const linearScale = (value, domainMin, domainMax, rangeMin, rangeMax) => {
  const ratio = (value - domainMin) / (domainMax - domainMin);
  return rangeMin + ratio * (rangeMax - rangeMin);
};

const PointGlyph = ({ point, x, y, color, muted = false, onEnter, onLeave }) => {
  const label = point.player + ', ' + formatInteger(point.elo) + ' Elo';
  const radius = muted ? 4 : 6;

  return (
    <g
      className={muted ? 'gobench-chart-point is-muted' : 'gobench-chart-point'}
      role="img"
      aria-label={label}
      tabIndex={muted ? undefined : 0}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onFocus={onEnter}
      onBlur={onLeave}
    >
      <title>{label}</title>
      <circle className="gobench-point-hitbox" cx={x} cy={y} r="13" />
      <circle
        cx={x}
        cy={y}
        r={radius}
        fill={color}
        stroke={muted ? '#f6f5f2' : '#ffffff'}
        strokeWidth={muted ? 1 : 2}
      />
    </g>
  );
};

const ChartPanel = ({ title, points, llmNames, xDomain, xTicks, referenceElo }) => {
  const width = 560;
  const height = 390;
  const margin = { top: 45, right: 22, bottom: 60, left: 62 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const yTicks = [0, 1000, 2000, 3000, 4000];
  const [hovered, setHovered] = useState(null);

  const xPosition = value =>
    logScale(value, xDomain[0], xDomain[1], margin.left, margin.left + plotWidth);
  const yPosition = value =>
    linearScale(value, 0, 4600, margin.top + plotHeight, margin.top);

  const showPoint = point => {
    const x = xPosition(point.cost_usd_per_move);
    const y = yPosition(point.elo);
    const left = Math.min(82, Math.max(18, (x / width) * 100));
    setHovered({ point, left, top: (y / height) * 100 });
  };

  return (
    <div className="gobench-chart-panel">
      <div className="gobench-chart-title">{title}</div>
      <div className="gobench-chart-canvas">
        <svg
          viewBox={'0 0 ' + width + ' ' + height}
          role="img"
          aria-label={title + ': Elo by cost per move'}
        >
          {yTicks.map(tick => {
            const y = yPosition(tick);
            return (
              <g key={'y-' + tick}>
                <line
                  className="gobench-chart-gridline"
                  x1={margin.left}
                  x2={margin.left + plotWidth}
                  y1={y}
                  y2={y}
                />
                <text className="gobench-chart-tick" x={margin.left - 12} y={y + 4} textAnchor="end">
                  {formatInteger(tick)}
                </text>
              </g>
            );
          })}

          {xTicks.map(tick => {
            const x = xPosition(tick.value);
            return (
              <g key={'x-' + tick.value}>
                <line
                  className="gobench-chart-gridline"
                  x1={x}
                  x2={x}
                  y1={margin.top}
                  y2={margin.top + plotHeight}
                />
                <text
                  className="gobench-chart-tick"
                  x={x}
                  y={margin.top + plotHeight + 25}
                  textAnchor="middle"
                >
                  {tick.label}
                </text>
              </g>
            );
          })}

          <line
            className="gobench-chart-axis"
            x1={margin.left}
            x2={margin.left}
            y1={margin.top}
            y2={margin.top + plotHeight}
          />
          <line
            className="gobench-chart-axis"
            x1={margin.left}
            x2={margin.left + plotWidth}
            y1={margin.top + plotHeight}
            y2={margin.top + plotHeight}
          />

          {referenceElo ? (
            <g>
              <line
                className="gobench-reference-line"
                x1={margin.left}
                x2={margin.left + plotWidth}
                y1={yPosition(referenceElo)}
                y2={yPosition(referenceElo)}
              />
              <text
                className="gobench-reference-label"
                x={margin.left + 8}
                y={yPosition(referenceElo) - 8}
              >
                Strongest KataGo · {formatInteger(referenceElo)} Elo
              </text>
            </g>
          ) : null}

          {points.map(point => {
            const isLlm = llmNames.has(point.player);
            const llmIndex = isLlm ? Array.from(llmNames).indexOf(point.player) : -1;
            const x = xPosition(point.cost_usd_per_move);
            const y = yPosition(point.elo);
            const error = isLlm ? point.elo_ci_95 : null;
            const color = isLlm ? CHART_COLORS[llmIndex % CHART_COLORS.length] : '#9aa3ad';

            return (
              <g key={point.player}>
                {error ? (
                  <g className="gobench-error-bar" stroke={color}>
                    <line x1={x} x2={x} y1={yPosition(point.elo - error)} y2={yPosition(point.elo + error)} />
                    <line x1={x - 5} x2={x + 5} y1={yPosition(point.elo - error)} y2={yPosition(point.elo - error)} />
                    <line x1={x - 5} x2={x + 5} y1={yPosition(point.elo + error)} y2={yPosition(point.elo + error)} />
                  </g>
                ) : null}
                <PointGlyph
                  point={point}
                  x={x}
                  y={y}
                  color={color}
                  muted={!isLlm}
                  onEnter={() => showPoint(point)}
                  onLeave={() => setHovered(null)}
                />
              </g>
            );
          })}

          <text
            className="gobench-chart-axis-label"
            x={margin.left + plotWidth / 2}
            y={height - 10}
            textAnchor="middle"
          >
            Cost, USD / move (log scale)
          </text>
          <text
            className="gobench-chart-axis-label"
            transform={'translate(16 ' + (margin.top + plotHeight / 2) + ') rotate(-90)'}
            textAnchor="middle"
          >
            Elo
          </text>
        </svg>

        {hovered ? (
          <div
            className="gobench-chart-tooltip"
            style={{ left: String(hovered.left) + '%', top: String(hovered.top) + '%' }}
          >
            <strong>{hovered.point.player}</strong>
            <span>{formatInteger(hovered.point.elo)} Elo</span>
            <span>{formatCost(hovered.point.cost_usd_per_move)} / move</span>
          </div>
        ) : null}
      </div>
    </div>
  );
};

const CostChart = ({ data }) => {
  const llmPlayers = data.datasets.llm_players;
  const katagoPlayers = data.datasets.katago_players;
  const llmNames = useMemo(
    () => new Set(llmPlayers.map(player => player.player)),
    [llmPlayers],
  );
  const allPoints = useMemo(() => [...katagoPlayers, ...llmPlayers], [katagoPlayers, llmPlayers]);
  const referenceElo = data.figure_2.panels[1].katago_reference_line.elo;

  return (
    <section className="gobench-section" aria-labelledby="gobench-chart-heading">
      <div className="gobench-section-header">
        <div>
          <p className="gobench-eyebrow">Cost efficiency</p>
          <h2 id="gobench-chart-heading">Cost per move vs. Elo</h2>
        </div>
        <p className="gobench-section-note">Hover or focus a point to see its model and Elo rating.</p>
      </div>

      <div className="gobench-chart-grid">
        <ChartPanel
          title="(a) All players"
          points={allPoints}
          llmNames={llmNames}
          xDomain={[1e-7, 0.6]}
          xTicks={[
            { value: 1e-7, label: '10⁻⁷' },
            { value: 1e-5, label: '10⁻⁵' },
            { value: 1e-3, label: '10⁻³' },
            { value: 1e-1, label: '10⁻¹' },
          ]}
        />
        <ChartPanel
          title="(b) LLMs only"
          points={llmPlayers}
          llmNames={llmNames}
          xDomain={[0.011, 0.35]}
          xTicks={[
            { value: 0.02, label: '$0.02' },
            { value: 0.05, label: '$0.05' },
            { value: 0.1, label: '$0.10' },
            { value: 0.2, label: '$0.20' },
          ]}
          referenceElo={referenceElo}
        />
      </div>

      <div className="gobench-chart-legend" aria-label="Chart legend">
        <div className="gobench-legend-item">
          <span className="gobench-legend-dot is-katago" />
          <span>KataGo ({katagoPlayers.length})</span>
        </div>
        {llmPlayers.map((player, index) => (
          <div className="gobench-legend-item" key={player.player}>
            <span
              className="gobench-legend-dot"
              style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
            />
            <span>{player.player}</span>
          </div>
        ))}
      </div>
      <p className="gobench-caption">
        {data.figure_2.caption} Error bars show the 95% Elo confidence interval; the dashed line marks the strongest KataGo reference player.
      </p>
    </section>
  );
};

const neighborsOf = (row, column, size) =>
  [
    [row - 1, column],
    [row + 1, column],
    [row, column - 1],
    [row, column + 1],
  ].filter(([nextRow, nextColumn]) =>
    nextRow >= 0 && nextRow < size && nextColumn >= 0 && nextColumn < size,
  );

const findGroup = (board, startRow, startColumn) => {
  const color = board[startRow][startColumn];
  const size = board.length;
  const stones = [];
  const liberties = new Set();
  const visited = new Set();
  const pending = [[startRow, startColumn]];

  while (pending.length) {
    const [row, column] = pending.pop();
    const key = row + ':' + column;
    if (visited.has(key)) {
      continue;
    }

    visited.add(key);
    stones.push([row, column]);
    neighborsOf(row, column, size).forEach(([nextRow, nextColumn]) => {
      const neighbor = board[nextRow][nextColumn];
      if (!neighbor) {
        liberties.add(nextRow + ':' + nextColumn);
      } else if (neighbor === color && !visited.has(nextRow + ':' + nextColumn)) {
        pending.push([nextRow, nextColumn]);
      }
    });
  }

  return { stones, liberties };
};

const parseMove = (move, size) => {
  const normalized = String(move).toUpperCase();
  const match = normalized.match(/^([A-HJ])(\d+)$/);
  if (!match) {
    return null;
  }

  const column = GO_COLUMNS.indexOf(match[1]);
  const rowNumber = Number(match[2]);
  if (column < 0 || column >= size || rowNumber < 1 || rowNumber > size) {
    return null;
  }

  return { row: size - rowNumber, column };
};

const replayMoves = (moves, moveCount, size) => {
  const board = Array.from({ length: size }, () => Array(size).fill(null));
  let lastPoint = null;

  moves.slice(0, moveCount).forEach(move => {
    const point = parseMove(move.move, size);
    if (!point || board[point.row][point.column]) {
      lastPoint = null;
      return;
    }

    const color = move.color;
    const opponent = color === 'B' ? 'W' : 'B';
    board[point.row][point.column] = color;

    neighborsOf(point.row, point.column, size).forEach(([row, column]) => {
      if (board[row][column] !== opponent) {
        return;
      }
      const group = findGroup(board, row, column);
      if (group.liberties.size === 0) {
        group.stones.forEach(([stoneRow, stoneColumn]) => {
          board[stoneRow][stoneColumn] = null;
        });
      }
    });

    const ownGroup = findGroup(board, point.row, point.column);
    if (ownGroup.liberties.size === 0) {
      ownGroup.stones.forEach(([stoneRow, stoneColumn]) => {
        board[stoneRow][stoneColumn] = null;
      });
      lastPoint = null;
    } else {
      lastPoint = point;
    }
  });

  return { board, lastPoint };
};

const GoBoard = ({ moves, moveCount, size }) => {
  const position = useMemo(() => replayMoves(moves, moveCount, size), [moves, moveCount, size]);
  const viewSize = 500;
  const margin = 46;
  const boardWidth = viewSize - margin * 2;
  const spacing = boardWidth / (size - 1);
  const starPoints = size === 9
    ? [[2, 2], [2, 6], [4, 4], [6, 2], [6, 6]]
    : [];

  return (
    <svg
      className="gobench-board"
      viewBox={'0 0 ' + viewSize + ' ' + viewSize}
      role="img"
      aria-label={'Go board after ' + moveCount + ' moves'}
    >
      <defs>
        <radialGradient id="gobench-white-stone" cx="35%" cy="28%" r="70%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#d9d7d1" />
        </radialGradient>
        <radialGradient id="gobench-black-stone" cx="35%" cy="28%" r="70%">
          <stop offset="0%" stopColor="#505050" />
          <stop offset="100%" stopColor="#101010" />
        </radialGradient>
      </defs>
      <rect className="gobench-board-background" x="0" y="0" width={viewSize} height={viewSize} />

      {Array.from({ length: size }, (_, index) => {
        const offset = margin + spacing * index;
        return (
          <g key={'grid-' + index}>
            <line className="gobench-board-line" x1={margin} x2={viewSize - margin} y1={offset} y2={offset} />
            <line className="gobench-board-line" x1={offset} x2={offset} y1={margin} y2={viewSize - margin} />
            <text className="gobench-board-coordinate" x={offset} y={viewSize - 12} textAnchor="middle">
              {GO_COLUMNS[index]}
            </text>
            <text className="gobench-board-coordinate" x="18" y={offset + 4} textAnchor="middle">
              {size - index}
            </text>
          </g>
        );
      })}

      {starPoints.map(([row, column]) => (
        <circle
          className="gobench-board-star"
          key={row + '-' + column}
          cx={margin + column * spacing}
          cy={margin + row * spacing}
          r="4"
        />
      ))}

      {position.board.flatMap((row, rowIndex) =>
        row.map((stone, columnIndex) => {
          if (!stone) {
            return null;
          }

          const isLast =
            position.lastPoint?.row === rowIndex && position.lastPoint?.column === columnIndex;
          const x = margin + columnIndex * spacing;
          const y = margin + rowIndex * spacing;

          return (
            <g key={rowIndex + '-' + columnIndex}>
              <circle
                className="gobench-stone"
                cx={x}
                cy={y}
                r={spacing * 0.44}
                fill={stone === 'B' ? 'url(#gobench-black-stone)' : 'url(#gobench-white-stone)'}
                stroke={stone === 'B' ? '#090909' : '#b4b0a9'}
              />
              {isLast ? (
                <circle
                  className="gobench-last-move"
                  cx={x}
                  cy={y}
                  r={spacing * 0.105}
                  fill={stone === 'B' ? '#ffffff' : '#151515'}
                />
              ) : null}
            </g>
          );
        }),
      )}
    </svg>
  );
};

const getOutcome = game => {
  if (!game.winner || game.score_black === 0.5) {
    return 'Draw';
  }

  return game.winner === game.llm_player ? 'Win' : 'Loss';
};

const compactOpponentName = player => {
  if (player === 'kata1-random') {
    return 'KataGo · random';
  }

  const step = player.match(/-s(\d+)/)?.[1];
  const temperature = player.match(/-temp-([\d.]+)/)?.[1];
  const stepLabel = step
    ? Number(step) >= 1e6
      ? formatTwoSignificantFigures(Number(step) / 1e6) + 'M steps'
      : formatInteger(Number(step)) + ' steps'
    : player;
  return 'KataGo · ' + stepLabel + (temperature ? ' · temp ' + temperature : '');
};

const getOpponentRating = (player, katagoPlayers) => {
  if (player === 'kata1-random') {
    return { elo: 0, eloCi95: 0 };
  }

  const basePlayer = player.replace(/-temp-[\d.]+$/, '');
  const checkpoint = katagoPlayers.find(candidate => candidate.player === basePlayer);
  return checkpoint
    ? { elo: checkpoint.elo, eloCi95: checkpoint.elo_ci_95 }
    : { elo: null, eloCi95: null };
};

const GameReplayer = ({ data }) => {
  const games = data.datasets.llm_vs_katago_games;
  const tablePlayerOrder = useMemo(
    () => data.datasets.llm_players.map(player => player.player),
    [data.datasets.llm_players],
  );
  const llmPlayers = useMemo(() => {
    const gamePlayers = Array.from(new Set(games.map(game => game.llm_player)));
    return [
      ...tablePlayerOrder.filter(player => gamePlayers.includes(player)),
      ...gamePlayers.filter(player => !tablePlayerOrder.includes(player)).sort(),
    ];
  }, [games, tablePlayerOrder]);
  const [llm, setLlm] = useState(llmPlayers[0] || '');
  const [opponent, setOpponent] = useState('');
  const [gameId, setGameId] = useState('');
  const [moveCount, setMoveCount] = useState(0);
  const [playing, setPlaying] = useState(false);

  const opponentOptions = useMemo(() => {
    const grouped = new Map();
    games
      .filter(game => game.llm_player === llm)
      .forEach(game => {
        const current = grouped.get(game.katago_player) || {
          player: game.katago_player,
          wins: 0,
          losses: 0,
          draws: 0,
        };
        const outcome = getOutcome(game);
        if (outcome === 'Win') current.wins += 1;
        if (outcome === 'Loss') current.losses += 1;
        if (outcome === 'Draw') current.draws += 1;
        grouped.set(game.katago_player, current);
      });

    return Array.from(grouped.values())
      .map(item => ({
        ...item,
        ...getOpponentRating(item.player, data.datasets.katago_players),
      }))
      .sort((left, right) => (right.elo ?? -1) - (left.elo ?? -1));
  }, [data.datasets.katago_players, games, llm]);

  useEffect(() => {
    if (!opponentOptions.some(option => option.player === opponent)) {
      setOpponent(opponentOptions[0]?.player || '');
    }
  }, [opponent, opponentOptions]);

  const filteredGames = useMemo(
    () => games.filter(game => game.llm_player === llm && game.katago_player === opponent),
    [games, llm, opponent],
  );

  useEffect(() => {
    if (!filteredGames.some(game => game.id === gameId)) {
      setGameId(filteredGames[0]?.id || '');
    }
  }, [filteredGames, gameId]);

  const selectedGame = filteredGames.find(game => game.id === gameId) || filteredGames[0];
  const selectedOpponent = opponentOptions.find(option => option.player === opponent);

  useEffect(() => {
    setMoveCount(0);
    setPlaying(false);
  }, [selectedGame?.id]);

  useEffect(() => {
    if (!playing || !selectedGame) {
      return undefined;
    }

    if (moveCount >= selectedGame.moves.length) {
      setPlaying(false);
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setMoveCount(current => Math.min(current + 1, selectedGame.moves.length));
    }, 450);

    return () => window.clearTimeout(timer);
  }, [moveCount, playing, selectedGame]);

  if (!selectedGame) {
    return null;
  }

  const currentMove = moveCount > 0 ? selectedGame.moves[moveCount - 1] : null;
  const outcome = getOutcome(selectedGame);
  const outcomeClass = outcome.toLowerCase();
  const visibleMoves = selectedGame.moves.slice(Math.max(0, moveCount - 7), moveCount);

  const moveTo = nextMove => {
    setPlaying(false);
    setMoveCount(Math.max(0, Math.min(nextMove, selectedGame.moves.length)));
  };

  return (
    <section className="gobench-section" aria-labelledby="gobench-replayer-heading">
      <div className="gobench-section-header">
        <div>
          <p className="gobench-eyebrow">Game explorer</p>
          <h2 id="gobench-replayer-heading">Replay every match</h2>
        </div>
        <p className="gobench-section-note">
          Choose an LLM, its KataGo opponent, and a game. Records are shown from the LLM’s perspective.
        </p>
      </div>

      <div className="gobench-picker-grid">
        <label>
          <span><b>1</b> LLM</span>
          <select
            value={llm}
            onChange={event => {
              setLlm(event.target.value);
              setOpponent('');
              setGameId('');
            }}
          >
            {llmPlayers.map(player => (
              <option key={player} value={player}>{player}</option>
            ))}
          </select>
        </label>

        <label>
          <span><b>2</b> Opponent · W–L–D · Elo ± 95% CI</span>
          <select
            value={opponent}
            onChange={event => {
              setOpponent(event.target.value);
              setGameId('');
            }}
          >
            {opponentOptions.map(option => (
              <option key={option.player} value={option.player}>
                {compactOpponentName(option.player)} · {option.wins}–{option.losses}–{option.draws} · {option.elo === null ? 'Elo N/A' : formatInteger(option.elo) + ' Elo ±' + formatInteger(option.eloCi95)}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span><b>3</b> Game · LLM result</span>
          <select value={selectedGame.id} onChange={event => setGameId(event.target.value)}>
            {filteredGames.map((game, index) => (
              <option key={game.id} value={game.id}>
                Game {index + 1} · {getOutcome(game)} · {game.llm_color === 'B' ? 'Black' : 'White'} · {game.result}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="gobench-replayer">
        <div
          className="gobench-board-wrap"
          tabIndex="0"
          onKeyDown={event => {
            if (event.key === 'ArrowLeft') {
              event.preventDefault();
              moveTo(moveCount - 1);
            }
            if (event.key === 'ArrowRight') {
              event.preventDefault();
              moveTo(moveCount + 1);
            }
          }}
        >
          <GoBoard moves={selectedGame.moves} moveCount={moveCount} size={data.games.board_size} />
        </div>

        <div className="gobench-game-panel">
          <div className="gobench-game-result-row">
            <span className={'gobench-outcome is-' + outcomeClass}>{outcome}</span>
            <span className="gobench-result-code">{selectedGame.result}</span>
          </div>

          <dl className="gobench-game-meta">
            <div>
              <dt>Black</dt>
              <dd><span className="gobench-color-chip is-black" />{selectedGame.black}</dd>
            </div>
            <div>
              <dt>White</dt>
              <dd><span className="gobench-color-chip is-white" />{selectedGame.white}</dd>
            </div>
            <div>
              <dt>Opponent Elo · 95% CI</dt>
              <dd>{selectedOpponent?.elo === null ? 'N/A' : formatInteger(selectedOpponent?.elo) + ' ±' + formatInteger(selectedOpponent?.eloCi95)}</dd>
            </div>
            <div>
              <dt>Ended by</dt>
              <dd>{selectedGame.reason.replace('_', ' ')}</dd>
            </div>
          </dl>

          <div className="gobench-now-playing" aria-live="polite">
            <span>Current move</span>
            <strong>
              {currentMove
                ? currentMove.number + '. ' + (currentMove.color === 'B' ? 'Black' : 'White') + ' · ' + currentMove.move
                : 'Start position'}
            </strong>
          </div>

          <div className="gobench-move-strip" aria-hidden="true">
            {visibleMoves.length ? visibleMoves.map(move => (
              <span key={move.number} className={move.number === currentMove?.number ? 'is-current' : undefined}>
                {move.number} {move.move}
              </span>
            )) : <span className="is-empty">No moves played</span>}
          </div>

          <div className="gobench-playback">
            <div className="gobench-playback-buttons">
              <button type="button" onClick={() => moveTo(0)} disabled={moveCount === 0} aria-label="First move">|←</button>
              <button type="button" onClick={() => moveTo(moveCount - 1)} disabled={moveCount === 0} aria-label="Previous move">←</button>
              <button
                type="button"
                className="is-primary"
                onClick={() => {
                  if (moveCount >= selectedGame.moves.length) {
                    setMoveCount(0);
                  }
                  setPlaying(current => !current);
                }}
                aria-label={playing ? 'Pause replay' : 'Play replay'}
              >
                {playing ? 'Pause' : 'Play'}
              </button>
              <button type="button" onClick={() => moveTo(moveCount + 1)} disabled={moveCount === selectedGame.moves.length} aria-label="Next move">→</button>
              <button type="button" onClick={() => moveTo(selectedGame.moves.length)} disabled={moveCount === selectedGame.moves.length} aria-label="Last move">→|</button>
            </div>
            <div className="gobench-scrubber-row">
              <input
                type="range"
                min="0"
                max={selectedGame.moves.length}
                value={moveCount}
                onChange={event => moveTo(Number(event.target.value))}
                aria-label="Replay position"
              />
              <span>{moveCount} / {selectedGame.moves.length}</span>
            </div>
          </div>
        </div>
      </div>
      <p className="gobench-caption">
        {formatInteger(data.games.count)} games · {data.games.board_size}×{data.games.board_size} board · {data.games.rules} rules · {data.games.komi} komi
      </p>
    </section>
  );
};

const LoadingState = () => (
  <div className="gobench-loading" role="status">
    <span />
    <p>Loading GoBench results…</p>
  </div>
);

const GoBench = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    fetch(DATA_URL, { signal: controller.signal })
      .then(response => {
        if (!response.ok) {
          throw new Error('Unable to load the benchmark data.');
        }
        return response.json();
      })
      .then(setData)
      .catch(fetchError => {
        if (fetchError.name !== 'AbortError') {
          setError(fetchError.message);
        }
      });

    return () => controller.abort();
  }, []);

  if (error) {
    return <div className="gobench-error" role="alert">{error}</div>;
  }

  if (!data) {
    return <LoadingState />;
  }

  return (
    <div className="gobench-root">
      <div className="gobench-overview" aria-label="Benchmark summary">
        <div>
          <span>Evaluated models</span>
          <strong>{data.datasets.llm_players.length}</strong>
        </div>
        <div>
          <span>KataGo references</span>
          <strong>{data.datasets.katago_players.length}</strong>
        </div>
        <div>
          <span>Recorded games</span>
          <strong>{data.games.count}</strong>
        </div>
        <div>
          <span>Board</span>
          <strong>{data.games.board_size}×{data.games.board_size}</strong>
        </div>
      </div>
      <Leaderboard data={data} />
      <CostChart data={data} />
      <GameReplayer data={data} />
    </div>
  );
};

export default GoBench;
