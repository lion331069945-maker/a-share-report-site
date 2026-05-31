function agentTone(score) {
  if (score >= 70) return "good";
  if (score <= 42) return "bad";
  return "warn";
}

function injectAgentDeskStyles() {
  if (document.getElementById("agent-desk-style")) return;
  const style = document.createElement("style");
  style.id = "agent-desk-style";
  style.textContent = `
    .agent-desk-section { margin-top: 18px; }
    .agent-consensus {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .agent-consensus-card,
    .agent-card,
    .agent-playbook-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .agent-consensus-card {
      min-height: 112px;
      padding: 14px;
    }
    .agent-consensus-card.good,
    .agent-card.good {
      border-color: #99d5bf;
      background: #f1fbf6;
    }
    .agent-consensus-card.warn,
    .agent-card.warn {
      border-color: #f1c588;
      background: #fff8ed;
    }
    .agent-consensus-card.bad,
    .agent-card.bad {
      border-color: #f2aaa5;
      background: #fff5f5;
    }
    .agent-consensus-card span,
    .agent-card-head span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }
    .agent-consensus-card strong {
      display: block;
      margin-top: 8px;
      color: var(--ink);
      font-size: 21px;
      line-height: 1.25;
    }
    .agent-debate-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
    }
    .agent-card {
      min-height: 190px;
      padding: 14px;
    }
    .agent-card-head {
      display: grid;
      gap: 7px;
    }
    .agent-card-head strong {
      color: var(--accent-strong);
      font-size: 16px;
      line-height: 1.35;
    }
    .agent-card p,
    .agent-playbook-card p {
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .agent-meter {
      display: block;
      height: 8px;
      margin-top: 12px;
      border-radius: 999px;
      background: #e5edf4;
      overflow: hidden;
    }
    .agent-meter span {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: var(--accent);
    }
    .agent-consensus-card.warn .agent-meter span,
    .agent-card.warn .agent-meter span {
      background: var(--warn);
    }
    .agent-consensus-card.bad .agent-meter span,
    .agent-card.bad .agent-meter span {
      background: var(--red);
    }
    .agent-playbook {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .agent-playbook-card {
      padding: 14px;
    }
    .agent-playbook-card strong {
      display: block;
      color: var(--accent-strong);
      font-size: 15px;
    }
    @media (max-width: 980px) {
      .agent-consensus,
      .agent-debate-grid,
      .agent-playbook {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 640px) {
      .agent-consensus,
      .agent-debate-grid,
      .agent-playbook {
        grid-template-columns: 1fr;
      }
    }
  `;
  document.head.append(style);
}

function agentVerdict(score, riskScore) {
  if (riskScore >= 72) return "防守等待";
  if (score >= 72) return "顺势进攻";
  if (score >= 58) return "控仓跟随";
  if (score >= 45) return "低吸观察";
  return "暂缓出手";
}

function calcAgentRiskScore(sentiment, indicators, themeRows) {
  const shanghai = indicators.find((item) => item.series.id === "shanghai") || indicators[0];
  const trendPenalty = shanghai?.score <= 2 ? 18 : shanghai?.score >= 4 ? 0 : 8;
  const reopenPenalty = clamp(sentiment.reopenRate * 0.55, 0, 26);
  const heightPenalty = sentiment.ladderHeight >= 5 ? 14 : sentiment.ladderHeight <= 2 ? 6 : 10;
  const concentration = themeRows[0]?.score >= 78 ? 10 : 4;
  const weakBreadth = sentiment.total < 40 ? 16 : sentiment.total < 55 ? 8 : 0;
  return Math.round(clamp(trendPenalty + reopenPenalty + heightPenalty + concentration + weakBreadth, 0, 100));
}

function buildAgentDesk(report) {
  const charts = state.marketCharts;
  if (!report || !charts?.series?.length) return null;

  const sentiment = buildSentiment(report);
  const themeRows = buildThemeStrength(report);
  const indicators = charts.series.map(getIndicator).filter(Boolean);
  const shanghai = indicators.find((item) => item.series.id === "shanghai") || indicators[0];
  const techIndicators = indicators.filter((item) =>
    ["semiconductor", "optical_module", "fiber_optic", "chinext"].includes(item.series.id),
  );
  const avgTechScore = techIndicators.length ? mean(techIndicators.map((item) => item.score)) : shanghai?.score || 0;
  const topTheme = themeRows[0];
  const watchRows = state.watchPoolStocks || [];
  const focusRows = watchRows.filter((row) => row.level === "重点观察").slice(0, 5);
  const waitRows = watchRows.filter((row) => row.level === "等确认").slice(0, 4);
  const riskRows = watchRows.filter((row) => ["只看不追", "剔除观察"].includes(row.level)).slice(0, 4);
  const riskScore = calcAgentRiskScore(sentiment, indicators, themeRows);
  const marketScore = shanghai ? Math.round((shanghai.score / 5) * 100) : 50;
  const themeScore = topTheme?.score || 0;
  const actionScore = Math.round(
    clamp(sentiment.score * 0.28 + marketScore * 0.22 + themeScore * 0.25 + avgTechScore * 20 * 0.15 + (100 - riskScore) * 0.1, 0, 100),
  );
  const verdict = agentVerdict(actionScore, riskScore);
  const topThemeName = topTheme?.theme?.name || "暂无明确主线";
  const topLeader = stockLabel(topTheme?.leader);
  const topMiddle = stockLabel(topTheme?.middle);
  const candidateText = formatStockList(focusRows.length ? focusRows : waitRows, 5);

  return {
    report,
    themeRows,
    riskScore,
    actionScore,
    verdict,
    topThemeName,
    focusRows,
    waitRows,
    agents: [
      {
        role: "市场分析师",
        score: marketScore,
        stance: shanghai?.trend || "震荡",
        view: shanghai
          ? `${shanghai.series.name} ${pctText(shanghai.series.latestPct)}，技术结构为${shanghai.trend}，关键区间 ${formatCompact(shanghai.support)} / ${formatCompact(shanghai.resistance)}。`
          : "指数数据不足，先按震荡处理。",
      },
      {
        role: "主线分析师",
        score: themeScore,
        stance: topThemeName,
        view: `${topThemeName} 强度 ${themeScore} 分，龙头 ${topLeader}，中军 ${topMiddle}，观察板块内部是否继续扩容。`,
      },
      {
        role: "情绪分析师",
        score: sentiment.score,
        stance: sentiment.label,
        view: `涨停 ${sentiment.total} 只，最高 ${sentiment.ladderHeight || "--"} 板，回封压力 ${sentiment.reopenedStocks} 只，情绪定性为${sentiment.label}。`,
      },
      {
        role: "风控经理",
        score: 100 - riskScore,
        stance: riskLevel(riskScore),
        view: `风险温度 ${riskScore}/100，重点盯高标负反馈、回封压力和后排尾盘拉板，风险未降温前不做无确认追高。`,
      },
      {
        role: "组合经理",
        score: actionScore,
        stance: verdict,
        view: `${verdict}，候选优先级看 ${candidateText}；若指数跌破关键支撑或核心标的开盘负反馈，则自动降一档执行。`,
      },
    ],
    playbook: [
      {
        label: "可进攻",
        value: `指数站稳短均线，${topThemeName} 前排继续强于后排，优先看 ${formatStockList(focusRows, 4)}。`,
      },
      {
        label: "等确认",
        value: `若竞价强但量能不足，只看 ${formatStockList(waitRows, 4)} 是否放量回封或分时承接。`,
      },
      {
        label: "降风险",
        value: riskRows.length
          ? `${formatStockList(riskRows, 4)} 属于高波动或后排样本，冲高回落、炸板不回封时剔除。`
          : "若高标低开低走、回封压力扩大或主线缩容，观察池统一降级。",
      },
    ],
  };
}

function renderAgentDesk() {
  const source = el("#agent-desk-source");
  const consensus = el("#agent-consensus");
  const debate = el("#agent-debate");
  const playbook = el("#agent-playbook");
  if (!source || !consensus || !debate || !playbook) return;

  const desk = buildAgentDesk(state.report);
  if (!desk) return;

  source.textContent = `${desk.report.date} 收盘数据，参考 TradingAgents 的分析师、研究辩论、交易员、风控和组合经理流程生成`;
  consensus.innerHTML = "";
  debate.innerHTML = "";
  playbook.innerHTML = "";

  [
    { label: "团队共识", value: desk.verdict, score: desk.actionScore, tone: agentTone(desk.actionScore) },
    { label: "风险温度", value: `${desk.riskScore}/100`, score: 100 - desk.riskScore, tone: riskTone(desk.riskScore) },
    { label: "最强主线", value: desk.topThemeName, score: desk.themeRows[0]?.score || 0, tone: agentTone(desk.themeRows[0]?.score || 0) },
    { label: "执行优先级", value: desk.focusRows.length ? "前排跟踪" : "等待确认", score: desk.focusRows.length ? 72 : 52, tone: desk.focusRows.length ? "good" : "warn" },
  ].forEach((item) => {
    const card = create("article", `agent-consensus-card ${item.tone}`.trim());
    card.append(create("span", "", item.label));
    card.append(create("strong", "", item.value));
    const meter = create("div", "agent-meter");
    const fill = create("span");
    fill.style.width = `${clamp(item.score, 0, 100)}%`;
    meter.append(fill);
    card.append(meter);
    consensus.append(card);
  });

  desk.agents.forEach((agent) => {
    const card = create("article", `agent-card ${agentTone(agent.score)}`.trim());
    const head = create("div", "agent-card-head");
    head.append(create("span", "", agent.role));
    head.append(create("strong", "", agent.stance));
    card.append(head);
    card.append(create("p", "", agent.view));
    const meter = create("div", "agent-meter");
    const fill = create("span");
    fill.style.width = `${clamp(agent.score, 0, 100)}%`;
    meter.append(fill);
    card.append(meter);
    debate.append(card);
  });

  desk.playbook.forEach((item) => {
    const card = create("article", "agent-playbook-card");
    card.append(create("strong", "", item.label));
    card.append(create("p", "", item.value));
    playbook.append(card);
  });
}

function waitForAgentDeskData() {
  if (state.report && state.marketCharts && state.watchPoolStocks?.length) {
    injectAgentDeskStyles();
    renderAgentDesk();
    return;
  }
  window.setTimeout(waitForAgentDeskData, 80);
}

waitForAgentDeskData();
