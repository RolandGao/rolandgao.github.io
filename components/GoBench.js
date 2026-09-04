import { Fragment, useEffect, useMemo, useState } from 'react';

import { useGoBenchData } from './GoBenchData';
import ProviderLogo, { getProvider } from './ProviderLogo';

const API_PLAYER_SUFFIX = '-api';
const GO_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'];
const CHART_COLORS = {
  anthropic: '#9b4f32',
  google: '#356fd4',
  deepseek: '#6754d9',
  moonshot: '#e59112',
  openai: '#109b78',
  meta: '#e34f88',
  xai: '#272727',
  unknown: '#767676',
};
const HARNESS_PRESENTATION = {
  api: { label: 'API', color: '#272727' },
  'codex-multi': { label: 'Codex multi', color: '#6754d9' },
  'codex-workspace': { label: 'Codex workspace', color: '#109b78' },
  'codex-workspace-continual': { label: 'Codex workspace continual', color: '#d06f32' },
};
const HARNESS_ORDER = Object.keys(HARNESS_PRESENTATION);
const REASONING_ORDER = { low: 0, high: 1, max: 2 };
const REASONING_PRESENTATION = {
  low: { label: 'Low', shape: 'triangle' },
  high: { label: 'High', shape: 'diamond' },
  max: { label: 'Max', shape: 'pentagon' },
};

const PLAYER_PRESENTATION = {
  'opus-5-high': { label: 'Claude Opus 5' },
  'gemini-3.1-pro-high': { label: 'Gemini 3.1 Pro' },
  'DeepSeek-V4-Flash-0731-high': { label: 'DeepSeek V4 Flash 0731' },
  'kimi-k3-high': { label: 'Kimi K3' },
  'gpt5.6-sol-high': { label: 'GPT-5.6 Sol' },
  'gpt5.6-sol-low': { label: 'GPT-5.6 Sol' },
  'gpt5.6-sol-high-context': { label: 'GPT-5.6 Sol' },
  'gpt5.6-sol-max-context': { label: 'GPT-5.6 Sol' },
  'gpt5.6-luna-high': { label: 'GPT-5.6 Luna' },
  'gpt5.6-luna-low': { label: 'GPT-5.6 Luna' },
  'gpt5.6-luna-high-context': { label: 'GPT-5.6 Luna' },
  'gpt5.6-luna-max-context': { label: 'GPT-5.6 Luna' },
  'muse-spark-1.2-openrouter-high': { label: 'Muse Spark 1.2' },
  'gpt-5.4-low': { label: 'GPT-5.4' },
  'grok-4.5-high': { label: 'Grok 4.5' },
  'gemini-3.6-flash-high': { label: 'Gemini 3.6 Flash' },
};

const getApiPlayerBaseName = player => player.endsWith(API_PLAYER_SUFFIX)
  ? player.slice(0, -API_PLAYER_SUFFIX.length)
  : player;

const isApiPlayer = player => typeof player === 'string' && player.endsWith(API_PLAYER_SUFFIX);

const getHarnessPlayerDetails = player => {
  const match = player.match(/^gpt5\.6-sol-(low|high|max)-(.+)$/);

  if (!match || !HARNESS_PRESENTATION[match[2]]) {
    return null;
  }

  return {
    reasoning: match[1],
    harness: match[2],
  };
};

const getPlayerPresentation = player => {
  const baseName = getApiPlayerBaseName(player);

  return PLAYER_PRESENTATION[baseName] || {
    label: baseName,
  };
};

const filterApiData = data => ({
  ...data,
  datasets: {
    ...data.datasets,
    llm_players: data.datasets.llm_players.filter(player => isApiPlayer(player.player)),
  },
});

const formatPlayerDisplayName = player => getPlayerPresentation(player).label;

const formatHarnessPlayerDisplayName = player => {
  const details = getHarnessPlayerDetails(player);
  if (!details) {
    return formatPlayerDisplayName(player);
  }

  return 'GPT-5.6 Sol · ' +
    details.reasoning[0].toUpperCase() + details.reasoning.slice(1) +
    ' · ' + HARNESS_PRESENTATION[details.harness].label;
};

const formatReplayPlayerDisplayName = player => {
  const details = getHarnessPlayerDetails(player);
  return details && details.harness !== 'api'
    ? formatHarnessPlayerDisplayName(player)
    : formatPlayerDisplayName(player);
};

const formatReplayPlayerOption = (player, rating) => {
  const presentation = getPlayerPresentation(player);
  const details = getHarnessPlayerDetails(player);
  const ratingLabel = Number.isFinite(rating)
    ? ' · ' + formatInteger(rating) + ' Elo'
    : '';

  if (details && details.harness !== 'api') {
    const reasoning = details.reasoning[0].toUpperCase() + details.reasoning.slice(1);
    return 'GPT-5.6 Sol' + ratingLabel +
      ' · ' + HARNESS_PRESENTATION[details.harness].label +
      ' · ' + reasoning;
  }

  return presentation.label + ratingLabel;
};

const getResultRowAlpha = (resultOrder, resultCount) => {
  if (resultCount <= 1) {
    return 0.17;
  }

  const progress = resultOrder / (resultCount - 1);
  return 0.17 + (0.03 - 0.17) * progress;
};

const getChartColor = player => CHART_COLORS[getProvider(player)] || CHART_COLORS.unknown;

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
    render: row => (
      <span className="gobench-player-cell" title={row.player}>
        <ProviderLogo player={row.player} />
        <span className="gobench-player-details">
          <span>{row.label}</span>
        </span>
      </span>
    ),
  },
  {
    key: 'elo',
    label: 'Elo',
    value: row => row.elo,
    render: row => (
      <span className="gobench-elo-value">
        <strong>{formatInteger(row.elo)}</strong>
        <span>± {formatInteger(row.elo_ci_95)}</span>
      </span>
    ),
  },
  {
    key: 'cost',
    label: 'Cost / move',
    compactLabel: 'Cost',
    value: row => row.cost,
    render: row => (
      <span className="gobench-cost-value">
        <span className="gobench-cost-value-full">{formatCost(row.cost)}</span>
        <span className="gobench-cost-value-compact" aria-hidden="true">
          {formatCompactCost(row.cost)}
        </span>
      </span>
    ),
  },
  {
    key: 'seconds',
    label: 'Seconds / move',
    compactLabel: 'Seconds',
    value: row => row.seconds,
    render: row => formatTwoSignificantFigures(row.seconds) + 's',
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

const formatCompactCost = value => {
  if (value > 0 && value < 0.0001) {
    const exponent = Math.floor(Math.log10(value));
    const mantissa = value / 10 ** exponent;
    return '$' + formatTwoSignificantFigures(mantissa) + 'e' + exponent;
  }

  return '$' + formatTwoSignificantFigures(value);
};

const getTableRows = data => {
  const llmRows = data.datasets.llm_players.map((player, resultOrder) => {
    const presentation = getPlayerPresentation(player.player);

    return {
      ...player,
      ...presentation,
      resultOrder,
      seconds: player.api_seconds_per_move,
      cost: player.cost_usd_per_move,
      rowType: 'llm',
    };
  });
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
  const resultCount = data.datasets.llm_players.length;
  const [sort, setSort] = useState(null);
  const [isHorizontallyScrolled, setIsHorizontallyScrolled] = useState(false);

  const displayedRows = useMemo(() => {
    if (!sort) {
      return rows;
    }

    const column = TABLE_COLUMNS.find(candidate => candidate.key === sort.key);
    const llmRows = rows.filter(row => row.rowType === 'llm');
    const referenceRows = rows.filter(row => row.rowType === 'reference');

    const sortedLlmRows = llmRows
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

    return [...sortedLlmRows, ...referenceRows];
  }, [rows, sort]);

  const sortBy = key => {
    setSort(current => {
      if (current?.key !== key) {
        return { key, direction: 'ascending' };
      }

      if (current.direction === 'ascending') {
        return { key, direction: 'descending' };
      }

      return null;
    });
  };

  return (
    <section className="gobench-section" aria-labelledby="gobench-leaderboard-heading">
      <div className="gobench-section-header">
        <h2 id="gobench-leaderboard-heading">Leaderboard</h2>
        <p className="gobench-caption">API results · Elo ± 95% confidence interval. Select a column heading to sort.</p>
      </div>
      <div className="gobench-table-shell">
        <div
          className={
            isHorizontallyScrolled
              ? 'gobench-table-scroll is-horizontally-scrolled'
              : 'gobench-table-scroll'
          }
          onScroll={event => {
            const nextIsScrolled = event.currentTarget.scrollLeft > 1;
            if (nextIsScrolled !== isHorizontallyScrolled) {
              setIsHorizontallyScrolled(nextIsScrolled);
            }
          }}
        >
          <table className="gobench-table">
            <colgroup>
              <col className="gobench-col-rank" />
              <col className="gobench-col-player" />
              <col className="gobench-col-elo" />
              <col className="gobench-col-cost" />
              <col className="gobench-col-seconds" />
            </colgroup>
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
                      className={
                        (column.align === 'left' ? 'is-left ' : '') +
                        'is-' + column.key
                      }
                    >
                      <button
                        type="button"
                        aria-label={'Sort by ' + column.label}
                        onClick={() => sortBy(column.key)}
                      >
                        <span className="gobench-column-label">
                          <span className="gobench-column-label-full">{column.label}</span>
                          {column.compactLabel ? (
                            <span className="gobench-column-label-compact" aria-hidden="true">
                              {column.compactLabel}
                            </span>
                          ) : null}
                        </span>
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
              {displayedRows.map((row, index) => {
                const isFirstReference = row.rowType === 'reference' &&
                  (index === 0 || displayedRows[index - 1].rowType !== 'reference');
                const rowStyle = row.rowType === 'llm'
                  ? { '--gobench-row-alpha': getResultRowAlpha(row.resultOrder, resultCount) }
                  : undefined;

                return (
                  <Fragment key={row.player}>
                    {isFirstReference ? (
                      <tr className="gobench-reference-heading">
                        <th colSpan={TABLE_COLUMNS.length} scope="rowgroup">
                          <span>KataGo references</span>
                        </th>
                      </tr>
                    ) : null}
                    <tr
                      className={row.rowType === 'reference'
                        ? 'gobench-reference-row'
                        : 'gobench-result-row'}
                      style={rowStyle}
                    >
                      {TABLE_COLUMNS.map(column => (
                        <td
                          key={column.key}
                          className={
                            (column.align === 'left' ? 'is-left ' : '') +
                            (column.key === 'player' ? 'is-player ' : '') +
                            'is-' + column.key
                          }
                        >
                          {column.render(row, index)}
                        </td>
                      ))}
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
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

const PointMarker = ({ shape = 'circle', color, muted = false }) => {
  const markerProps = {
    className: 'gobench-point-shape',
    fill: color,
    stroke: muted ? '#f6f5f2' : '#ffffff',
    strokeWidth: muted ? 1 : 2,
  };

  if (shape === 'triangle') {
    return <polygon {...markerProps} points="0,-7 6.5,5.5 -6.5,5.5" />;
  }

  if (shape === 'diamond') {
    return <polygon {...markerProps} points="0,-7 7,0 0,7 -7,0" />;
  }

  if (shape === 'pentagon') {
    return <polygon {...markerProps} points="0,-7 6.7,-2.2 4.1,5.7 -4.1,5.7 -6.7,-2.2" />;
  }

  return <circle {...markerProps} cx="0" cy="0" r={muted ? 4 : 6} />;
};

const PointGlyph = ({
  point,
  displayName,
  x,
  y,
  color,
  shape = 'circle',
  muted = false,
  onEnter,
  onLeave,
}) => {
  const confidence = Number.isFinite(point.elo_ci_95)
    ? ' plus or minus ' + formatInteger(point.elo_ci_95)
    : '';
  const label =
    displayName + ', ' + formatInteger(point.elo) + confidence +
    ' Elo, ' + formatCost(point.cost_usd_per_move) + ' per move';

  return (
    <g
      className={muted ? 'gobench-chart-point is-muted' : 'gobench-chart-point'}
      transform={'translate(' + x + ' ' + y + ')'}
      role="img"
      aria-label={label}
      tabIndex={muted ? undefined : 0}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onFocus={onEnter}
      onBlur={onLeave}
    >
      <title>{label}</title>
      <PointMarker shape={shape} color={color} muted={muted} />
    </g>
  );
};

const ChartPanel = ({
  title,
  points,
  llmNames,
  referenceNames,
  xDomain,
  xTicks,
  displayNames,
  pointColors,
  pointShapes,
  series = [],
  showTitle = true,
  yDomain = [0, 4600],
  yTicks = [0, 1000, 2000, 3000, 4000],
}) => {
  const width = 560;
  const height = 390;
  const margin = { top: 45, right: 22, bottom: 60, left: 96 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const [hovered, setHovered] = useState(null);

  const xPosition = value =>
    logScale(value, xDomain[0], xDomain[1], margin.left, margin.left + plotWidth);
  const yPosition = value =>
    linearScale(value, yDomain[0], yDomain[1], margin.top + plotHeight, margin.top);

  const showPoint = (point, displayName) => {
    const x = xPosition(point.cost_usd_per_move);
    const y = yPosition(point.elo);
    setHovered({
      point,
      displayName,
      left: (x / width) * 100,
      top: (y / height) * 100,
      placement: y < margin.top + 70 ? 'below' : 'above',
    });
  };

  return (
    <div className="gobench-chart-panel">
      {showTitle ? <div className="gobench-chart-title">{title}</div> : null}
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

          {series.map(item => (
            <polyline
              key={item.key}
              className="gobench-chart-series"
              points={item.points.map(point =>
                xPosition(point.cost_usd_per_move) + ',' + yPosition(point.elo)).join(' ')}
              stroke={item.color}
            />
          ))}

          {points.map(point => {
            const isLlm = llmNames.has(point.player);
            const displayName = displayNames?.get(point.player) || (isLlm
              ? formatPlayerDisplayName(point.player)
              : referenceNames.get(point.player) || 'KataGo');
            const x = xPosition(point.cost_usd_per_move);
            const y = yPosition(point.elo);
            const error = isLlm ? point.elo_ci_95 : null;
            const color = pointColors?.get(point.player) ||
              (isLlm ? getChartColor(point.player) : '#9aa3ad');

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
                  displayName={displayName}
                  x={x}
                  y={y}
                  color={color}
                  shape={pointShapes?.get(point.player)}
                  muted={!isLlm}
                  onEnter={() => showPoint(point, displayName)}
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
            Cost / move
          </text>
          <text
            className="gobench-chart-axis-label"
            transform={'translate(18 ' + (margin.top + plotHeight / 2) + ') rotate(-90)'}
            textAnchor="middle"
          >
            Elo
          </text>
        </svg>

        {hovered ? (
          <div
            className={'gobench-chart-tooltip is-' + hovered.placement}
            style={{
              '--gobench-tooltip-x': String(hovered.left) + '%',
              top: String(hovered.top) + '%',
            }}
          >
            <strong>{hovered.displayName}</strong>
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
  const llmPointShapes = useMemo(
    () => new Map(llmPlayers.map(player => [player.player, data.figure_2.llm_marker])),
    [data.figure_2.llm_marker, llmPlayers],
  );
  const referenceNames = useMemo(
    () => new Map(
      data.table_2.katago_reference_players.map(player => [player.player, player.label]),
    ),
    [data.table_2.katago_reference_players],
  );
  const llmCostDomain = useMemo(() => {
    const costs = llmPlayers
      .map(player => player.cost_usd_per_move)
      .filter(cost => Number.isFinite(cost) && cost > 0);

    if (!costs.length) {
      return [0.001, 0.5];
    }

    return [Math.min(...costs) / 1.45, Math.max(...costs) * 1.3];
  }, [llmPlayers]);
  const llmCostTicks = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
    .filter(value => value > llmCostDomain[0] && value < llmCostDomain[1])
    .map(value => ({
      value,
      label: '$' + value,
  }));

  return (
    <section className="gobench-section" aria-label="LLM Elo versus cost charts">
      <div className="gobench-chart-grid">
        <ChartPanel
          title="(a) KataGo and LLMs"
          points={allPoints}
          llmNames={llmNames}
          referenceNames={referenceNames}
          pointShapes={llmPointShapes}
          xDomain={[1e-7, 0.6]}
          xTicks={[
            { value: 1e-7, label: '10⁻⁷' },
            { value: 1e-5, label: '10⁻⁵' },
            { value: 1e-3, label: '10⁻³' },
            { value: 1e-1, label: '10⁻¹' },
          ]}
        />
        <ChartPanel
          title="(b) LLMs (high reasoning effort)"
          points={llmPlayers}
          llmNames={llmNames}
          referenceNames={referenceNames}
          pointShapes={llmPointShapes}
          xDomain={llmCostDomain}
          xTicks={llmCostTicks}
          yDomain={[750, 2500]}
          yTicks={[1000, 1500, 2000, 2500]}
        />
      </div>

      <div className="gobench-chart-legend" aria-label="Chart legend">
        <div className="gobench-legend-item">
          <span className="gobench-legend-dot is-katago" />
          <span>KataGo ({katagoPlayers.length})</span>
        </div>
        {llmPlayers.map(player => (
          <div className="gobench-legend-item" key={player.player}>
            <svg className="gobench-marker-key" viewBox="-10 -10 20 20" aria-hidden="true">
              <PointMarker
                shape={data.figure_2.llm_marker}
                color={getChartColor(player.player)}
              />
            </svg>
            <span>{formatPlayerDisplayName(player.player)}</span>
          </div>
        ))}
      </div>
    </section>
  );
};

const AgenticHarnessChart = ({ data }) => {
  const chartData = useMemo(() => {
    const groupedPlayers = new Map(HARNESS_ORDER.map(harness => [harness, []]));

    data.datasets.sol_harness_players.forEach(player => {
      const details = getHarnessPlayerDetails(player.player);
      if (details) {
        groupedPlayers.get(details.harness).push({ ...player, ...details });
      }
    });

    const series = HARNESS_ORDER.map(harness => {
      const presentation = HARNESS_PRESENTATION[harness];
      return {
        key: harness,
        label: presentation.label,
        color: presentation.color,
        points: groupedPlayers.get(harness)
          .sort((left, right) => REASONING_ORDER[left.reasoning] - REASONING_ORDER[right.reasoning]),
      };
    }).filter(item => item.points.length);
    const points = series.flatMap(item => item.points);
    const pointColors = new Map();
    const displayNames = new Map();
    const pointShapes = new Map();

    series.forEach(item => {
      item.points.forEach(point => {
        pointColors.set(point.player, item.color);
        pointShapes.set(point.player, REASONING_PRESENTATION[point.reasoning].shape);
        displayNames.set(
          point.player,
          formatHarnessPlayerDisplayName(point.player),
        );
      });
    });

    return {
      series,
      points,
      pointColors,
      pointShapes,
      displayNames,
      playerNames: new Set(points.map(player => player.player)),
    };
  }, [data.datasets.sol_harness_players]);

  if (!chartData.points.length) {
    return null;
  }

  return (
    <section className="gobench-section" aria-labelledby="gobench-harness-chart-heading">
      <div className="gobench-section-header">
        <div>
          <h2 id="gobench-harness-chart-heading">Elo vs cost for agentic harnesses</h2>
          <dl className="gobench-harness-definitions">
            <div>
              <dt>API</dt>
              <dd>A single-turn API call with no tools.</dd>
            </div>
            <div>
              <dt>Codex multi</dt>
              <dd>Multi-turn execution with automatic context compaction and no tools.</dd>
            </div>
            <div>
              <dt>Codex workspace</dt>
              <dd>Multi-turn execution with offline tools and a sandboxed workspace for each game.</dd>
            </div>
            <div>
              <dt>Codex workspace continual</dt>
              <dd>The same setup, but with the workspace and conversation preserved across games.</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="gobench-chart-grid is-single">
        <ChartPanel
          title="Elo vs cost for agentic harnesses"
          showTitle={false}
          points={chartData.points}
          llmNames={chartData.playerNames}
          referenceNames={new Map()}
          displayNames={chartData.displayNames}
          pointColors={chartData.pointColors}
          pointShapes={chartData.pointShapes}
          series={chartData.series}
          xDomain={[0.02, 0.5]}
          xTicks={[
            { value: 0.02, label: '$0.02' },
            { value: 0.05, label: '$0.05' },
            { value: 0.1, label: '$0.10' },
            { value: 0.2, label: '$0.20' },
            { value: 0.5, label: '$0.50' },
          ]}
          yDomain={[750, 2500]}
          yTicks={[1000, 1500, 2000, 2500]}
        />
      </div>

      <div className="gobench-harness-keys">
        <div className="gobench-harness-key-group" role="group" aria-label="Color shows execution mode">
          <div className="gobench-harness-key-items is-modes">
            {chartData.series.map(item => (
              <div className="gobench-legend-item" key={item.key}>
                <span className="gobench-legend-line" style={{ backgroundColor: item.color }} />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="gobench-harness-key-group" role="group" aria-label="Shape shows reasoning effort">
          <div className="gobench-harness-key-items is-reasoning">
            {Object.entries(REASONING_PRESENTATION).map(([key, item]) => (
              <div className="gobench-legend-item" key={key}>
                <svg className="gobench-marker-key" viewBox="-10 -10 20 20" aria-hidden="true">
                  <PointMarker shape={item.shape} color="#5f5b56" />
                </svg>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
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

const formatGameResult = result => String(result || '').replace(/\.0+$/, '');

const getOpponentRating = (player, katagoPlayers) => {
  if (player === 'kata1-random') {
    return { elo: 0, eloCi95: 0 };
  }

  const exactPlayer = katagoPlayers.find(candidate => candidate.player === player);
  if (exactPlayer) {
    return { elo: exactPlayer.elo, eloCi95: exactPlayer.elo_ci_95 };
  }

  const basePlayer = player.replace(/-temp-[\d.]+$/, '');
  const checkpoint = katagoPlayers.find(candidate => candidate.player === basePlayer);
  return checkpoint
    ? { elo: checkpoint.elo, eloCi95: checkpoint.elo_ci_95 }
    : { elo: null, eloCi95: null };
};

const formatOpponentRating = ({ elo, eloCi95 }) =>
  elo === null
    ? 'Elo N/A'
    : 'Elo ' + formatInteger(elo) + ' ± ' + formatInteger(eloCi95);

const formatOpponentOption = option => {
  const rating = option.elo === null
    ? 'Elo N/A'
    : formatInteger(option.elo) + ' ± ' + formatInteger(option.eloCi95) + ' Elo';
  return rating + ' · ' + option.wins + '–' + option.losses + '–' + option.draws;
};

const compactGamePlayerName = (player, katagoPlayers) => {
  if (!player.startsWith('kata1-')) {
    return formatReplayPlayerDisplayName(player);
  }

  const rating = getOpponentRating(player, katagoPlayers);
  return rating.elo === null
    ? 'KataGo · Elo N/A'
    : 'KataGo · ' + formatInteger(rating.elo) + ' Elo';
};

const GameReplayer = ({ data }) => {
  const games = data.datasets.llm_vs_katago_games;
  const katagoPlayers = data.datasets.katago_players;
  const replayLlmRatings = useMemo(
    () => new Map(
      [...data.datasets.llm_players, ...data.datasets.sol_harness_players]
        .map(player => [player.player, player.elo]),
    ),
    [data.datasets.llm_players, data.datasets.sol_harness_players],
  );
  const llmPlayerGroups = useMemo(() => {
    const gamePlayers = Array.from(new Set(games.map(game => game.llm_player)));
    const byElo = (left, right) =>
      (replayLlmRatings.get(right) ?? Number.NEGATIVE_INFINITY) -
      (replayLlmRatings.get(left) ?? Number.NEGATIVE_INFINITY);

    return [
      {
        label: 'API',
        players: gamePlayers.filter(isApiPlayer).sort(byElo),
      },
      {
        label: 'Agentic harnesses',
        players: gamePlayers.filter(player => !isApiPlayer(player)).sort(byElo),
      },
    ];
  }, [games, replayLlmRatings]);
  const llmPlayers = llmPlayerGroups.flatMap(group => group.players);
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
        const rating = getOpponentRating(game.katago_player, katagoPlayers);
        const key = String(rating.elo) + ':' + String(rating.eloCi95);
        const current = grouped.get(key) || {
          key,
          players: [],
          ...rating,
          wins: 0,
          losses: 0,
          draws: 0,
        };
        if (!current.players.includes(game.katago_player)) {
          current.players.push(game.katago_player);
        }
        const outcome = getOutcome(game);
        if (outcome === 'Win') current.wins += 1;
        if (outcome === 'Loss') current.losses += 1;
        if (outcome === 'Draw') current.draws += 1;
        grouped.set(key, current);
      });

    return Array.from(grouped.values())
      .sort((left, right) => (right.elo ?? -1) - (left.elo ?? -1));
  }, [games, llm, katagoPlayers]);

  useEffect(() => {
    if (!opponentOptions.some(option => option.key === opponent)) {
      setOpponent(opponentOptions[0]?.key || '');
    }
  }, [opponent, opponentOptions]);

  const selectedOpponent = opponentOptions.find(option => option.key === opponent);

  const filteredGames = useMemo(
    () => games.filter(game =>
      game.llm_player === llm && selectedOpponent?.players.includes(game.katago_player)),
    [games, llm, selectedOpponent],
  );

  useEffect(() => {
    if (!filteredGames.some(game => game.id === gameId)) {
      setGameId(filteredGames[0]?.id || '');
    }
  }, [filteredGames, gameId]);

  const selectedGame = filteredGames.find(game => game.id === gameId) || filteredGames[0];

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
  const isAtEnd = moveCount >= selectedGame.moves.length;
  const visibleMoves = selectedGame.moves.slice(Math.max(0, moveCount - 8), moveCount);
  const blackPlayerName = compactGamePlayerName(
    selectedGame.black,
    katagoPlayers,
  );
  const whitePlayerName = compactGamePlayerName(
    selectedGame.white,
    katagoPlayers,
  );

  const moveTo = nextMove => {
    setPlaying(false);
    setMoveCount(Math.max(0, Math.min(nextMove, selectedGame.moves.length)));
  };

  return (
    <section className="gobench-section" aria-labelledby="gobench-replayer-heading">
      <div className="gobench-section-header">
        <div>
          <h2 id="gobench-replayer-heading">Replay every match</h2>
        </div>
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
            {llmPlayerGroups.map(group => (
              <optgroup key={group.label} label={group.label}>
                {group.players.map(player => {
                  const rating = replayLlmRatings.get(player);
                  return (
                    <option key={player} value={player}>
                      {formatReplayPlayerOption(player, rating)}
                    </option>
                  );
                })}
              </optgroup>
            ))}
          </select>
        </label>

        <label>
          <span><b>2</b> KataGo · Elo ± 95% CI · W–L–D</span>
          <select
            value={opponent}
            onChange={event => {
              setOpponent(event.target.value);
              setGameId('');
            }}
          >
            {opponentOptions.map(option => (
              <option key={option.key} value={option.key}>
                {formatOpponentOption(option)}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span><b>3</b> Game · Result</span>
          <select value={selectedGame.id} onChange={event => setGameId(event.target.value)}>
            {filteredGames.map((game, index) => (
              <option key={game.id} value={game.id}>
                Game {index + 1} · {getOutcome(game)}
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
          <div className="gobench-playback">
            <div className="gobench-playback-buttons">
              <button type="button" onClick={() => moveTo(0)} disabled={moveCount === 0} aria-label="First move">↤</button>
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
              <button type="button" onClick={() => moveTo(selectedGame.moves.length)} disabled={moveCount === selectedGame.moves.length} aria-label="Last move">↦</button>
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

          <dl className="gobench-game-meta">
            <div>
              <dt>Black</dt>
              <dd title={blackPlayerName}>
                <span className="gobench-color-chip is-black" />
                <span>{blackPlayerName}</span>
              </dd>
            </div>
            <div>
              <dt>White</dt>
              <dd title={whitePlayerName}>
                <span className="gobench-color-chip is-white" />
                <span>{whitePlayerName}</span>
              </dd>
            </div>
          </dl>

          <div className="gobench-now-playing" aria-live="polite">
            <span>{isAtEnd ? 'Game result' : 'Current move'}</span>
            <strong>
              {isAtEnd
                ? formatGameResult(selectedGame.result)
                : currentMove
                ? currentMove.number + '. ' + (currentMove.color === 'B' ? 'Black' : 'White') + ' · ' + currentMove.move
                : 'Start position'}
            </strong>
          </div>

          <div
            className="gobench-move-strip"
            data-count={visibleMoves.length}
            aria-hidden="true"
          >
            {visibleMoves.length ? visibleMoves.map(move => (
              <span key={move.number} className={move.number === currentMove?.number ? 'is-current' : undefined}>
                {move.number} {move.move}
              </span>
            )) : <span className="is-empty">No moves played</span>}
          </div>

        </div>
      </div>
      <p className="gobench-caption">
        {formatInteger(games.length)} games · {data.games.board_size}×{data.games.board_size} board · {data.games.rules} rules · {data.games.komi} komi
      </p>
    </section>
  );
};

const LoadingState = () => (
  <div className="gobench-loading" role="status">
    <span />
    <p>Loading benchmark…</p>
  </div>
);

const GoBench = ({ section = 'all' }) => {
  const { data: result, error } = useGoBenchData();
  const data = result ? filterApiData(result) : null;
  const showAll = section === 'all';
  const showStatus = showAll || section === 'api';

  if (error) {
    return showStatus
      ? <div className="gobench-error" role="alert">{error}</div>
      : null;
  }

  if (!data) {
    return showStatus ? <LoadingState /> : null;
  }

  return (
    <div className="gobench-root">
      {showAll || section === 'leaderboard' ? <Leaderboard data={data} /> : null}
      {showAll || section === 'api' ? <CostChart data={data} /> : null}
      {showAll || section === 'agentic' ? <AgenticHarnessChart data={data} /> : null}
      {showAll || section === 'replayer' ? <GameReplayer data={data} /> : null}
    </div>
  );
};

export default GoBench;
