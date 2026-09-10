const fs = require('fs');
const path = require('path');
const supplement = require('../public/data/goplay_players.json');
const base = require('../public/data/gobench_data/results.json');
const catalog = require('../data/goplay_catalog.json');

// Keep the approved opponent selection explicit and GoBench's ratings
// authoritative. Temperature variants share one physical network file.
const ratings = new Map([
  ...supplement.players,
  ...base.datasets.katago_players,
].map(player => [player.player, player]));
const rawBase = 'https://raw.githubusercontent.com/RolandGao/rolandgao.github.io/main/networks/goplay';
const networks = {};
for (const [name, network] of Object.entries(catalog.networks)) {
  if (!new RegExp(`^${name}\\.(txt|bin)\\.gz$`).test(network.file)) {
    throw new Error(`Invalid network filename: ${network.file}`);
  }
  const file = path.join(__dirname, '../networks/goplay', network.file);
  const bytes = fs.statSync(file).size;
  if (bytes !== network.size_bytes || bytes > catalog.max_network_bytes) {
    throw new Error(`Network size does not match the catalog or exceeds 100 MB: ${name}`);
  }
  networks[name] = {
    file: network.file,
    url: `${rawBase}/${network.file}`,
    size_bytes: bytes,
  };
}

if (new Set(catalog.players).size !== catalog.players.length) {
  throw new Error('The GoPlay catalog contains duplicate opponents');
}
const players = catalog.players.map(name => {
  const rating = ratings.get(name);
  const network = name.replace(/-temp-(\d+(?:\.\d+)?)$/, '');
  if (!rating || !Number.isFinite(rating.elo) || !networks[network]) {
    throw new Error(`Missing rating or network for GoPlay opponent: ${name}`);
  }
  const { player, elo, elo_ci_95 } = rating;
  return { player, elo, elo_ci_95 };
}).sort((left, right) => left.elo - right.elo);

if (players.at(-1)?.player !== catalog.strongest_player) {
  throw new Error('The approved strongest GoPlay opponent must be last');
}
players.forEach((player, index) => {
  if (index > 0 && player.player !== catalog.strongest_player
      && player.elo - players[index - 1].elo < catalog.min_elo_gap) {
    throw new Error(`GoPlay ratings changed: review the 50-Elo spacing near ${player.player}`);
  }
});

fs.writeFileSync(
  path.join(__dirname, '../public/data/goplay_opponents.json'),
  `${JSON.stringify({
    schema_version: 2,
    source: 'Approved selection from data/goplay_catalog.json, with GoBench ratings and shared GitHub-hosted weights',
    networks,
    players,
  }, null, 2)}\n`,
);
