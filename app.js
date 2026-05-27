const state = {
  report: null,
  stocks: [],
  newHighStocks: [],
  techPullbackStocks: [],
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

function uniqueNewHighSectors(stocks) {
  return [...new Set(stocks.map((stock) => stock.sector || stock.board || "").filter(Boolean))].sort(
    (a, b) => a.localeCompare(b, "zh-CN"),
  );
}

function uniqueTechPullbackCategories(stocks) {
  return [...new Set(stocks.map((stock) => stock.category || stock.sector || "").filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-CN"),
  );
}

function setupFilters(stocks) {
  const filter = el("#category-filter");
  filter.innerHTML = '<option value="">全部分类</option>';
  uniqueCategories(stocks).forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    filter.append(option);
  });

  el("#search").addEventListener("input", renderStocks);
  filter.addEventListener("change", renderStocks);
}

function setupNewHighFilters(stocks) {
  const filter = el("#new-high-filter");
  const search = el("#new-high-search");
  if (!filter || !search) return;

  filter.innerHTML = '<option value="">全部分类</option>';
  uniqueNewHighSectors(stocks).forEach((sector) => {
    const option = document.createElement("option");
    option.value = sector;
    option.textContent = sector;
    filter.append(option);
  });

  search.addEventListener("input", renderNewHighs);
  filter.addEventListener("change", renderNewHighs);
}

function setupTechPullbackFilters(stocks) {
  const filter = el("#tech-pullback-filter");
  const search = el("#tech-pullback-search");
  if (!filter || !search) return;

  filter.innerHTML = '<option value="">全部分类</option>';
  uniqueTechPullbackCategories(stocks).forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    filter.append(option);
  });

  search.addEventListener("input", renderTechPullbacks);
  filter.addEventListener("change", renderTechPullbacks);
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

function renderNewHighs() {
  const root = el("#new-high-body");
  const scope = el("#new-high-scope");
  const report = state.report || {};
  const rows = state.newHighStocks || [];
  const query = (el("#new-high-search")?.value || "").trim().toLowerCase();
  const sector = el("#new-high-filter")?.value || "";
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

  rows
    .filter((stock) => {
      const stockSector = stock.sector || stock.board || "";
      const haystack = [
        stock.code,
        stock.name,
        stock.highType || stock.type,
        stockSector,
        stock.catalyst || stock.reason,
        stock.note,
      ]
        .join(" ")
        .toLowerCase();
      return (!query || haystack.includes(query)) && (!sector || stockSector === sector);
    })
    .forEach((stock) => {
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

  if (!root.children.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 6;
    td.textContent = "没有匹配的创新高股票。";
    tr.append(td);
    root.append(tr);
  }
}

function renderTechPullbacks() {
  const root = el("#tech-pullback-body");
  const scope = el("#tech-pullback-scope");
  const report = state.report || {};
  const rows = state.techPullbackStocks || [];
  const query = (el("#tech-pullback-search")?.value || "").trim().toLowerCase();
  const category = el("#tech-pullback-filter")?.value || "";
  root.innerHTML = "";

  if (scope && report.techPullbackScope) {
    scope.textContent = report.techPullbackScope;
  }

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.textContent =
      "暂无符合条件的科技补涨股票。收盘自动化更新后，这里会按10日横盘、当日涨超5%、成交量大于前一日的口径筛选。";
    tr.append(td);
    root.append(tr);
    return;
  }

  rows
    .filter((stock) => {
      const stockCategory = stock.category || stock.sector || "";
      const haystack = [
        stock.code,
        stock.name,
        stockCategory,
        stock.sector,
        stock.catalyst,
        stock.note,
        stock.amount,
      ]
        .join(" ")
        .toLowerCase();
      return (!query || haystack.includes(query)) && (!category || stockCategory === category);
    })
    .forEach((stock) => {
      const tr = document.createElement("tr");
      [
        stock.code || "",
        stock.name || "",
        stock.category || "",
        stock.sector || "",
        stock.pct === undefined ? "" : `${Number(stock.pct).toFixed(2)}%`,
        stock.rangePct === undefined ? "" : `${Number(stock.rangePct).toFixed(2)}%`,
        stock.volumeRatio === undefined ? "" : `${Number(stock.volumeRatio).toFixed(2)}倍`,
        stock.amount || "",
        stock.catalyst || stock.reason || stock.note || "",
      ].forEach((value, index) => {
        const td = document.createElement("td");
        if (index === 1) {
          td.append(create("span", "stock-name", value));
        } else if (index === 2 && value) {
          td.append(create("span", "status", value));
        } else if (index === 4 && value) {
          td.append(create("span", "pct-up", value));
        } else {
          td.textContent = value;
        }
        tr.append(td);
      });
      root.append(tr);
    });

  if (!root.children.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.textContent = "没有匹配的科技补涨股票。";
    tr.append(td);
    root.append(tr);
  }
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

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function movingAverage(points, size) {
  if (points.length < size) return null;
  return mean(points.slice(-size).map((point) => Number(point.close)));
}

function ema(values, size) {
  if (!values.length) return [];
  const multiplier = 2 / (size + 1);
  const result = [values[0]];
  for (let index = 1; index < values.length; index += 1) {
    result.push(values[index] * multiplier + result[index - 1] * (1 - multiplier));
  }
  return result;
}

function calcMacd(points) {
  const closes = points.map((point) => Number(point.close));
  if (closes.length < 35) return null;
  const ema12 = ema(closes, 12);
  const ema26 = ema(closes, 26);
  const dif = ema12.map((value, index) => value - ema26[index]);
  const dea = ema(dif, 9);
  const latestDif = dif.at(-1);
  const latestDea = dea.at(-1);
  const previousDif = dif.at(-2);
  const previousDea = dea.at(-2);
  return {
    dif: latestDif,
    dea: latestDea,
    hist: (latestDif - latestDea) * 2,
    crossUp: previousDif <= previousDea && latestDif > latestDea,
    crossDown: previousDif >= previousDea && latestDif < latestDea,
  };
}

function calcRsi(points, size = 14) {
  if (points.length <= size) return null;
  const changes = points.slice(1).map((point, index) => Number(point.close) - Number(points[index].close));
  const recent = changes.slice(-size);
  const gains = recent.map((change) => Math.max(change, 0));
  const losses = recent.map((change) => Math.abs(Math.min(change, 0)));
  const avgGain = mean(gains);
  const avgLoss = mean(losses);
  if (!avgLoss) return 100;
  return 100 - 100 / (1 + avgGain / avgLoss);
}

function calcBoll(points, size = 20) {
  if (points.length < size) return null;
  const closes = points.slice(-size).map((point) => Number(point.close));
  const mid = mean(closes);
  const variance = mean(closes.map((value) => (value - mid) ** 2));
  const deviation = Math.sqrt(variance);
  return {
    upper: mid + deviation * 2,
    mid,
    lower: mid - deviation * 2,
  };
}

function formatCompact(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function getIndicator(series) {
  const points = series.points || [];
  const latest = points.at(-1);
  if (!latest) return null;

  const ma5 = movingAverage(points, 5);
  const ma10 = movingAverage(points, 10);
  const ma20 = movingAverage(points, 20);
  const ma60 = movingAverage(points, 60);
  const macd = calcMacd(points);
  const rsi = calcRsi(points);
  const boll = calcBoll(points);
  const close = Number(latest.close);
  const recent = points.slice(-20);
  const support = Math.min(...recent.map((point) => Number(point.low)));
  const resistance = Math.max(...recent.map((point) => Number(point.high)));
  const maStack = [ma5, ma10, ma20].every(Boolean) && ma5 > ma10 && ma10 > ma20;
  const belowShort = ma5 && close < ma5;
  const aboveMid = ma20 && close >= ma20;

  let trend = "震荡";
  if (maStack && close >= ma5) trend = "多头延续";
  else if (belowShort && aboveMid) trend = "强势回踩";
  else if (ma20 && close < ma20) trend = "短线转弱";
  else if (ma5 && close >= ma5) trend = "修复中";

  let macdText = "--";
  if (macd) {
    if (macd.crossUp) macdText = "金叉";
    else if (macd.crossDown) macdText = "死叉";
    else macdText = macd.hist >= 0 ? "红柱" : "绿柱";
  }

  let rsiText = "--";
  if (rsi !== null) {
    if (rsi >= 75) rsiText = `${rsi.toFixed(1)} 超买`;
    else if (rsi <= 30) rsiText = `${rsi.toFixed(1)} 超卖`;
    else rsiText = `${rsi.toFixed(1)} 中性`;
  }

  let bollText = "--";
  if (boll) {
    if (close > boll.upper) bollText = "上轨外";
    else if (close < boll.lower) bollText = "下轨外";
    else if (close >= boll.mid) bollText = "中轨上方";
    else bollText = "中轨下方";
  }

  return {
    series,
    latest,
    close,
    ma5,
    ma10,
    ma20,
    ma60,
    macd,
    macdText,
    rsi,
    rsiText,
    boll,
    bollText,
    support,
    resistance,
    trend,
    score:
      (close >= (ma5 || close) ? 1 : 0) +
      (ma5 && ma10 && ma5 >= ma10 ? 1 : 0) +
      (ma20 && close >= ma20 ? 1 : 0) +
      (macd && macd.hist >= 0 ? 1 : 0) +
      (rsi !== null && rsi >= 45 && rsi <= 72 ? 1 : 0),
  };
}

function addInfoItem(root, label, value, tone = "") {
  const item = create("div", `strategy-item ${tone}`.trim());
  item.append(create("span", "", label));
  item.append(create("strong", "", value));
  root.append(item);
}

function addSnapshot(label, value, tone = "") {
  const card = create("article", `snapshot-card ${tone}`.trim());
  card.append(create("span", "", label));
  card.append(create("strong", "", value));
  return card;
}

function renderStrategy() {
  const report = state.report;
  const charts = state.marketCharts;
  if (!report || !charts?.series?.length) return;

  const indicators = charts.series.map(getIndicator).filter(Boolean);
  const shanghai = indicators.find((item) => item.series.id === "shanghai") || indicators[0];
  const techIndicators = indicators.filter((item) =>
    ["semiconductor", "optical_module", "fiber_optic", "chinext"].includes(item.series.id),
  );
  const avgTechScore = techIndicators.length ? mean(techIndicators.map((item) => item.score)) : shanghai.score;
  const limitUpCount = Number(report.market?.limitUpCount || state.stocks.length || 0);
  const ladderHeight = Number.parseInt(report.ladder?.[0]?.height, 10) || 0;
  const strongThemes = (report.themes || []).slice(0, 3).map((theme) => theme.name).join("、") || "暂无明确主线";
  const newHighCount = state.newHighStocks.length;
  const techPullbackCount = state.techPullbackStocks.length;

  let marketState = "震荡分歧";
  if (shanghai.series.latestPct > 0.5 && limitUpCount >= 60) marketState = "强修复";
  else if (shanghai.series.latestPct > 0 && limitUpCount >= 45) marketState = "温和修复";
  else if (shanghai.series.latestPct < -1 && limitUpCount < 50) marketState = "分歧加大";

  let sentiment = "中性";
  if (limitUpCount >= 70 || ladderHeight >= 5) sentiment = "偏强";
  else if (limitUpCount <= 35 && ladderHeight <= 2) sentiment = "偏弱";
  else if (ladderHeight >= 3) sentiment = "结构性活跃";

  let nextAction = "控制节奏，围绕前排和低位补涨做观察";
  if (marketState === "强修复") nextAction = "可跟随主线前排，低吸强趋势回踩";
  else if (marketState === "分歧加大") nextAction = "防高位补跌，等修复确认后再加仓";
  else if (avgTechScore >= 3.6) nextAction = "科技线仍可观察低位补涨和放量突破";

  text("#strategy-date", `${report.date} 盘后生成；指数数据更新于 ${charts.updatedAt}`);

  const snapshot = el("#strategy-snapshot");
  snapshot.innerHTML = "";
  snapshot.append(addSnapshot("市场状态", marketState, marketState.includes("分歧") ? "warn" : "good"));
  snapshot.append(addSnapshot("主线方向", strongThemes));
  snapshot.append(addSnapshot("技术评分", `${avgTechScore.toFixed(1)} / 5`, avgTechScore >= 3.5 ? "good" : "warn"));
  snapshot.append(addSnapshot("情绪温度", sentiment, sentiment.includes("弱") ? "warn" : "good"));
  snapshot.append(addSnapshot("次日策略", nextAction));

  const marketRoot = el("#strategy-market");
  marketRoot.innerHTML = "";
  addInfoItem(marketRoot, "指数表现", `${shanghai.series.name} ${pctText(shanghai.series.latestPct)}，收于 ${formatCompact(shanghai.close)}`, pctClass(shanghai.series.latestPct));
  addInfoItem(marketRoot, "强势板块", strongThemes);
  addInfoItem(marketRoot, "创新高样本", `${newHighCount} 只，观察资金是否继续抱团趋势股`);
  addInfoItem(marketRoot, "科技补涨", `${techPullbackCount} 只符合横盘后放量启动口径`);

  const technicalRoot = el("#strategy-technical");
  technicalRoot.innerHTML = "";
  addInfoItem(technicalRoot, "上证结构", `${shanghai.trend}，${shanghai.bollText}`);
  addInfoItem(technicalRoot, "均线状态", `MA5 ${formatCompact(shanghai.ma5)} / MA20 ${formatCompact(shanghai.ma20)}`);
  addInfoItem(technicalRoot, "动能指标", `MACD ${shanghai.macdText}，RSI ${shanghai.rsiText}`);
  addInfoItem(technicalRoot, "关键区间", `${formatCompact(shanghai.support)} - ${formatCompact(shanghai.resistance)}`);

  const sentimentRoot = el("#strategy-sentiment");
  sentimentRoot.innerHTML = "";
  addInfoItem(sentimentRoot, "涨停家数", `${limitUpCount} 只`);
  addInfoItem(sentimentRoot, "连板高度", ladderHeight ? `${ladderHeight} 板` : "--");
  addInfoItem(sentimentRoot, "龙头反馈", (report.leaders || []).slice(0, 2).map((item) => item.stocks).join("；") || "等待确认");
  addInfoItem(sentimentRoot, "情绪判断", sentiment);

  const indicatorRoot = el("#strategy-indicators");
  indicatorRoot.innerHTML = "";
  indicators.forEach((item) => {
    const tr = document.createElement("tr");
    [
      item.series.name,
      item.trend,
      `MA5 ${formatCompact(item.ma5)} / MA20 ${formatCompact(item.ma20)}`,
      item.macdText,
      item.rsiText,
      item.bollText,
      `${formatCompact(item.support)} / ${formatCompact(item.resistance)}`,
    ].forEach((value, index) => {
      const td = document.createElement("td");
      if (index === 0) td.append(create("span", "stock-name", value));
      else if (index === 1) td.append(create("span", `strategy-badge ${item.score >= 4 ? "good" : item.score <= 2 ? "warn" : ""}`.trim(), value));
      else td.textContent = value;
      tr.append(td);
    });
    indicatorRoot.append(tr);
  });

  const scenarios = [
    {
      title: "强修复",
      trigger: "指数重新站回短均线，科技主线龙头止跌反包，涨停家数继续扩张。",
      action: "关注主线核心和低位补涨，优先选择放量突破且回落承接强的标的。",
    },
    {
      title: "弱修复",
      trigger: "指数冲高回落或缩量反弹，板块内部继续分化，连板高度没有打开。",
      action: "降低追高欲望，只看前排辨识度和已通过筛选的低位科技补涨。",
    },
    {
      title: "继续分歧",
      trigger: "指数跌破关键均线，高位趋势股补跌，炸板和跌停反馈明显增加。",
      action: "以防守为主，等待情绪冰点或新主线确认后再提高仓位。",
    },
  ];
  const scenarioRoot = el("#strategy-scenarios");
  scenarioRoot.innerHTML = "";
  scenarios.forEach((scenario) => {
    const card = create("article", "scenario-card");
    card.append(create("strong", "", scenario.title));
    card.append(create("p", "", `触发：${scenario.trigger}`));
    card.append(create("p", "", `应对：${scenario.action}`));
    scenarioRoot.append(card);
  });
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
  state.newHighStocks = report.newHighStocks || report.newHighs || [];
  state.techPullbackStocks = report.techPullbackStocks || [];

  setHero(report, data.updatedAt);
  renderSummary(report);
  renderThemes(report);
  renderLadder(report);
  renderLeaders(report);
  renderSpecials(report);
  renderStats(report);
  setupNewHighFilters(state.newHighStocks);
  renderNewHighs();
  setupTechPullbackFilters(state.techPullbackStocks);
  renderTechPullbacks();
  setupFilters(report.stocks);
  renderStocks();
  renderArchive(data.reports);
  renderMarketCharts();
  renderStrategy();
}

init().catch((error) => {
  console.error(error);
  document.body.innerHTML = '<main class="section"><h1>数据加载失败</h1><p>请检查 data/reports.json 是否存在。</p></main>';
});
