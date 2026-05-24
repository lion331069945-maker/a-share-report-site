const state = {
  report: null,
  stocks: [],
  marketCharts: null,
  activeChart: 0,
};

const el = (selector) => document.querySelector(selector);

const text = (selector, value) => {
  el(selector).textContent = value;
};

const create = (tag, className, content) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
};

const maxStat = (stats) => Math.max(...stats.map((item) => item.count), 1);

const svgNS = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const node = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function formatNumber(value) {
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function pctClass(value) {
  return value >= 0 ? "up" : "down";
}

function pctText(value) {
  return `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;
}

function setHero(report, updatedAt) {
  text("#updated", `最后更新：${updatedAt}`);
  text("#report-title", `${report.date} ${report.title}`);
  text("#report-summary", report.summary[0]);
  text("#metric-date", report.date);
  text("#metric-count", report.market.limitUpCount);
  text("#metric-high", report.ladder[0]?.height || "--");
  text("#scope", `${report.market.dataSource}；${report.market.sampleScope}`);

  const pdf = el("#pdf-link");
  pdf.href = report.pdf;
}

function renderSummary(report) {
  const root = el("#summary-list");
  root.innerHTML = "";
  report.summary.forEach((item, index) => {
    const card = create("article", "summary-card");
    card.append(create("strong", "", `结论 ${index + 1}`));
    card.append(document.createTextNode(item));
    root.append(card);
  });
}

function renderThemes(report) {
  const root = el("#theme-grid");
  root.innerHTML = "";
  report.themes.forEach((theme) => {
    const card = create("article", "theme-card");
    card.append(create("h3", "", theme.name));
    card.append(create("span", "theme-meta", `涨停数 ${theme.count}`));
    card.append(create("p", "", theme.catalyst));

    const tags = create("div", "tags");
    theme.leaders.forEach((leader) => tags.append(create("span", "tag", leader)));
    card.append(tags);
    root.append(card);
  });
}

function renderLadder(report) {
  const root = el("#ladder-body");
  root.innerHTML = "";
  report.ladder.forEach((row) => {
    const tr = document.createElement("tr");
    [row.height, row.stocks, row.theme, row.note].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    });
    root.append(tr);
  });
}

function renderLeaders(report) {
  const root = el("#leader-list");
  root.innerHTML = "";
  report.leaders.forEach((leader) => {
    const card = create("article", "leader-card");
    card.append(create("strong", "", leader.type));
    const stock = create("span", "", leader.stocks);
    card.append(stock);
    card.append(create("p", "", leader.logic));
    root.append(card);
  });
}

function renderSpecials(report) {
  const root = el("#special-list");
  root.innerHTML = "";
  (report.specials || []).forEach((special) => {
    const card = create("article", "special-card");
    card.append(create("strong", "", special.title));
    card.append(create("p", "", special.summary));
    card.append(create("p", "", `观察点：${special.watch}`));
    root.append(card);
  });
}

function renderStats(report) {
  const root = el("#stat-bars");
  root.innerHTML = "";
  const max = maxStat(report.stats);
  report.stats.forEach((item) => {
    const row = create("div", "stat-row");
    row.append(create("span", "stat-label", item.category));
    const bar = create("span", "bar");
    const fill = create("span");
    fill.style.width = `${Math.round((item.count / max) * 100)}%`;
    bar.append(fill);
    row.append(bar);
    row.append(create("strong", "", item.count));
    root.append(row);
  });
}

function uniqueCategories(stocks) {
  return [...new Set(stocks.map((stock) => stock.category))].sort((a, b) =>
    a.localeCompare(b, "zh-CN"),
  );
}

function setupFilters(stocks) {
  const filter = el("#category-filter");
  uniqueCategories(stocks).forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    filter.append(option);
  });

  el("#search").addEventListener("input", renderStocks);
  filter.addEventListener("change", renderStocks);
}

function renderStocks() {
  const query = el("#search").value.trim().toLowerCase();
  const category = el("#category-filter").value;
  const root = el("#stock-body");
  root.innerHTML = "";

  state.stocks
    .filter((stock) => {
      const haystack = [stock.code, stock.name, stock.category, stock.reason, stock.status]
        .join(" ")
        .toLowerCase();
      return (!query || haystack.includes(query)) && (!category || stock.category === category);
    })
    .forEach((stock) => {
      const tr = document.createElement("tr");

      const code = document.createElement("td");
      code.textContent = stock.code;
      tr.append(code);

      const name = document.createElement("td");
      name.append(create("span", "stock-name", stock.name));
      tr.append(name);

      const cat = document.createElement("td");
      cat.textContent = stock.category;
      tr.append(cat);

      const reason = document.createElement("td");
      reason.textContent = stock.reason;
      tr.append(reason);

      const status = document.createElement("td");
      status.append(create("span", "status", stock.status));
      tr.append(status);

      root.append(tr);
    });
}

function renderNewHighs(report) {
  const root = el("#new-high-body");
  const scope = el("#new-high-scope");
  const rows = report.newHighStocks || report.newHighs || [];
  root.innerHTML = "";

  if (scope && report.newHighScope) {
    scope.textContent = report.newHighScope;
  }

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 6;
    td.textContent = "暂无创新高数据。收盘自动化更新后，这里会列出当天收盘创新高或盘中创过新高的股票。";
    tr.append(td);
    root.append(tr);
    return;
  }

  rows.forEach((stock) => {
    const tr = document.createElement("tr");
    [
      stock.code || "",
      stock.name || "",
      stock.highType || stock.type || "",
      stock.sector || stock.board || "",
      stock.catalyst || stock.reason || "",
      stock.note || "",
    ].forEach((value, index) => {
      const td = document.createElement("td");
      if (index === 1) {
        td.append(create("span", "stock-name", value));
      } else if (index === 2 && value) {
        td.append(create("span", "status", value));
      } else {
        td.textContent = value;
      }
      tr.append(td);
    });
    root.append(tr);
  });
}

function renderArchive(reports) {
  const root = el("#archive-list");
  root.innerHTML = "";
  reports.forEach((report) => {
    const card = create("article", "archive-card");
    const link = create("a");
    link.href = report.pdf;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.append(create("strong", "", `${report.date} ${report.title}`));
    link.append(
      create(
        "p",
        "",
        `涨停 ${report.market.limitUpCount} 只；最高连板 ${report.ladder[0]?.height || "--"}；${report.summary[0]}`,
      ),
    );
    card.append(link);
    root.append(card);
  });
}

function renderChartTabs(charts) {
  const root = el("#chart-tabs");
  root.innerHTML = "";
  charts.series.forEach((series, index) => {
    const button = create("button", "chart-tab", series.name);
    button.type = "button";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", index === state.activeChart ? "true" : "false");
    button.addEventListener("click", () => {
      state.activeChart = index;
      renderMarketCharts();
    });
    root.append(button);
  });
}

function pathFromPoints(points) {
  return points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

function makeScales(points, width, height, pad) {
  const values = points.flatMap((point) => [point.close, point.high, point.low]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const gap = Math.max((max - min) * 0.08, max * 0.002);
  const yMin = min - gap;
  const yMax = max + gap;
  const xStep = points.length > 1 ? (width - pad.left - pad.right) / (points.length - 1) : 0;
  const yScale = (value) => pad.top + ((yMax - value) / (yMax - yMin)) * (height - pad.top - pad.bottom);
  const xScale = (index) => pad.left + index * xStep;
  return { yMin, yMax, xScale, yScale };
}

function nearestPoint(event, svgNode, points) {
  const rect = svgNode.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 920;
  return points.reduce((best, point, index) => {
    const distance = Math.abs(point.x - x);
    return distance < best.distance ? { point, index, distance } : best;
  }, { point: points[0], index: 0, distance: Infinity });
}

function showTooltip(event, series, point) {
  const tooltip = el("#chart-tooltip");
  const wrap = el(".chart-wrap");
  const rect = wrap.getBoundingClientRect();
  tooltip.hidden = false;
  tooltip.innerHTML = `<strong>${series.name} ${point.date}</strong><div>收盘：${formatNumber(point.close)}</div><div>涨跌幅：${pctText(point.pct)}</div>`;
  tooltip.style.left = `${event.clientX - rect.left}px`;
  tooltip.style.top = `${event.clientY - rect.top}px`;
}

function renderMarketCharts() {
  const charts = state.marketCharts;
  if (!charts?.series?.length) return;

  renderChartTabs(charts);
  text("#market-source", `${charts.source}；更新于 ${charts.updatedAt}`);

  const series = charts.series[state.activeChart];
  const points = series.points || [];
  const latest = points[points.length - 1];
  const svgNode = el("#market-chart");
  svgNode.innerHTML = "";
  if (!points.length) return;

  text("#chart-name", `${series.name}（${series.latestDate}）`);
  text("#chart-close", formatNumber(series.latestClose));
  const change = el("#chart-change");
  change.textContent = `${pctText(series.latestPct)} / 区间 ${pctText(series.rangePct)}`;
  change.className = pctClass(series.latestPct);
  text("#chart-range", `${points[0].date} 至 ${latest.date}`);

  const width = 920;
  const height = 300;
  const pad = { top: 20, right: 64, bottom: 34, left: 54 };
  const scales = makeScales(points, width, height, pad);
  const mapped = points.map((point, index) => ({
    ...point,
    x: scales.xScale(index),
    y: scales.yScale(point.close),
  }));

  [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
    const y = pad.top + ratio * (height - pad.top - pad.bottom);
    svgNode.append(svg("line", { class: "chart-grid", x1: pad.left, x2: width - pad.right, y1: y, y2: y }));
    const value = scales.yMax - ratio * (scales.yMax - scales.yMin);
    const label = svg("text", { class: "chart-label", x: width - pad.right + 8, y: y + 4 });
    label.textContent = formatNumber(value);
    svgNode.append(label);
  });

  svgNode.append(svg("line", { class: "chart-axis", x1: pad.left, x2: width - pad.right, y1: height - pad.bottom, y2: height - pad.bottom }));
  const area = `${pathFromPoints(mapped)} L${width - pad.right},${height - pad.bottom} L${pad.left},${height - pad.bottom} Z`;
  svgNode.append(svg("path", { class: "chart-area", d: area, fill: series.color }));
  svgNode.append(svg("path", { class: "chart-line", d: pathFromPoints(mapped), stroke: series.color }));

  const firstLabel = svg("text", { class: "chart-label", x: pad.left, y: height - 10 });
  firstLabel.textContent = mapped[0].date.slice(5);
  svgNode.append(firstLabel);
  const lastLabel = svg("text", { class: "chart-label", x: width - pad.right - 32, y: height - 10 });
  lastLabel.textContent = latest.date.slice(5);
  svgNode.append(lastLabel);

  const crosshair = svg("line", { class: "chart-crosshair", x1: mapped.at(-1).x, x2: mapped.at(-1).x, y1: pad.top, y2: height - pad.bottom });
  const dot = svg("circle", { class: "chart-point", cx: mapped.at(-1).x, cy: mapped.at(-1).y, r: 5, stroke: series.color });
  svgNode.append(crosshair, dot);

  const updateHover = (event) => {
    const nearest = nearestPoint(event, svgNode, mapped).point;
    crosshair.setAttribute("x1", nearest.x);
    crosshair.setAttribute("x2", nearest.x);
    dot.setAttribute("cx", nearest.x);
    dot.setAttribute("cy", nearest.y);
    showTooltip(event, series, nearest);
  };

  svgNode.onpointermove = updateHover;
  svgNode.onpointerleave = () => {
    el("#chart-tooltip").hidden = true;
    crosshair.setAttribute("x1", mapped.at(-1).x);
    crosshair.setAttribute("x2", mapped.at(-1).x);
    dot.setAttribute("cx", mapped.at(-1).x);
    dot.setAttribute("cy", mapped.at(-1).y);
  };
}

async function init() {
  const [reportResponse, chartResponse] = await Promise.all([
    fetch("./data/reports.json", { cache: "no-store" }),
    fetch("./data/market_charts.json", { cache: "no-store" }),
  ]);
  const data = await reportResponse.json();
  state.marketCharts = await chartResponse.json();
  const report = data.reports[0];
  state.report = report;
  state.stocks = report.stocks;

  setHero(report, data.updatedAt);
  renderSummary(report);
  renderThemes(report);
  renderLadder(report);
  renderLeaders(report);
  renderSpecials(report);
  renderStats(report);
  renderNewHighs(report);
  setupFilters(report.stocks);
  renderStocks();
  renderArchive(data.reports);
  renderMarketCharts();
}

init().catch((error) => {
  console.error(error);
  document.body.innerHTML = '<main class="section"><h1>数据加载失败</h1><p>请检查 data/reports.json 是否存在。</p></main>';
});
