const state = {
  report: null,
  stocks: [],
  newHighStocks: [],
  techPullbackStocks: [],
  maConvergenceStocks: [],
  watchPoolStocks: [],
  whiteHairPicks: null,
  marketCharts: null,
  dailyWatch: null,
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
  text("#scope", `更新于 ${updatedAt}`);

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

function newsCategoryTone(category) {
  if (category === "科技") return "tech";
  if (category === "政治") return "policy";
  return "finance";
}

function inferNewsCategory(textValue) {
  const value = String(textValue || "");
  if (/(科技|AI|算力|半导体|芯片|机器人|硬件|新能源|光模块)/.test(value)) return "科技";
  if (/(政策|国务院|央行|监管|政治|外交|改革|规划)/.test(value)) return "政治";
  return "财经";
}

function buildFallbackMarketNews(report) {
  return [
    {
      category: "提示",
      heat: "待补充",
      title: `${report.date || "当日"} 真实新闻尚未维护`,
      impact: "该板块只展示已核验新闻事件，不再用盘面主线归纳冒充新闻。",
      whyHot: "请在更新脚本中补充英伟达、苹果、AI、芯片、机器人、产业政策等真实事件。",
      relatedThemes: [],
      watch: "补充新闻清单后重新生成日报。",
      source: "本地新闻清单",
      url: "",
    },
  ];
}

function normalizeMarketNews(report) {
  const rows = Array.isArray(report.marketNews) && report.marketNews.length ? report.marketNews : buildFallbackMarketNews(report);
  return rows.map((item) => ({
    category: item.category || inferNewsCategory(`${item.title} ${item.impact} ${item.relatedThemes}`),
    heat: item.heat || "市场关注",
    title: item.title || item.headline || "未命名新闻",
    impact: item.impact || item.summary || "等待补充盘面影响。",
    whyHot: item.whyHot || item.reason || "",
    watch: item.watch || item.watchPoint || "",
    relatedThemes: Array.isArray(item.relatedThemes) ? item.relatedThemes : String(item.relatedThemes || "").split(/[、,，]/).filter(Boolean),
    source: item.source || "待核验",
    url: item.url || "",
  }));
}

function renderMarketNews(report) {
  const source = el("#market-news-source");
  const spotlight = el("#market-news-spotlight");
  const body = el("#market-news-body");
  if (!source || !spotlight || !body) return;

  const rows = normalizeMarketNews(report);
  source.textContent = `${report.date} 市场与科技新闻雷达，覆盖盘面主线、全球科技、AI、芯片、机器人和产业政策`;
  spotlight.innerHTML = "";
  body.innerHTML = "";

  rows.slice(0, 3).forEach((item) => {
    const card = create("article", `market-news-card ${newsCategoryTone(item.category)}`);
    const meta = create("div", "market-news-meta");
    meta.append(create("span", "", item.category));
    meta.append(create("span", "", item.heat));
    card.append(meta);
    card.append(create("strong", "", item.title));
    card.append(create("p", "", item.impact));
    if (item.whyHot) card.append(create("p", "market-news-reason", `热议原因：${item.whyHot}`));
    spotlight.append(card);
  });

  rows.forEach((item) => {
    const tr = create("tr");
    tr.append(create("td", "", item.category));
    tr.append(create("td", "", item.heat));
    tr.append(create("td", "", item.title));
    tr.append(create("td", "", item.impact));
    tr.append(create("td", "", item.relatedThemes.join("、") || "--"));
    tr.append(create("td", "", item.watch || "--"));
    const sourceCell = create("td");
    if (item.url) {
      const link = create("a", "", item.source);
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      sourceCell.append(link);
    } else {
      sourceCell.textContent = item.source;
    }
    tr.append(sourceCell);
    body.append(tr);
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function asNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseBoardHeight(value) {
  const textValue = String(value || "");
  if (textValue.includes("首")) return 1;
  const parsed = Number.parseInt(textValue, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isEarlyLimit(stock, time = "09:35:00") {
  return Boolean(stock?.firstLimitTime && stock.firstLimitTime <= time);
}

function stockLabel(stock) {
  if (!stock) return "--";
  return `${stock.name}${stock.code ? `(${stock.code})` : ""}`;
}

function formatPctRaw(value) {
  if (!Number.isFinite(value)) return "--";
  return `${value.toFixed(0)}%`;
}

function formatYiRaw(value) {
  const amount = asNumber(value);
  if (!amount) return "--";
  return `${(amount / 100000000).toFixed(1)}亿`;
}

function sentimentLabel(score) {
  if (score >= 78) return "强修复";
  if (score >= 62) return "结构性活跃";
  if (score >= 45) return "中性震荡";
  return "分歧偏弱";
}

function sentimentTone(score) {
  if (score >= 62) return "good";
  if (score < 45) return "bad";
  return "warn";
}

function buildSentiment(report) {
  const stocks = report.stocks || [];
  const total = asNumber(report.market?.limitUpCount, stocks.length);
  const ladderHeight = Math.max(
    parseBoardHeight(report.ladder?.[0]?.height),
    ...stocks.map((stock) => asNumber(stock.consecutive)),
  );
  const multiBoard = stocks.filter((stock) => asNumber(stock.consecutive) >= 2).length;
  const firstBoard = stocks.filter((stock) => asNumber(stock.consecutive) <= 1).length;
  const earlyLimit = stocks.filter((stock) => isEarlyLimit(stock)).length;
  const auctionLimit = stocks.filter((stock) => isEarlyLimit(stock, "09:25:30")).length;
  const reopenPressure = stocks.reduce((sum, stock) => sum + asNumber(stock.reopenCount), 0);
  const reopenedStocks = stocks.filter((stock) => asNumber(stock.reopenCount) > 0).length;
  const earlyRate = total ? (earlyLimit / total) * 100 : 0;
  const multiRate = total ? (multiBoard / total) * 100 : 0;
  const reopenRate = total ? (reopenedStocks / total) * 100 : 0;
  const score = Math.round(
    clamp((total / 80) * 28, 0, 28) +
      clamp((ladderHeight / 6) * 20, 0, 20) +
      clamp((multiBoard / 16) * 18, 0, 18) +
      clamp((earlyRate / 45) * 18, 0, 18) +
      clamp(((100 - reopenRate) / 100) * 16, 0, 16),
  );
  return {
    total,
    ladderHeight,
    multiBoard,
    firstBoard,
    earlyLimit,
    auctionLimit,
    reopenPressure,
    reopenedStocks,
    earlyRate,
    multiRate,
    reopenRate,
    score: clamp(score, 0, 100),
    label: sentimentLabel(score),
  };
}

function renderSentimentDashboard(report) {
  const cards = el("#sentiment-cards");
  const detail = el("#sentiment-detail");
  const source = el("#sentiment-source");
  if (!cards || !detail || !source) return;

  const sentiment = buildSentiment(report);
  source.textContent = `${report.date} 收盘数据，基于涨停池、连板天梯、首次封板时间和回封次数计算`;
  cards.innerHTML = "";
  detail.innerHTML = "";

  const items = [
    {
      label: "情绪温度",
      value: `${sentiment.score}`,
      unit: "/100",
      note: sentiment.label,
      tone: sentimentTone(sentiment.score),
      meter: sentiment.score,
    },
    {
      label: "涨停家数",
      value: sentiment.total,
      unit: "只",
      note: sentiment.total >= 60 ? "赚钱效应扩张" : sentiment.total >= 40 ? "局部活跃" : "偏弱修复",
      meter: clamp((sentiment.total / 80) * 100, 0, 100),
    },
    {
      label: "连板高度",
      value: sentiment.ladderHeight || "--",
      unit: sentiment.ladderHeight ? "板" : "",
      note: sentiment.ladderHeight >= 5 ? "高度打开" : sentiment.ladderHeight >= 3 ? "梯队可用" : "高度受限",
      meter: clamp((sentiment.ladderHeight / 6) * 100, 0, 100),
    },
    {
      label: "连板股",
      value: sentiment.multiBoard,
      unit: "只",
      note: `连板占比 ${formatPctRaw(sentiment.multiRate)}`,
      meter: clamp((sentiment.multiRate / 35) * 100, 0, 100),
    },
    {
      label: "早盘封板",
      value: sentiment.earlyLimit,
      unit: "只",
      note: `竞价封板 ${sentiment.auctionLimit} 只`,
      meter: clamp((sentiment.earlyRate / 55) * 100, 0, 100),
    },
    {
      label: "回封压力",
      value: sentiment.reopenedStocks,
      unit: "只",
      note: `合计回封 ${sentiment.reopenPressure} 次`,
      tone: sentiment.reopenRate > 35 ? "bad" : sentiment.reopenRate > 18 ? "warn" : "good",
      meter: clamp(100 - sentiment.reopenRate, 0, 100),
    },
  ];

  items.forEach((item) => {
    const card = create("article", `sentiment-card ${item.tone || ""}`.trim());
    const top = create("div", "sentiment-card-top");
    top.append(create("span", "", item.label));
    const value = create("strong");
    value.append(document.createTextNode(item.value));
    if (item.unit) value.append(create("small", "", item.unit));
    top.append(value);
    card.append(top);
    card.append(create("p", "", item.note));
    const meter = create("div", "sentiment-meter");
    const fill = create("span");
    fill.style.width = `${clamp(item.meter, 0, 100)}%`;
    meter.append(fill);
    card.append(meter);
    cards.append(card);
  });

  const structure = create("article", "sentiment-detail-card");
  structure.append(create("strong", "", "情绪结构"));
  structure.append(create("p", "", `首板 ${sentiment.firstBoard} 只，连板 ${sentiment.multiBoard} 只，最高 ${sentiment.ladderHeight || "--"} 板。`));
  structure.append(create("p", "", `早盘 9:35 前封板 ${sentiment.earlyLimit} 只，说明资金进攻节奏${sentiment.earlyRate >= 40 ? "较主动" : "偏谨慎"}。`));
  detail.append(structure);

  const action = create("article", "sentiment-detail-card");
  action.append(create("strong", "", "盘面含义"));
  const riskText =
    sentiment.reopenRate > 35
      ? "炸板/回封压力偏大，追后排需要降速。"
      : sentiment.score >= 62
        ? "情绪有承接，可以优先看主线前排和低位补涨。"
        : "情绪没有全面打开，先看辨识度和承接。";
  action.append(create("p", "", `${sentiment.label}：${riskText}`));
  action.append(create("p", "", "明日重点观察高标反馈、昨日首板晋级率，以及强主线是否继续扩容。"));
  detail.append(action);
}

function themeStocks(theme, stocks) {
  const leaders = new Set(theme.leaders || []);
  return stocks.filter((stock) => stock.theme === theme.name || leaders.has(stock.name));
}

function leaderForTheme(theme, report, stocks) {
  const explicit = (report.leaders || []).find((leader) => leader.theme === theme.name || leader.type === theme.name);
  if (explicit?.stock) {
    const matched = stocks.find((stock) => stock.name === explicit.stock || stock.code === explicit.code);
    return matched || { name: explicit.stock, code: explicit.code };
  }
  return rankStocks(stocks)[0] || null;
}

function sameStock(left, right) {
  if (!left || !right) return false;
  return Boolean((left.code && left.code === right.code) || (left.name && left.name === right.name));
}

function buildThemeStrength(report) {
  const stocks = report.stocks || [];
  return (report.themes || [])
    .map((theme) => {
      const rows = themeStocks(theme, stocks);
      const count = asNumber(theme.count, rows.length);
      const multiBoard = rows.filter((stock) => asNumber(stock.consecutive) >= 2).length;
      const maxHeight = Math.max(0, ...rows.map((stock) => asNumber(stock.consecutive)));
      const earlyLimit = rows.filter((stock) => isEarlyLimit(stock)).length;
      const reopenPressure = rows.reduce((sum, stock) => sum + asNumber(stock.reopenCount), 0);
      const amountRaw = rows.reduce((sum, stock) => sum + asNumber(stock.amountRaw), 0);
      const leader = leaderForTheme(theme, report, rows);
      const middle = rows
        .filter((stock) => !sameStock(stock, leader))
        .sort((a, b) => asNumber(b.amountRaw) - asNumber(a.amountRaw))[0];
      const supplement = rankStocks(
        rows.filter(
          (stock) =>
            asNumber(stock.consecutive) <= 1 && !sameStock(stock, leader) && !sameStock(stock, middle),
        ),
      )
        .slice(0, 2)
        .map(stockLabel)
        .join("、");
      const score = Math.round(
        clamp(count * 4.8, 0, 32) +
          clamp(multiBoard * 7, 0, 22) +
          clamp(maxHeight * 5, 0, 24) +
          clamp(earlyLimit * 2.5, 0, 12) +
          clamp(Math.log10(amountRaw / 100000000 + 1) * 8, 0, 12) -
          clamp(reopenPressure * 1.2, 0, 12),
      );
      return {
        theme,
        count,
        multiBoard,
        maxHeight,
        earlyLimit,
        amountRaw,
        leader,
        middle,
        supplement,
        score: clamp(score, 0, 100),
      };
    })
    .sort((a, b) => b.score - a.score || b.count - a.count || b.maxHeight - a.maxHeight);
}

function renderThemeStrength(report) {
  const body = el("#theme-strength-body");
  const source = el("#theme-strength-source");
  if (!body || !source) return;

  const rows = buildThemeStrength(report);
  source.textContent = `${report.date} 收盘数据，按涨停数量、连板数量、最高板、早盘封板和成交额综合打分`;
  body.innerHTML = "";

  rows.forEach((row, index) => {
    const tr = document.createElement("tr");
    const cells = [
      `#${index + 1}`,
      row.theme.name,
      "",
      `${row.count}只`,
      `${row.multiBoard}只`,
      row.maxHeight ? `${row.maxHeight}板` : "--",
      stockLabel(row.leader),
      stockLabel(row.middle),
      row.supplement || "--",
      row.theme.catalyst || "",
    ];
    cells.forEach((value, cellIndex) => {
      const td = document.createElement("td");
      if (cellIndex === 1) {
        td.append(create("span", "stock-name", value));
      } else if (cellIndex === 2) {
        const score = create("div", "theme-score");
        score.append(create("strong", "", row.score));
        const bar = create("span", "theme-score-bar");
        const fill = create("span");
        fill.style.width = `${row.score}%`;
        bar.append(fill);
        score.append(bar);
        td.append(score);
      } else if (cellIndex === 6 || cellIndex === 7) {
        td.append(create("span", "stock-name", value));
      } else {
        td.textContent = value;
      }
      tr.append(td);
    });
    body.append(tr);
  });
}

function riskLevel(score) {
  if (score >= 72) return "高风险";
  if (score >= 45) return "中风险";
  return "低风险";
}

function riskTone(score) {
  if (score >= 72) return "bad";
  if (score >= 45) return "warn";
  return "good";
}

function riskCard(root, label, value, note, tone = "") {
  const card = create("article", `risk-card ${tone}`.trim());
  card.append(create("span", "", label));
  card.append(create("strong", "", value));
  card.append(create("p", "", note));
  root.append(card);
}

function addRiskRow(root, risk, trigger, avoid, anchor, action, tone = "") {
  const tr = document.createElement("tr");
  [risk, trigger, avoid, anchor, action].forEach((value, index) => {
    const td = document.createElement("td");
    if (index === 0) td.append(create("span", `risk-badge ${tone}`.trim(), value));
    else td.textContent = value;
    tr.append(td);
  });
  root.append(tr);
}

function topThemeConcentration(report) {
  const total = asNumber(report.market?.limitUpCount, (report.stocks || []).length);
  const topCount = (report.themes || []).slice(0, 2).reduce((sum, theme) => sum + asNumber(theme.count), 0);
  return total ? (topCount / total) * 100 : 0;
}

function renderRiskWarnings(report) {
  const cards = el("#risk-warning-cards");
  const body = el("#risk-warning-body");
  const source = el("#risk-warning-source");
  if (!cards || !body || !source) return;

  const stocks = report.stocks || [];
  const sentiment = buildSentiment(report);
  const themes = buildThemeStrength(report);
  const topTheme = themes[0];
  const topLeader = topTheme?.leader;
  const topMiddle = topTheme?.middle;
  const highBoardStocks = rankStocks(stocks.filter((stock) => asNumber(stock.consecutive) >= 3));
  const highReopenStocks = stocks.filter((stock) => asNumber(stock.reopenCount) >= 2);
  const lateLimitStocks = stocks.filter((stock) => !stock.firstLimitTime || stock.firstLimitTime > "13:30:00");
  const bigAmountStocks = stocks
    .filter((stock) => asNumber(stock.amountRaw) > 0)
    .sort((a, b) => asNumber(b.amountRaw) - asNumber(a.amountRaw));
  const concentration = topThemeConcentration(report);
  const reopenRisk = sentiment.reopenRate;
  const lateRate = sentiment.total ? (lateLimitStocks.length / sentiment.total) * 100 : 0;
  const highRiskCount = highBoardStocks.length + highReopenStocks.length;
  const riskScore = Math.round(
    clamp(reopenRisk * 0.8, 0, 38) +
      clamp((highRiskCount / 12) * 22, 0, 22) +
      clamp((lateRate / 35) * 16, 0, 16) +
      clamp((sentiment.score < 55 ? 55 - sentiment.score : 0) * 0.7, 0, 18) +
      clamp((concentration > 60 ? concentration - 60 : 0) * 0.4, 0, 8),
  );
  const level = riskLevel(riskScore);

  source.textContent = `${report.date} 收盘数据，基于回封压力、高位股、尾盘封板、主线集中度和龙头/中军状态生成`;
  cards.innerHTML = "";
  body.innerHTML = "";

  riskCard(cards, "风险温度", `${riskScore}/100`, level, riskTone(riskScore));
  riskCard(
    cards,
    "回封压力",
    `${sentiment.reopenedStocks}只`,
    `炸板/回封占比 ${formatPctRaw(reopenRisk)}，合计回封 ${sentiment.reopenPressure} 次`,
    reopenRisk >= 35 ? "bad" : reopenRisk >= 20 ? "warn" : "good",
  );
  riskCard(
    cards,
    "高位压力",
    `${highBoardStocks.length}只`,
    highBoardStocks.length ? `重点看 ${formatStockList(highBoardStocks, 3)}` : "高位样本不多",
    highBoardStocks.length >= 5 ? "bad" : highBoardStocks.length >= 2 ? "warn" : "good",
  );
  riskCard(
    cards,
    "主线集中度",
    formatPctRaw(concentration),
    topTheme ? `最强主线：${topTheme.theme.name}` : "暂无明确主线",
    concentration >= 65 ? "warn" : "good",
  );
  riskCard(
    cards,
    "尾盘封板",
    `${lateLimitStocks.length}只`,
    lateLimitStocks.length ? "后排尾盘拉板，次日容易分化" : "尾盘抢筹压力不高",
    lateLimitStocks.length >= 6 ? "bad" : lateLimitStocks.length >= 3 ? "warn" : "good",
  );

  addRiskRow(
    body,
    "高位股负反馈",
    highBoardStocks.length ? `3板以上 ${highBoardStocks.length} 只，最高 ${sentiment.ladderHeight} 板` : "高位高度有限",
    "高标低开、冲高回落或炸板不回封时，不追同题材后排。",
    highBoardStocks.length ? formatStockList(highBoardStocks, 4) : "观察最高板是否继续正反馈",
    "只等核心主动回封或板块中军承接确认；高位断板日降低仓位。",
    highBoardStocks.length >= 3 ? "bad" : "warn",
  );
  addRiskRow(
    body,
    "炸板/回封压力",
    `回封股票 ${sentiment.reopenedStocks} 只，回封次数 ${sentiment.reopenPressure} 次`,
    "同一题材批量炸板、回封越来越弱时，不追午后跟风板。",
    highReopenStocks.length ? formatStockList(highReopenStocks, 4) : "观察涨停池回封次数",
    "优先看首次封板早且未炸板的前排，回封多的后排只观察。",
    reopenRisk >= 35 ? "bad" : "warn",
  );
  addRiskRow(
    body,
    "主线高潮后分歧",
    `前两大主线占涨停 ${formatPctRaw(concentration)}`,
    "主线连续扩容后，后排一字/秒板开板放量时，不追低辨识度补涨。",
    topLeader || topMiddle ? [stockLabel(topLeader), stockLabel(topMiddle)].filter(Boolean).join("、") : "观察最强主线龙头和中军",
    "只做龙头、中军或低位最先转强的补涨；后排等分歧后再看承接。",
    concentration >= 65 ? "warn" : "",
  );
  addRiskRow(
    body,
    "尾盘后排抢筹",
    lateLimitStocks.length ? `13:30 后首次封板 ${lateLimitStocks.length} 只` : "尾盘封板不多",
    "尾盘被动拉板、成交额不足、无板块联动时，次日不接高开。",
    lateLimitStocks.length ? formatStockList(rankStocks(lateLimitStocks), 4) : "观察尾盘封板次日竞价",
    "次日只有高开后不杀、10:30 前站稳分时均线，才考虑低位换手机会。",
    lateLimitStocks.length >= 6 ? "bad" : "warn",
  );
  addRiskRow(
    body,
    "中军承接失效",
    topMiddle ? `最强主线中军：${stockLabel(topMiddle)}，成交 ${formatYiRaw(topMiddle.amountRaw)}` : "中军样本不足",
    "中军放量滞涨、冲高回落或低开低走时，不追同主线小票加速。",
    bigAmountStocks.length ? formatStockList(bigAmountStocks, 4) : "观察主线容量票",
    "中军稳住且前排不炸，补涨才有持续性；中军走弱则只看不做。",
    "warn",
  );
}

function sourceText(stock) {
  return [
    stock.name,
    stock.code,
    stock.theme,
    stock.sector,
    stock.industry,
    stock.category,
    stock.type,
    stock.highType,
    stock.reason,
    stock.catalyst,
    stock.note,
  ]
    .filter(Boolean)
    .join(" ");
}

function compactText(value, max = 86) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function candidateTextPool(candidate) {
  const rows = [
    candidate.financialBrief,
    candidate.latestFinancialReport,
    candidate.earningsBrief,
    candidate.companyAction,
    candidate.latestAction,
    candidate.action,
    ...(candidate.reasons || []),
    ...(candidate.raw || []).flatMap((item) => [
      item.financialBrief,
      item.latestFinancialReport,
      item.earningsBrief,
      item.companyAction,
      item.latestAction,
      item.action,
      item.reason,
      item.catalyst,
      item.note,
      item.status,
    ]),
  ];
  return rows.filter(Boolean).map((item) => String(item).trim()).filter(Boolean);
}

function summarizeFinancialBrief(candidate) {
  const explicit = candidate.financialBrief || candidate.latestFinancialReport || candidate.earningsBrief;
  if (explicit) return compactText(explicit, 96);
  const financialKeywords = /(年报|半年报|一季报|三季报|季报|财报|业绩快报|业绩预告|营收|净利润|扣非|毛利率)/;
  const found = candidateTextPool(candidate).find((text) => financialKeywords.test(text));
  if (found) return compactText(found, 96);
  return "暂未接入最新财报摘要";
}

function summarizeCompanyAction(candidate) {
  const explicit = candidate.companyAction || candidate.latestAction || candidate.action;
  if (explicit) return compactText(explicit, 110);
  const actionKeywords = /(公告|增持|减持|回购|并购|收购|重组|定增|中标|签署|合作|投产|扩产|复牌|停牌|实控人|股权|订单|投资者关系|互动易)/;
  const found = candidateTextPool(candidate).find((text) => actionKeywords.test(text));
  return compactText(found || "暂无明确公司动作", 110);
}

function mergeWatchCandidate(map, key, patch) {
  if (!key) return;
  const current = map.get(key) || {
    code: patch.code || "",
    name: patch.name || "",
    theme: patch.theme || patch.sector || "",
    sector: patch.sector || patch.industry || "",
    tags: [],
    reasons: [],
    risks: [],
    raw: [],
  };
  current.code = current.code || patch.code || "";
  current.name = current.name || patch.name || "";
  current.theme = current.theme || patch.theme || patch.sector || current.theme;
  current.sector = current.sector || patch.sector || patch.industry || "";
  current.position = current.position || patch.position || "";
  current.amountRaw = Math.max(asNumber(current.amountRaw), asNumber(patch.amountRaw));
  current.pct = patch.pct !== undefined ? patch.pct : current.pct;
  current.consecutive = Math.max(asNumber(current.consecutive), asNumber(patch.consecutive));
  current.reopenCount = Math.max(asNumber(current.reopenCount), asNumber(patch.reopenCount));
  current.financialBrief = current.financialBrief || patch.financialBrief || patch.latestFinancialReport || patch.earningsBrief || "";
  current.companyAction = current.companyAction || patch.companyAction || patch.latestAction || patch.action || "";
  (patch.tags || []).forEach((tag) => {
    if (tag && !current.tags.includes(tag)) current.tags.push(tag);
  });
  (patch.reasons || []).forEach((reason) => {
    if (reason && !current.reasons.includes(reason)) current.reasons.push(reason);
  });
  (patch.risks || []).forEach((risk) => {
    if (risk && !current.risks.includes(risk)) current.risks.push(risk);
  });
  if (patch.raw) current.raw.push(patch.raw);
  map.set(key, current);
}

function bestThemeForStock(stock, themeRows) {
  const haystack = sourceText(stock);
  return themeRows.find((row) => haystack.includes(row.theme.name)) || null;
}

function candidateRole(candidate, themeRows) {
  const row = themeRows.find((item) => item.theme.name === candidate.theme || item.theme.name === candidate.sector);
  if (row?.leader && sameStock(candidate, row.leader)) return "龙头";
  if (row?.middle && sameStock(candidate, row.middle)) return "中军";
  if (row?.supplement && candidate.name && row.supplement.includes(candidate.name)) return "补涨";
  if (candidate.consecutive >= 3) return "高标";
  if (candidate.tags.includes("强主线")) return "主线跟随";
  return candidate.position || "观察";
}

function scoreWatchCandidate(candidate, themeRows, sentiment) {
  const themeRow = themeRows.find((item) => item.theme.name === candidate.theme || item.theme.name === candidate.sector);
  const role = candidateRole(candidate, themeRows);
  let score = 36;
  if (themeRow) score += clamp(themeRow.score / 4, 0, 25);
  if (role === "龙头") score += 18;
  else if (role === "中军") score += 14;
  else if (role === "补涨") score += 12;
  else if (role === "高标") score += 8;
  if (candidate.tags.includes("创新高")) score += 8;
  if (candidate.tags.includes("均线黏合")) score += 8;
  if (candidate.tags.includes("放量突破")) score += 10;
  if (candidate.tags.includes("科技补涨")) score += 10;
  if (candidate.tags.includes("竞价封板")) score += 8;
  if (asNumber(candidate.amountRaw) >= 1000000000) score += 5;
  if (asNumber(candidate.reopenCount) >= 2) score -= 12;
  if (asNumber(candidate.consecutive) >= 4) score -= 8;
  if (candidate.tags.includes("尾盘封板")) score -= 10;
  if (sentiment.reopenRate >= 35 && role !== "龙头" && role !== "中军") score -= 6;
  return clamp(Math.round(score), 0, 100);
}

function watchLevel(score, candidate) {
  if (candidate.risks.length >= 2 || (score < 50 && candidate.tags.includes("尾盘封板"))) return "只看不追";
  if (candidate.risks.length >= 1 && score < 85) return "等确认";
  if (score >= 78) return "重点观察";
  if (score >= 62) return "等确认";
  if (score >= 48) return "只看不追";
  return "剔除观察";
}

function buildWatchPool(report) {
  const map = new Map();
  const stocks = report.stocks || [];
  const themeRows = buildThemeStrength(report);
  const sentiment = buildSentiment(report);

  stocks.forEach((stock) => {
    const themeRow = bestThemeForStock(stock, themeRows);
    const tags = [];
    const risks = [];
    if (themeRow) tags.push("强主线");
    if (asNumber(stock.consecutive) >= 2) tags.push(`${asNumber(stock.consecutive)}连板`);
    if (isEarlyLimit(stock)) tags.push("早盘封板");
    if (isEarlyLimit(stock, "09:25:30")) tags.push("竞价封板");
    if (asNumber(stock.reopenCount) >= 2) risks.push("回封次数偏多");
    if (stock.firstLimitTime && stock.firstLimitTime > "13:30:00") {
      tags.push("尾盘封板");
      risks.push("尾盘后排");
    }
    mergeWatchCandidate(map, stock.code || stock.name, {
      ...stock,
      theme: stock.theme || themeRow?.theme.name || "",
      position: candidateRole({ ...stock, theme: stock.theme || themeRow?.theme.name || "", tags }, themeRows),
      tags,
      reasons: [stock.reason || stock.status],
      risks,
      raw: stock,
    });
  });

  (report.newHighStocks || report.newHighs || []).forEach((stock) => {
    const themeRow = bestThemeForStock(stock, themeRows);
    mergeWatchCandidate(map, stock.code || stock.name, {
      ...stock,
      theme: themeRow?.theme.name || stock.sector || "",
      sector: stock.sector || "",
      tags: ["创新高"],
      reasons: [stock.catalyst || stock.note || stock.highType],
      risks: [],
      raw: stock,
    });
  });

  (report.techPullbackStocks || []).forEach((stock) => {
    const themeRow = bestThemeForStock(stock, themeRows);
    mergeWatchCandidate(map, stock.code || stock.name, {
      ...stock,
      theme: themeRow?.theme.name || stock.category || stock.sector || "",
      sector: stock.sector || stock.category || "",
      tags: ["科技补涨", "放量启动"],
      reasons: [stock.catalyst || stock.reason || stock.note],
      risks: [],
      raw: stock,
    });
  });

  (report.maConvergenceStocks || []).forEach((stock) => {
    const type = stock.type || "";
    const themeRow = bestThemeForStock(stock, themeRows);
    const tags = ["均线黏合"];
    if (type.includes("放量")) tags.push("放量突破");
    if (type.includes("多头")) tags.push("多头发散");
    mergeWatchCandidate(map, stock.code || stock.name, {
      ...stock,
      theme: themeRow?.theme.name || stock.sector || "",
      sector: stock.sector || "",
      tags,
      reasons: [stock.note || type],
      risks: [],
      raw: stock,
    });
  });

  themeRows.slice(0, 5).forEach((row) => {
    [row.leader, row.middle]
      .filter(Boolean)
      .forEach((stock) => {
        mergeWatchCandidate(map, stock.code || stock.name, {
          ...stock,
          theme: row.theme.name,
          tags: ["强主线"],
          reasons: [`${row.theme.name} 强度 ${row.score} 分`],
          risks: [],
          raw: stock,
        });
      });
  });

  return [...map.values()]
    .map((candidate) => {
      const score = scoreWatchCandidate(candidate, themeRows, sentiment);
      const role = candidateRole(candidate, themeRows);
      const level = watchLevel(score, candidate);
      return { ...candidate, score, role, level };
    })
    .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, "zh-CN"))
    .slice(0, 80);
}

function uniqueWatchLevels(rows) {
  const order = ["重点观察", "等确认", "只看不追", "剔除观察"];
  return order.filter((level) => rows.some((row) => row.level === level));
}

function setupWatchPoolFilters(rows) {
  const filter = el("#watch-pool-filter");
  const search = el("#watch-pool-search");
  if (!filter || !search) return;
  filter.innerHTML = '<option value="">全部等级</option>';
  uniqueWatchLevels(rows).forEach((level) => {
    const option = document.createElement("option");
    option.value = level;
    option.textContent = level;
    filter.append(option);
  });
  search.addEventListener("input", renderWatchPool);
  filter.addEventListener("change", renderWatchPool);
}

function renderWatchPool() {
  const rows = state.watchPoolStocks || [];
  const body = el("#watch-pool-body");
  const summary = el("#watch-pool-summary");
  const source = el("#watch-pool-source");
  if (!body || !summary || !source) return;

  const query = (el("#watch-pool-search")?.value || "").trim().toLowerCase();
  const level = el("#watch-pool-filter")?.value || "";
  const counts = rows.reduce((acc, row) => {
    acc[row.level] = (acc[row.level] || 0) + 1;
    return acc;
  }, {});
  source.textContent = `${state.report?.date || "--"} 收盘数据，合并创新高、科技补涨、均线黏合、主线龙头/中军/补涨和风险锚点`;
  summary.innerHTML = "";
  ["重点观察", "等确认", "只看不追", "剔除观察"].forEach((name) => {
    const card = create("article", `watch-summary-card ${name === "重点观察" ? "good" : name === "只看不追" || name === "剔除观察" ? "warn" : ""}`.trim());
    card.append(create("span", "", name));
    card.append(create("strong", "", counts[name] || 0));
    summary.append(card);
  });

  body.innerHTML = "";
  rows
    .filter((row) => {
      const haystack = [
        row.code,
        row.name,
        row.theme,
        row.sector,
        row.role,
        row.level,
        row.tags.join(" "),
        row.reasons.join(" "),
        row.risks.join(" "),
        summarizeFinancialBrief(row),
        summarizeCompanyAction(row),
      ]
        .join(" ")
        .toLowerCase();
      return (!query || haystack.includes(query)) && (!level || row.level === level);
    })
    .forEach((row) => {
      const tr = document.createElement("tr");
      [
        row.score,
        row.level,
        row.code || "",
        row.name || "",
        row.theme || row.sector || "",
        row.role,
        row.tags.join("、"),
        row.reasons.slice(0, 2).join("；"),
        row.risks.length ? row.risks.join("；") : "暂无明显风险",
        summarizeFinancialBrief(row),
        summarizeCompanyAction(row),
      ].forEach((value, index) => {
        const td = document.createElement("td");
        if (index === 0) {
          td.append(create("span", `watch-score ${row.score >= 78 ? "good" : row.score < 50 ? "warn" : ""}`.trim(), value));
        } else if (index === 1) {
          td.append(create("span", `watch-level ${row.level === "重点观察" ? "good" : row.level === "只看不追" || row.level === "剔除观察" ? "warn" : ""}`.trim(), value));
        } else if (index === 3) {
          td.append(create("span", "stock-name", value));
        } else {
          td.textContent = value;
        }
        tr.append(td);
      });
      body.append(tr);
    });

  if (!body.children.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 11;
    td.textContent = "没有匹配的观察标的。";
    tr.append(td);
    body.append(tr);
  }
}

function normalizeWhiteHairPicks(report) {
  const source = report.whiteHairPicks || {};
  if (Array.isArray(source)) {
    return {
      title: "白毛严选",
      source: "从当天首板中按 Serenity 方法论筛出的 A 评价观察池。",
      methodology: [],
      totalFirstBoard: report.stocks?.filter((stock) => asNumber(stock.consecutive) === 1).length || 0,
      aCount: source.length,
      items: source,
    };
  }
  return {
    title: source.title || "白毛严选",
    source: source.source || "从当天首板中按 Serenity 方法论筛出的 A 评价观察池。",
    methodology: Array.isArray(source.methodology) ? source.methodology : [],
    totalFirstBoard: asNumber(source.totalFirstBoard),
    aCount: asNumber(source.aCount, (source.items || []).length),
    items: source.items || [],
  };
}

function whiteHairCard(root, label, value, note, tone = "") {
  const card = create("article", `white-hair-card ${tone}`.trim());
  card.append(create("span", "", label));
  card.append(create("strong", "", value));
  if (note) card.append(create("p", "", note));
  root.append(card);
}

function renderWhiteHairPicks(report) {
  const source = el("#white-hair-source");
  const summary = el("#white-hair-summary");
  const body = el("#white-hair-body");
  if (!source || !summary || !body) return;

  const picks = normalizeWhiteHairPicks(report);
  source.textContent = `${report.date} ${picks.source}`;
  summary.innerHTML = "";
  body.innerHTML = "";

  whiteHairCard(summary, "首板样本", `${picks.totalFirstBoard}只`, "只从当天首板里筛", "");
  whiteHairCard(summary, "A评价", `${picks.aCount}只`, "供应链/主线/封板质量共振", picks.aCount ? "good" : "warn");
  whiteHairCard(
    summary,
    "评价体系",
    "Serenity",
    picks.methodology[0] || "偏重上游瓶颈、AI/机器人/电力/材料需求和风险扣分",
  );

  picks.items.forEach((item) => {
    const tr = document.createElement("tr");
    [
      item.score,
      item.grade || "A",
      item.code || "",
      item.name || "",
      item.theme || item.category || "",
      item.category || "",
      item.firstLimitTime || "--",
      item.amount || "--",
      item.serenityAReason || item.serenityReason || item.reason || "",
      item.risk || "仍需人工核验公告、财务与次日承接",
    ].forEach((value, index) => {
      const td = document.createElement("td");
      if (index === 0) {
        td.append(create("span", "white-hair-score", value));
      } else if (index === 1) {
        td.append(create("span", "serenity-grade", value));
      } else if (index === 3) {
        td.append(create("span", "stock-name", value));
      } else {
        td.textContent = value;
      }
      tr.append(td);
    });
    body.append(tr);
  });

  if (!body.children.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 10;
    td.textContent = "当天首板里没有达到 Serenity A 评价的标的。";
    tr.append(td);
    body.append(tr);
  }
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

function uniqueMaConvergenceTypes(stocks) {
  const values = [];
  stocks.forEach((stock) => {
    String(stock.type || "")
      .split("/")
      .map((item) => item.trim())
      .filter(Boolean)
      .forEach((item) => values.push(item));
  });
  return [...new Set(values)].sort((a, b) => a.localeCompare(b, "zh-CN"));
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

function setupMaConvergenceFilters(stocks) {
  const filter = el("#ma-convergence-filter");
  const search = el("#ma-convergence-search");
  if (!filter || !search) return;

  filter.innerHTML = '<option value="">全部类型</option>';
  uniqueMaConvergenceTypes(stocks).forEach((type) => {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = type;
    filter.append(option);
  });

  search.addEventListener("input", renderMaConvergence);
  filter.addEventListener("change", renderMaConvergence);
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

function renderMaConvergence() {
  const root = el("#ma-convergence-body");
  const scope = el("#ma-convergence-scope");
  const report = state.report || {};
  const rows = state.maConvergenceStocks || [];
  const query = (el("#ma-convergence-search")?.value || "").trim().toLowerCase();
  const type = el("#ma-convergence-filter")?.value || "";
  root.innerHTML = "";

  if (scope && report.maConvergenceScope) {
    scope.textContent = report.maConvergenceScope;
  }

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 10;
    td.textContent =
      "暂无符合条件的均线黏合股票。收盘自动化更新后，这里会按5/10/15/20日均线是否落在5元价格区间内筛选。";
    tr.append(td);
    root.append(tr);
    return;
  }

  rows
    .filter((stock) => {
      const stockType = stock.type || "";
      const haystack = [
        stock.code,
        stock.name,
        stockType,
        stock.sector,
        stock.note,
        stock.amount,
      ]
        .join(" ")
        .toLowerCase();
      return (!query || haystack.includes(query)) && (!type || stockType.includes(type));
    })
    .forEach((stock) => {
      const tr = document.createElement("tr");
      [
        stock.code || "",
        stock.name || "",
        stock.type || "",
        stock.sector || "",
        stock.pct === undefined ? "" : `${Number(stock.pct).toFixed(2)}%`,
        stock.recentGainPct === undefined ? "" : `${Number(stock.recentGainPct).toFixed(2)}%`,
        stock.maRangeYuan === undefined ? "" : `${Number(stock.maRangeYuan).toFixed(2)}元`,
        stock.volumeRatio === undefined ? "" : `${Number(stock.volumeRatio).toFixed(2)}倍`,
        stock.amount || "",
        stock.note || "",
      ].forEach((value, index) => {
        const td = document.createElement("td");
        if (index === 1) {
          td.append(create("span", "stock-name", value));
        } else if (index === 2 && value) {
          td.append(create("span", "status", value));
        } else if ((index === 4 || index === 5) && value) {
          td.append(create("span", Number.parseFloat(value) >= 0 ? "pct-up" : "pct-down", value));
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
    td.colSpan = 10;
    td.textContent = "没有匹配的均线黏合股票。";
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
  text("#market-source", `更新于 ${charts.updatedAt}`);

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

function moneyText(value) {
  const number = Number(value || 0);
  if (number >= 100000000) return `${(number / 100000000).toFixed(2)}亿`;
  if (number >= 10000) return `${(number / 10000).toFixed(0)}万`;
  return `${number.toFixed(0)}`;
}

function volumeText(value) {
  const number = Number(value || 0);
  if (number >= 100000000) return `${(number / 100000000).toFixed(2)}亿股`;
  if (number >= 10000) return `${(number / 10000).toFixed(2)}万股`;
  return `${number.toFixed(0)}股`;
}

function renderDailyWatch() {
  const watch = state.dailyWatch;
  const cards = el("#daily-watch-cards");
  const forecast = el("#daily-watch-forecast");
  const body = el("#daily-watch-body");
  if (!cards || !forecast || !body) return;

  cards.innerHTML = "";
  forecast.innerHTML = "";
  body.innerHTML = "";

  if (!watch || !watch.date) {
    text("#daily-watch-source", "等待更新");
    cards.append(addSnapshot("数据状态", "尚未生成", "warn"));
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.textContent = "每日 9:30 前后云端任务会自动更新竞价一字板观察。";
    tr.append(td);
    body.append(tr);
    return;
  }

  text("#daily-watch-source", `更新于 ${watch.updatedAt || "--"}`);
  cards.append(addSnapshot("竞价一字板", `${watch.limitUpCount || 0} 只`, watch.limitUpCount >= 6 ? "good" : "warn"));
  cards.append(addSnapshot("封单总额", moneyText(watch.totalSealFund), watch.totalSealFund >= 1000000000 ? "good" : ""));
  cards.append(addSnapshot("最强方向", (watch.hotSectors || []).slice(0, 3).map((item) => `${item.name} ${item.count}`).join(" / ") || "待确认"));
  cards.append(addSnapshot("连板高度", watch.maxLadder ? `${watch.maxLadder} 板` : "--"));

  (watch.forecast || []).forEach((item) => {
    const card = create("article", "daily-forecast-card");
    card.append(create("strong", "", item.title || "盘前判断"));
    card.append(create("p", "", item.text || item));
    forecast.append(card);
  });

  const rows = watch.stocks || [];
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.textContent = "今日暂未捕捉到竞价一字板，或数据源尚未更新。";
    tr.append(td);
    body.append(tr);
    return;
  }

  rows.forEach((stock) => {
    const tr = document.createElement("tr");
    [
      stock.code,
      stock.name,
      stock.sector,
      stock.ladder ? `${stock.ladder}板` : "--",
      moneyText(stock.sealFund),
      volumeText(stock.sealVolume),
      stock.firstLimitTime || "--",
      stock.status || "竞价封板",
      stock.note || "",
    ].forEach((value, index) => {
      const td = document.createElement("td");
      if (index === 1) td.append(create("span", "stock-name", value));
      else if (index === 2 && value) td.append(create("span", "status", value));
      else td.textContent = value;
      tr.append(td);
    });
    body.append(tr);
  });
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

function splitNames(value) {
  if (Array.isArray(value)) return value.flatMap(splitNames);
  return String(value || "")
    .split(/[、，,；;\/\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function stockScore(stock) {
  const consecutive = Number(stock.consecutive || 0);
  const reopen = Number(stock.reopenCount || 0);
  const firstTime = stock.firstLimitTime || "15:00:00";
  const earlyScore = firstTime <= "09:35:00" ? 8 : firstTime <= "10:30:00" ? 5 : firstTime <= "13:30:00" ? 2 : 0;
  return consecutive * 12 + earlyScore - reopen * 2;
}

function uniqueStocks(stocks) {
  const seen = new Set();
  return stocks.filter((stock) => {
    const key = stock?.code || stock?.name;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function rankStocks(stocks) {
  return uniqueStocks(stocks.filter(Boolean)).sort((a, b) => stockScore(b) - stockScore(a));
}

function resolveStocks(names, stocks) {
  return splitNames(names)
    .map((name) => stocks.find((stock) => stock.name === name) || stocks.find((stock) => name.includes(stock.name)))
    .filter(Boolean);
}

function formatStockList(stocks, limit = 4) {
  const list = stocks.slice(0, limit).map((stock) => `${stock.name}${stock.code ? `(${stock.code})` : ""}`);
  return list.length ? list.join("、") : "等待盘中确认";
}

function pickScenarioCandidates(report) {
  const stocks = report.stocks || [];
  const themes = report.themes || [];
  const leaders = report.leaders || [];
  const techKeywords = ["AI", "科技", "电子", "半导体", "光模块", "光纤", "光芯片", "PCB", "算力", "芯片", "CPO", "存储"];
  const defenseKeywords = ["电力", "能源", "智能电网", "资源", "材料", "公用"];

  const leaderStocks = resolveStocks(leaders.slice(0, 3).map((item) => item.stocks), stocks);
  const topThemeStocks = resolveStocks(themes.slice(0, 4).flatMap((theme) => theme.leaders || []), stocks);
  const techThemeStocks = resolveStocks(
    themes
      .filter((theme) => techKeywords.some((keyword) => [theme.name, theme.catalyst, ...(theme.leaders || [])].join(" ").includes(keyword)))
      .flatMap((theme) => theme.leaders || []),
    stocks,
  );
  const techStocks = stocks.filter((stock) =>
    techKeywords.some((keyword) => [stock.name, stock.theme, stock.industry, stock.category, stock.reason, stock.status].join(" ").includes(keyword)),
  );
  const defenseStocks = stocks.filter((stock) =>
    defenseKeywords.some((keyword) => [stock.name, stock.theme, stock.industry, stock.category, stock.reason, stock.status].join(" ").includes(keyword)),
  );
  const lowPositionTech = techStocks.filter((stock) => Number(stock.consecutive || 0) <= 1);

  return {
    core: rankStocks([...leaderStocks, ...topThemeStocks]).slice(0, 5),
    techCore: rankStocks([...techThemeStocks, ...techStocks]).slice(0, 5),
    lowTech: rankStocks([...state.techPullbackStocks, ...lowPositionTech]).slice(0, 5),
    defense: rankStocks(defenseStocks).slice(0, 4),
  };
}

function addScenarioLine(card, label, value, className = "") {
  const line = create("p", className);
  line.append(create("span", "scenario-label", `${label}：`));
  line.append(document.createTextNode(value));
  card.append(line);
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
  const candidates = pickScenarioCandidates(report);
  const supportLine = shanghai.ma20 ? Math.min(shanghai.support, shanghai.ma20) : shanghai.support;
  const stopLine = supportLine * 0.995;
  const repairLine = shanghai.ma5 || shanghai.close;
  const pressureLine = Math.min(shanghai.resistance, repairLine * 1.015);

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

  text("#strategy-date", `更新于 ${charts.updatedAt}`);

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
  const detailedScenarios = [
    {
      title: "强修复",
      trigger: `上证重新站回 ${formatCompact(repairLine)} 附近的短线位，且科技主线前排止跌反包，涨停家数较今日 ${limitUpCount} 只继续扩张。`,
      focus: `优先看前排核心：${formatStockList(candidates.techCore.length ? candidates.techCore : candidates.core)}；低位补涨再看：${formatStockList(candidates.lowTech, 3)}。`,
      confirm: "候选标的次日高开后不快速回落，10:30 前维持分时均线上方，放量突破或回封强度优于后排，才算修复有效。",
      invalid: `若指数冲到 ${formatCompact(pressureLine)} 附近缩量回落，或核心标的高开低走、炸板不回封，强修复情景降级。`,
      action: "只做主动走强的前排和低位首板/趋势突破，避免追后排跟风。",
    },
    {
      title: "弱修复",
      trigger: `指数在 ${formatCompact(supportLine)} - ${formatCompact(repairLine)} 区间内震荡，涨停家数没有明显扩张，板块内部继续轮动。`,
      focus: `不追高，只观察承接更强的低位方向：${formatStockList(candidates.lowTech.length ? candidates.lowTech : candidates.core, 4)}。`,
      confirm: "候选股低开不破前日实体中位，或平开后放量站上分时均线；板块内至少有 2-3 只同方向个股同步走强。",
      invalid: `若上证跌破 ${formatCompact(supportLine)} 后无法快速收回，弱修复也按防守处理。`,
      action: "仓位放轻，优先等回踩承接，不在缩量冲高时追买。",
    },
    {
      title: "继续分歧",
      trigger: `指数有效跌破 ${formatCompact(supportLine)}，尤其盘中砸到 ${formatCompact(stopLine)} 下方还拉不回，同时高位趋势股补跌。`,
      focus: `这个情景少做进攻，防守观察：${formatStockList(candidates.defense.length ? candidates.defense : candidates.core, 4)}。`,
      confirm: "如果高标继续负反馈、炸板率上升、昨日强势股低开低走，说明退潮没有结束。",
      invalid: `若跌破后快速收回 ${formatCompact(supportLine)}，且核心标的重新回封，分歧情景才有修复机会。`,
      action: "砸穿关键位先降风险，等待情绪冰点或新主线确认后再提高仓位。",
    },
  ];
  const scenarioRoot = el("#strategy-scenarios");
  scenarioRoot.innerHTML = "";
  detailedScenarios.forEach((scenario) => {
    const card = create("article", "scenario-card");
    card.append(create("strong", "", scenario.title));
    addScenarioLine(card, "触发", scenario.trigger);
    addScenarioLine(card, "优先观察", scenario.focus);
    addScenarioLine(card, "上车确认", scenario.confirm);
    addScenarioLine(card, "失败信号", scenario.invalid, "scenario-risk");
    addScenarioLine(card, "应对", scenario.action);
    scenarioRoot.append(card);
  });
}

async function init() {
  const [reportResponse, chartResponse, dailyWatchResponse] = await Promise.all([
    fetch("./data/reports.json", { cache: "no-store" }),
    fetch("./data/market_charts.json", { cache: "no-store" }),
    fetch("./data/daily_watch.json", { cache: "no-store" }).catch(() => null),
  ]);
  const data = await reportResponse.json();
  state.marketCharts = await chartResponse.json();
  if (dailyWatchResponse?.ok) {
    state.dailyWatch = await dailyWatchResponse.json();
  }
  const report = data.reports[0];
  state.report = report;
  state.stocks = report.stocks;
  state.newHighStocks = report.newHighStocks || report.newHighs || [];
  state.techPullbackStocks = report.techPullbackStocks || [];
  state.maConvergenceStocks = report.maConvergenceStocks || [];
  state.watchPoolStocks = buildWatchPool(report);
  state.whiteHairPicks = normalizeWhiteHairPicks(report);

  setHero(report, data.updatedAt);
  renderSummary(report);
  renderSentimentDashboard(report);
  renderThemeStrength(report);
  renderRiskWarnings(report);
  setupWatchPoolFilters(state.watchPoolStocks);
  renderWatchPool();
  renderWhiteHairPicks(report);
  renderThemes(report);
  renderLadder(report);
  renderLeaders(report);
  renderSpecials(report);
  renderStats(report);
  setupNewHighFilters(state.newHighStocks);
  renderNewHighs();
  setupMaConvergenceFilters(state.maConvergenceStocks);
  renderMaConvergence();
  setupFilters(report.stocks);
  renderStocks();
  renderArchive(data.reports);
  renderMarketCharts();
  renderDailyWatch();
  renderStrategy();
  renderMarketNews(report);
}

init().catch((error) => {
  console.error(error);
  document.body.innerHTML = '<main class="section"><h1>数据加载失败</h1><p>请检查 data/reports.json 是否存在。</p></main>';
});
