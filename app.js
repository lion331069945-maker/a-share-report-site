const state = {
  report: null,
  stocks: [],
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

async function init() {
  const response = await fetch("./data/reports.json", { cache: "no-store" });
  const data = await response.json();
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
  setupFilters(report.stocks);
  renderStocks();
  renderArchive(data.reports);
}

init().catch((error) => {
  console.error(error);
  document.body.innerHTML = '<main class="section"><h1>数据加载失败</h1><p>请检查 data/reports.json 是否存在。</p></main>';
});
