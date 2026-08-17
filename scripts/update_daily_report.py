import argparse
import json
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reports.json"
CHARTS = ROOT / "data" / "market_charts.json"
CN_TZ = timezone(timedelta(hours=8))

CHART_SECIDS = {
    "shanghai": "1.000001",
    "chinext": "0.399006",
    "securities": "0.399975",
    "avg_price": "47.800005",
    "semiconductor": "90.BK0917",
    "optical_module": "90.BK1136",
    "fiber_optic": "90.BK1660",
}

SERENITY_DEMAND_THEME_SCORE = {
    "AI硬件/CPO/半导体": 22,
    "化工材料/电子化学品": 20,
    "机器人/高端制造/汽车链": 18,
    "电力能源/算力用电": 16,
    "电力设备/新能源设备": 15,
    "资源品/金属材料": 14,
    "AI应用/数据要素/服务": 10,
}

SERENITY_UPSTREAM_KEYWORDS = (
    "半导体",
    "光学光电",
    "通信设备",
    "元件",
    "电子化学",
    "金属新材",
    "小金属",
    "电池",
    "电网设备",
    "其他电源",
    "专用设备",
    "自动化设",
    "航空装备",
    "航天装备",
    "轨交设备",
)

SERENITY_WEAK_KEYWORDS = (
    "地产",
    "房地产",
    "装修建材",
    "一般零售",
    "服装家纺",
    "饰品",
    "白酒",
    "休闲食品",
)

CURATED_MARKET_NEWS_BY_DATE = {
    "2026-08-17": [
        {
            "category": "财经",
            "heat": "A股盘面 / 科技硬件",
            "title": "8月17日A股收盘：涨停池106只，AI硬件、电子化学品和机器人并列主线",
            "impact": "本地收盘样本显示，上证指数+1.41%、创业板指+3.14%、A股平均股价+2.88%；半导体指数+4.04%、光模块+4.11%、光纤通信+3.62%。涨停池106只，其中其他轮动20只、AI硬件/CPO/半导体20只、化工材料/电子化学品16只、机器人/高端制造/汽车链15只。科技硬件重新成为涨停扩散核心。",
            "whyHot": "这不是单纯指数普涨，而是AI硬件、上游材料和机器人三条供应链同时扩散；按 Serenity 框架，今天更值得看上游瓶颈、国产替代、客户验证和封板质量，而不是泛科技标签。",
            "relatedThemes": ["AI硬件/CPO/半导体", "化工材料/电子化学品", "机器人/高端制造/汽车链", "CPO/光通信"],
            "watch": "次日重点看AI硬件首板能否晋级、电子化学品是否继续扩散，以及光模块和半导体指数高开后是否还能承接；若只靠指数情绪，首板质量要降权。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "OpenAI / 英伟达 / 数据中心",
            "title": "OpenAI锁定俄亥俄20年巨型数据中心租约，英伟达参与首期芯片供应和融资支持",
            "impact": "《华尔街日报》报道，OpenAI通过SoftBank旗下SB Energy取得美国俄亥俄南部巨型AI数据中心长期租约，项目规划功率达到10吉瓦量级；英伟达将作为首个5吉瓦阶段的独家芯片供应方，并通过投资和资产价值支持帮助项目融资。",
            "whyHot": "这把AI交易从GPU订单继续推向电力、燃气机组、变压器、液冷、机柜、光互连和服务器供应链。对A股来说，映射重点不只是英伟达概念，而是能否拿到算力基建真实订单和上游瓶颈环节。",
            "relatedThemes": ["AI硬件/CPO/半导体", "AI数据中心", "电力能源/算力用电", "液冷"],
            "watch": "重点跟踪国内电源、液冷、光模块、服务器PCB和配电设备企业是否出现真实客户、合同或产能验证；没有订单兑现的纯概念要降权。",
            "source": "The Wall Street Journal",
            "url": "https://www.wsj.com/articles/openai-locks-in-lease-for-huge-data-center-in-ohio-with-backing-from-nvidia-7474bb9c",
        },
        {
            "category": "科技",
            "heat": "阿里巴巴 / AI战略",
            "title": "阿里巴巴拟至少15亿美元出售灵犀游戏，继续收缩非核心资产转向AI和电商主业",
            "impact": "《华尔街日报》报道，阿里巴巴计划以至少15亿美元出售旗下游戏业务灵犀游戏，买方为亚洲私募机构Trustar Capital；该交易被视为阿里继续削减非核心资产、集中资源投入AI和电商核心增长线的动作。",
            "whyHot": "这条新闻说明中国互联网巨头的资本开支和组织资源继续向AI倾斜。A股映射更偏云计算、数据要素、AI应用落地和国产算力生态，而不是泛游戏传媒。",
            "relatedThemes": ["AI应用/数据要素/服务", "国产算力", "云计算", "互联网平台"],
            "watch": "观察国内AI应用公司是否有付费客户、调用量和工作流闭环；只讲大厂合作但没有收入兑现的应用概念不宜高估。",
            "source": "The Wall Street Journal",
            "url": "https://www.wsj.com/tech/alibaba-to-sell-videogame-business-for-at-least-1-5-billion-8a547332",
        },
        {
            "category": "科技",
            "heat": "苹果 / 存储芯片 / 供应链安全",
            "title": "美国政府施压苹果不要采购中国存储芯片，AI内存紧缺继续外溢到消费电子",
            "impact": "《华尔街日报》报道，美国政府正敦促苹果不要采购中国存储芯片；在AI数据中心推高DRAM和NAND需求的背景下，苹果曾评估中国供应商以缓解成本压力，但该方案面临安全和产业政策阻力。",
            "whyHot": "存储短缺已经从AI服务器扩散到手机、PC和消费电子BOM。对A股来说，存储、先进封装、材料、设备和国产替代链条都会被反复定价，但需要区分真正产能和客户认证。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片", "消费电子/家居方向", "半导体材料"],
            "watch": "跟踪国内存储链是否有涨价传导、订单和良率改善；被美国政策限制的环节同时要考虑出口、客户和供应链替代风险。",
            "source": "The Wall Street Journal",
            "url": "https://www.wsj.com/tech/apple-china-memory-chip-plan-57773a83",
        },
        {
            "category": "科技",
            "heat": "中芯国际 / 华虹 / 成熟制程",
            "title": "中芯国际和华虹业绩走强，成熟制程晶圆涨价成为半导体链新催化",
            "impact": "《华尔街日报》Market Talk称，中芯国际和华虹半导体业绩表现强劲，花旗提到成熟制程芯片需求上升和晶圆涨价，并上调相关目标价。",
            "whyHot": "今天A股半导体和电子化学品走强，与成熟制程景气、国产替代和材料设备卡位能够形成共振。Serenity式判断要看谁处在不可绕开的上游环节，而不是所有芯片股一起拔估值。",
            "relatedThemes": ["AI硬件/CPO/半导体", "半导体设备", "化工材料/电子化学品", "晶圆制造"],
            "watch": "优先验证晶圆厂扩产、耗材涨价、设备交付和国产替代订单；若只是跟随指数补涨，持续性要打折。",
            "source": "The Wall Street Journal Market Talk",
            "url": "https://www.wsj.com/business/tech-media-telecom-roundup-market-talk-56efa474",
        },
        {
            "category": "科技",
            "heat": "液冷 / AI服务器",
            "title": "AI芯片功耗推动液冷渗透率上行，2027年液冷采用率预期升至60%",
            "impact": "《华尔街日报》Market Talk援引行业观点称，随着英伟达、AMD和Google下一代硬件拉高功耗，AI芯片液冷采用率预计到2027年达到60%。",
            "whyHot": "AI数据中心瓶颈从芯片延伸到散热、电源和机房工程，液冷不再只是题材，而是高功率机柜的工程前提。A股液冷、泵阀、冷板、CDU和服务器电源链条因此继续有事件催化。",
            "relatedThemes": ["液冷", "AI数据中心", "电力设备/新能源设备", "AI硬件/CPO/半导体"],
            "watch": "看订单是否来自真实云厂商或服务器厂，是否有批量交付和毛利率稳定；蹭液冷标签但没有认证和产能的个股要谨慎。",
            "source": "The Wall Street Journal Market Talk",
            "url": "https://www.wsj.com/business/tech-media-telecom-roundup-market-talk-56efa474",
        },
        {
            "category": "科技",
            "heat": "AI制造 / 洁净室",
            "title": "AI制造需求带动洁净室和半导体设备配套，UMS Integration与Riverstone被看好",
            "impact": "《华尔街日报》Market Talk提到，UMS Integration受益于AI相关制造需求和新客户收入增长，Riverstone Holdings则受益于洁净室业务增长和产品升级。",
            "whyHot": "这条线对应A股的半导体设备、洁净室工程、工业耗材和先进制造配套。AI扩产不只买芯片，也会拉动厂房、洁净室、检测、耗材和自动化设备需求。",
            "relatedThemes": ["半导体设备", "化工材料/电子化学品", "机器人/高端制造/汽车链", "洁净室工程"],
            "watch": "优先看有晶圆厂、封测厂或AI服务器供应链客户的公司；工程类订单要关注回款周期和毛利率，不能只看中标金额。",
            "source": "The Wall Street Journal Market Talk",
            "url": "https://www.wsj.com/business/tech-media-telecom-roundup-market-talk-56efa474",
        },
        {
            "category": "科技",
            "heat": "AI存储 / 供需瓶颈",
            "title": "AI内存短缺继续压制PC和手机BOM，IDC提示AI PC叙事可能受DRAM成本拖累",
            "impact": "IDC对2026年内存短缺的分析指出，DRAM和NAND供需紧张会推高PC和手机成本，AI PC因为内存规格更高，可能面临更明显的价格、利润率和出货压力。",
            "whyHot": "AI算力扩张正在占用存储供给，消费电子和AI PC反而承受BOM压力。对A股来说，存储涨价链有景气弹性，但终端整机和低端消费电子可能被成本挤压。",
            "relatedThemes": ["存储芯片", "AI PC", "消费电子/家居方向", "AI硬件/CPO/半导体"],
            "watch": "做多存储链时要分清上游涨价受益与下游成本受损；验证指标包括DRAM/NAND现货价、合同价、库存天数和终端厂商调价。",
            "source": "IDC",
            "url": "https://www.idc.com/resource-center/blog/global-memory-shortage-crisis-market-analysis-and-the-potential-impact-on-the-smartphone-and-pc-markets-in-2026/",
        },
    ],
    "2026-07-15": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "7月15日A股收盘：券商逆势走强，科技硬件继续承压，涨停池72只",
            "impact": "本地收盘样本显示，上证指数-0.29%、创业板指-1.21%、A股平均股价-1.82%，证券指数+2.47%；涨停池72只，其中其他轮动36只、消费零售9只、电子化学品5只居前，AI硬件/CPO/半导体未进入涨停主线前列。",
            "whyHot": "半导体指数-3.89%、光模块-3.78%、光纤通信-2.61%，说明硬件链仍处于退潮和分化阶段；资金一边做券商情绪修复，一边在低位消费、材料和事件驱动票里寻找活口。",
            "relatedThemes": ["券商金融", "消费零售/家居服饰", "化工材料/电子化学品", "AI硬件/CPO/半导体"],
            "watch": "次日重点看券商能否继续放量承接，以及科技硬件是否止跌回封；若硬件链继续弱于指数，白毛严选要继续压缩到真正有上游瓶颈和封板质量的少数个股。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "英伟达 / 中国AI芯片",
            "title": "英伟达有限恢复H200对华出货，Vera Rubin已进入生产阶段",
            "impact": "Investor's Business Daily报道，英伟达已开始向部分中国客户有限出货H200，同时Jensen Huang确认下一代Vera Rubin系统已进入生产，市场仍关注AI数据中心需求强度。",
            "whyHot": "这会同时牵动国产算力替代和海外芯片供应链：短期缓解部分中国AI算力供给，长期仍取决于出口许可、客户名单和替代生态成熟度。",
            "relatedThemes": ["AI硬件/CPO/半导体", "国产算力", "服务器", "CPO/光通信"],
            "watch": "A股映射不要只看英伟达单一新闻，重点跟踪国产算力出货、服务器订单、光互连需求和政策边际变化。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/news/technology/nvidia-stock-nears-buy-point-on-these-positive-signs/",
        },
        {
            "category": "科技",
            "heat": "AI数据中心 / 监管约束",
            "title": "纽约州发布大型AI数据中心一年暂停令，电力和水资源约束成为AI基建新瓶颈",
            "impact": "Business Insider、Barron's和FT报道，纽约州对50MW以上大型AI数据中心实施一年暂停令，原因包括电力、水资源、环境影响和居民公用事业成本压力。",
            "whyHot": "AI基建不再只看GPU采购，电力接入、地方审批、社区阻力和水资源也会成为瓶颈。对A股来说，电力设备、液冷、储能和自备电源链条仍是算力建设的重要外溢方向。",
            "relatedThemes": ["AI数据中心", "电力能源/算力用电", "液冷", "电力设备/新能源设备"],
            "watch": "关注国内项目是否具备接电、能评、土地和冷却条件；规划金额不能直接等同收入兑现。",
            "source": "Business Insider / Financial Times / Barron's",
            "url": "https://www.businessinsider.com/new-york-state-ai-data-center-moratorium-temporary-ban-2026-7",
        },
        {
            "category": "科技",
            "heat": "AI供电 / BYOP",
            "title": "Chevron与Microsoft推进AI数据中心供电项目，油气巨头进入算力电力生意",
            "impact": "Investor's Business Daily报道，Chevron、Microsoft和Engine No.1合作推进Project Kilby，以天然气和GE Vernova燃机为AI数据中心提供现场供电。",
            "whyHot": "这代表Bring Your Own Power模式升温，算力项目开始绕开电网接入瓶颈，自备电源、燃机、储能、变压器和液冷会成为AI基础设施的新交易方向。",
            "relatedThemes": ["电力能源/算力用电", "AI数据中心", "电力设备/新能源设备", "液冷"],
            "watch": "A股映射重点看真实订单和交付能力，尤其是变压器、配电、燃机配套、储能和液冷公司。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/research/industry-snapshot/chevron-entered-ai-power-business-microsoft-data-centers/",
        },
        {
            "category": "科技",
            "heat": "OpenAI硬件 / 法律风险",
            "title": "Apple起诉OpenAI涉商业秘密，OpenAI消费硬件计划可能被诉讼拖慢",
            "impact": "Axios报道，Apple对OpenAI提起商业秘密诉讼，可能影响OpenAI此前围绕Io收购推进的消费硬件计划。",
            "whyHot": "AI硬件从软件服务走向终端设备时，专利、人才流动、供应链和商业秘密都会成为不确定性；这会影响消费电子与AI终端映射的节奏。",
            "relatedThemes": ["消费电子/家居方向", "AI应用/数据要素/服务", "AI硬件/CPO/半导体", "端侧AI"],
            "watch": "A股消费电子映射要看确定订单、客户关系和量产节点，不能只用OpenAI硬件想象空间定价。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/07/14/litigation-openai-device-apple",
        },
        {
            "category": "财经",
            "heat": "金融股 / 风险偏好",
            "title": "美国大型金融机构财报带动金融股走强，国内券商逆势活跃形成情绪映射",
            "impact": "Barron's报道，高盛等美国大型金融机构因交易收入和财报表现走强，成为当天美股市场重要解释变量；A股今天证券指数也逆势上涨2.47%。",
            "whyHot": "当科技硬件回调时，券商和金融股走强往往承担市场风险偏好修复角色，但持续性需要成交量和指数共振验证。",
            "relatedThemes": ["券商金融", "其他轮动", "指数修复"],
            "watch": "次日观察券商是否放量、是否带动指数反包；如果只是一日护盘，题材股承接仍会偏弱。",
            "source": "Barron's",
            "url": "https://www.barrons.com/articles/stock-movers-70f9e550",
        },
        {
            "category": "科技",
            "heat": "国产AI芯片 / 工程约束",
            "title": "华为Ascend平台大模型推理研究提示，国产算力替代仍有工程适配成本",
            "impact": "近期arXiv研究基于华为Ascend 910部署MoE和多模态推理工作负载，指出迁移到非GPU加速器需要处理算子支持、并行稳定性、数值正确性、图编译和可观测性等问题。",
            "whyHot": "这不否定国产算力替代，但提示替代不是简单换芯片，生态、编译器、推理框架和运维工具同样是瓶颈。",
            "relatedThemes": ["国产算力", "AI硬件/CPO/半导体", "AI应用/数据要素/服务", "服务器"],
            "watch": "看真实部署、软件栈兼容、客户迁移成本和故障率，而不是只看芯片峰值算力。",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/2607.08215",
        },
        {
            "category": "科技",
            "heat": "企业AI落地",
            "title": "OpenAI收购Northslope后继续强化企业部署能力，AI应用从模型竞争转向工作流落地",
            "impact": "Axios此前报道，OpenAI的Deployment Company收购Northslope，强调帮助企业将AI应用到核心业务流程。",
            "whyHot": "AI应用行情的核心不再只是模型参数，而是数据连接、流程改造、权限治理、成本控制和可收费交付。",
            "relatedThemes": ["AI应用/数据要素/服务", "企业软件", "数据要素", "Agent"],
            "watch": "A股软件和数据要素映射要验证客户、调用量、续费和私有化部署能力；只有概念标签的公司要降权。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/07/08/openai-deployment-company-northslope-acquisition",
        },
    ],
    "2026-07-08": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "7月8日A股收盘：指数回落，AI应用/数据要素成为弱市涨停主线",
            "impact": "本地收盘样本显示，上证指数-0.49%、创业板指-1.70%、A股平均股价-1.89%，涨停池47只；AI应用/数据要素/服务13只居前，AI硬件/CPO/半导体8只，科技内部从硬件普涨转向应用与局部事件驱动。",
            "whyHot": "半导体指数-2.41%、光模块-3.17%、光纤通信-2.25%，说明前期硬件链回调压力仍在；弱市里资金更偏低位AI应用、数据要素和有事件催化的服务端标的。",
            "relatedThemes": ["AI应用/数据要素/服务", "AI硬件/CPO/半导体", "CPO/光通信", "电力设备/新能源设备"],
            "watch": "次日重点看AI应用首板能否晋级，硬件链若继续弱于指数，则白毛严选更要压缩到真正上游瓶颈、客户验证和封板质量更强的个股。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "AI应用 / 企业Agent",
            "title": "OpenAI收购Northslope，补强企业级AI工作流与数据分析落地能力",
            "impact": "SiliconANGLE报道，OpenAI收购Northslope，后者面向企业数据分析与工作流自动化，创始团队将加入OpenAI企业应用团队。",
            "whyHot": "这条新闻对应今天A股AI应用/数据要素走强：大模型公司正在从模型发布转向企业场景、数据连接、流程自动化和可收费工作流。",
            "relatedThemes": ["AI应用/数据要素/服务", "企业软件", "数据要素", "Agent"],
            "watch": "A股映射要看真实客户、调用量、私有化部署和收入兑现；没有产品落地的纯AI应用概念要降权。",
            "source": "SiliconANGLE",
            "url": "https://siliconangle.com/2026/07/08/openai-reportedly-buys-ai-startup-northslope/",
        },
        {
            "category": "科技",
            "heat": "Claude / 移动Agent",
            "title": "Anthropic推出Claude Cowork移动端版本，Agent从桌面扩展到随身协作",
            "impact": "Android Headlines报道，Anthropic发布Claude Cowork移动体验，强调持续运行、任务协作和移动端上下文接入能力。",
            "whyHot": "AI应用交易的关键正在从聊天框转向跨端Agent、任务执行和企业协作；这会利好有真实工作流、数据接口和行业客户的软件公司。",
            "relatedThemes": ["AI应用/数据要素/服务", "Agent", "办公软件", "移动应用"],
            "watch": "关注AI应用公司是否具备可复用工作流、付费转化和数据闭环；只做浅层套壳的应用弹性和持续性都要打折。",
            "source": "Android Headlines",
            "url": "https://www.androidheadlines.com/2026/07/claude-cowork-mobile-app-launch.html",
        },
        {
            "category": "科技",
            "heat": "苹果 / 定制芯片",
            "title": "苹果与Broadcom签署300亿美元芯片协议，继续强化自研硬件供应链",
            "impact": "Bloomberg报道，苹果与Broadcom达成约300亿美元芯片供应协议，涉及定制无线与连接芯片，强化其长期自研硬件和供应链控制。",
            "whyHot": "大客户通过定制芯片锁定供应链，是Serenity框架里“客户验证+长期合同+上游瓶颈”的重要信号；A股映射偏连接器、射频、PCB、封测和精密制造。",
            "relatedThemes": ["AI硬件/CPO/半导体", "消费电子/家居方向", "高速连接器", "先进封装"],
            "watch": "国内映射要核实是否进入苹果或Broadcom真实供应链，避免把所有消费电子零部件都泛化为受益。",
            "source": "Bloomberg",
            "url": "https://www.bloomberg.com/news/articles/2026-07-08/apple-and-broadcom-sign-30-billion-chip-deal",
        },
        {
            "category": "科技",
            "heat": "存储 / HBM",
            "title": "美光与存储股回撤，AI内存涨价交易进入业绩兑现与拥挤度检验期",
            "impact": "MarketWatch与Barron's近期报道指出，美光在AI存储景气中利润预期快速上行，但存储链股价也开始对高预期、扩产和估值拥挤做出反应。",
            "whyHot": "HBM和DRAM仍是AI服务器瓶颈，但市场不会无限线性外推涨价；短期缺货、客户合同、扩产节奏和估值拥挤会共同决定存储链弹性。",
            "relatedThemes": ["HBM", "存储芯片", "半导体材料", "AI硬件/CPO/半导体"],
            "watch": "A股存储链优先看订单、涨价传导和材料设备卡位；没有明确客户验证的概念股，在硬件链回调时更容易掉队。",
            "source": "MarketWatch / Barron's",
            "url": "https://www.marketwatch.com/story/micron-is-about-to-be-more-profitable-than-any-u-s-company-except-nvidia-and-google-3a83e343",
        },
        {
            "category": "科技",
            "heat": "国产AI芯片",
            "title": "英伟达中国AI芯片销售受阻，国产算力替代仍是A股硬件链观察点",
            "impact": "AP此前报道，受出口管制和本土替代推进影响，英伟达在中国AI芯片市场份额回落，华为昇腾等国产方案加速替代。",
            "whyHot": "今天AI硬件虽回调，但国产算力仍是结构性主线之一；AI芯片、服务器、交换机、PCB、电源和软件生态适配都需要真实出货验证。",
            "relatedThemes": ["国产算力", "AI硬件/CPO/半导体", "服务器", "PCB/连接器"],
            "watch": "不要只用“英伟达受限”推导所有国产芯片股上涨，重点看训练/推理部署、客户信用和供应约束。",
            "source": "Associated Press",
            "url": "https://apnews.com/article/1ae6228c4928ddbb43f984e9b38f49dd",
        },
        {
            "category": "科技",
            "heat": "AI数据中心 / 电力约束",
            "title": "AI数据中心供电架构升级继续升温，高功率机柜把电力设备推到前台",
            "impact": "近期arXiv论文讨论AI数据中心供电架构升级，指出高功率密度、电流瞬态和散热压力会推动高压DC/DC、低压直流配电和固态变压器等方案。",
            "whyHot": "AI基础设施瓶颈从GPU扩展到电力、液冷、变压器、配电和机柜级电源；这也是今天电力设备方向仍有涨停的产业解释。",
            "relatedThemes": ["AI数据中心", "电力能源/算力用电", "液冷", "电力设备/新能源设备"],
            "watch": "看项目订单、接电进度、液冷认证和交付能力，规划金额不能直接等同于收入兑现。",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/2606.25095",
        },
        {
            "category": "科技",
            "heat": "数据中心 / 外部约束",
            "title": "微软Fairwater数据中心项目遭附近居民起诉，AI基建扩张面临噪音与社区约束",
            "impact": "The Times of India报道，微软Fairwater数据中心因建设和运行噪音问题遭附近居民起诉，反映AI数据中心扩张中的环境、噪音和社区阻力。",
            "whyHot": "算力建设不是只看资本开支，电力、土地、噪音、冷却和社区审批都会影响落地节奏；A股数据中心链需要看项目兑现而非规划金额。",
            "relatedThemes": ["AI数据中心", "电力能源/算力用电", "液冷", "IDC工程"],
            "watch": "海外项目约束会让市场更重视交付能力、合规能力和本地资源绑定，纯远期规划型公司需要降权。",
            "source": "The Times of India",
            "url": "https://timesofindia.indiatimes.com/world/us/microsofts-fairwater-data-center-sued-by-residents-over-noise-what-is-the-controversy/articleshow/122316543.cms",
        },
    ],
    "2026-06-30": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月30日A股收盘：创业板与科技线大幅修复，AI硬件/CPO/半导体43只涨停",
            "impact": "本地收盘样本显示，上证指数+0.50%、创业板指+2.99%、A股平均股价+2.91%，涨停池140只；AI硬件/CPO/半导体43只、机器人/高端制造27只、电子化学品17只，是今天最强结构。",
            "whyHot": "半导体指数+4.84%、光模块+4.54%、光纤通信+3.04%，说明资金重新回到AI算力的芯片、光互连、存储、电子材料和高端制造链条。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "机器人/高端制造/汽车链", "化工材料/电子化学品"],
            "watch": "重点看43只AI硬件涨停后的晋级率，以及前排是否能换手承接；若指数继续放量，科技主线可从首板扩散到二板和趋势容量票。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "AI芯片 / 全球资金流",
            "title": "上半年AI芯片与存储股领涨全球市场，硬件瓶颈继续压过软件叙事",
            "impact": "The Guardian报道，2026年上半年芯片、存储和硬件股显著跑赢，韩国Kospi受三星与SK海力士带动大涨，美光、SanDisk、西部数据等也受AI存储需求推动。",
            "whyHot": "这对应Serenity的核心判断：AI资本开支扩张时，市场更愿意给不可替代的上游瓶颈、存储、光互连和材料环节定价。",
            "relatedThemes": ["AI硬件/CPO/半导体", "HBM", "存储芯片", "半导体材料"],
            "watch": "A股映射优先看产能稀缺、客户验证和涨价传导，不要只按AI概念标签扩散。",
            "source": "The Guardian",
            "url": "https://www.theguardian.com/business/2026/jun/29/shares-in-chipmakers-underpinning-ai-boom-surge-in-first-half-of-2026",
        },
        {
            "category": "科技",
            "heat": "韩国半导体 / HBM扩产",
            "title": "三星与SK海力士拟投入逾5200亿美元扩建韩国芯片基地，HBM供给周期成为焦点",
            "impact": "WSJ报道，三星电子与SK海力士计划在韩国新建半导体制造集群，投资规模超过5200亿美元，并配套先进封装设施，以应对AI带来的存储需求。",
            "whyHot": "短期看，HBM、DRAM和先进封装仍是AI服务器上游瓶颈；中期看，大规模扩产会让市场同时交易涨价弹性和未来供给释放。",
            "relatedThemes": ["HBM", "半导体设备", "先进封装", "半导体材料"],
            "watch": "A股材料、设备、封测方向要跟踪订单和扩产节奏；若供给释放预期升温，纯存储涨价逻辑会分化。",
            "source": "Wall Street Journal",
            "url": "https://www.wsj.com/tech/samsung-sk-hynix-to-spend-520-billion-on-chip-plants-in-south-korea-7d50aab2",
        },
        {
            "category": "科技",
            "heat": "国产AI芯片",
            "title": "AP称英伟达中国AI芯片销售受阻，华为等本土芯片厂商份额上升",
            "impact": "AP报道，受美国出口管制和本土替代推进影响，英伟达在中国AI芯片市场份额大幅回落，华为昇腾等国产方案获得更多采用。",
            "whyHot": "这条新闻直接对应国产算力链：AI芯片、服务器、交换机、电源、PCB和国产软件生态适配都会被资金重新评估。",
            "relatedThemes": ["国产算力", "AI硬件/CPO/半导体", "服务器", "PCB/连接器"],
            "watch": "重点看真实出货、训练/推理部署、生态适配和供应约束；不能只用英伟达受限来线性推导所有国产芯片股上涨。",
            "source": "Associated Press",
            "url": "https://apnews.com/article/1ae6228c4928ddbb43f984e9b38f49dd",
        },
        {
            "category": "科技",
            "heat": "高通 / 中国数据中心芯片",
            "title": "高通计划推出面向中国的数据中心芯片，Dragonfly产品线将做出口合规版本",
            "impact": "Tom's Hardware报道，高通计划把Dragonfly数据中心产品线引入中国，包括AI加速器、CPU、自研芯片和连接芯片的出口合规版本。",
            "whyHot": "AI数据中心硬件竞争从GPU扩展到CPU、AI加速器、互连和软件生态；中国市场的合规版本会加剧国产算力与海外方案的竞争。",
            "relatedThemes": ["AI硬件/CPO/半导体", "国产算力", "服务器", "高速连接器"],
            "watch": "看A股映射时要核实公司是否进入服务器、连接器、PCB、封测或电源实际供应链，避免泛化为单纯高通概念。",
            "source": "Tom's Hardware",
            "url": "https://www.tomshardware.com/tech-industry/qualcomm-plans-china-specific-data-center-chips-built-to-clear-us-export-limits",
        },
        {
            "category": "科技",
            "heat": "AI网络 / 以太网交换机",
            "title": "Nvidia成为数据中心以太网交换机收入第一，Spectrum-X强化AI网络瓶颈叙事",
            "impact": "Business Insider报道，Nvidia在2026年一季度成为数据中心以太网交换机市场收入第一，Spectrum-X推动其从GPU扩展到AI网络基础设施。",
            "whyHot": "AI集群瓶颈不仅是算力芯片，还包括交换机、光模块、网卡、连接器和高速PCB；这会强化A股CPO、光通信和高速互连链条的关注。",
            "relatedThemes": ["CPO/光通信", "AI硬件/CPO/半导体", "高速互连", "数据中心"],
            "watch": "重点跟踪AI网络设备真实订单、客户验证和800G/1.6T升级节奏；光模块大涨后更要看封板质量和回封承接。",
            "source": "Business Insider",
            "url": "https://www.businessinsider.com/nvidia-leads-in-data-center-ethernet-switch-market-revenue-2026-6",
        },
        {
            "category": "科技",
            "heat": "AI数据中心 / 电力约束",
            "title": "新论文聚焦AI数据中心供电架构升级，高功率机柜推动电力设备前置",
            "impact": "arXiv近期论文指出，AI工作负载带来更高功率密度、电流瞬态和散热压力，传统48V机柜和低压交流配电架构面临限制，需要高压DC/DC、低压直流配电和固态变压器等方案。",
            "whyHot": "AI数据中心瓶颈正在从GPU扩展到电力、液冷、变压器、配电和机柜级电源，A股电力设备/液冷链条与算力建设联动增强。",
            "relatedThemes": ["AI数据中心", "电力能源/算力用电", "液冷", "电力设备/新能源设备"],
            "watch": "看项目订单、接电进度、液冷认证和交付能力，规划金额不能直接等同于收入兑现。",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/2606.25095",
        },
        {
            "category": "科技",
            "heat": "消费电子 / AI硬件供应链",
            "title": "立讯精密拟香港上市募资约31亿美元，资金投向产能扩张与AI相关硬件研发",
            "impact": "WSJ报道，苹果供应商立讯精密计划在香港进行约31亿美元募资，资金将用于生产扩张和研发，公司也在拓展数据中心和汽车电子等AI相关硬件方向。",
            "whyHot": "消费电子龙头向数据中心和AI硬件扩展，强化连接器、精密制造、服务器组件和汽车电子之间的产业映射。",
            "relatedThemes": ["消费电子/家居方向", "AI硬件/CPO/半导体", "高速连接器", "汽车电子"],
            "watch": "观察港股上市融资后的产能投向和客户结构变化，重点看AI服务器/数据中心业务是否形成可验证收入。",
            "source": "Wall Street Journal",
            "url": "https://www.wsj.com/business/apple-supplier-luxshare-set-for-hong-kongs-biggest-listing-so-far-this-year-032391a8",
        },
    ],
    "2026-06-29": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月29日A股收盘：指数修复但光通信分化，涨停池扩至107只",
            "impact": "本地收盘样本显示，上证指数+1.16%、创业板指+0.54%、A股平均股价+0.31%，涨停池107只；其他轮动37只居前，AI硬件/CPO/半导体15只、消费零售11只、机器人/高端制造10只跟随。",
            "whyHot": "指数反弹带来短线情绪修复，但光模块指数-1.98%、光纤通信-2.96%，说明资金并未无差别回流AI硬件，而是在涨停池里保留上游材料、芯片、机器人和低位轮动。",
            "relatedThemes": ["AI硬件/CPO/半导体", "机器人/高端制造/汽车链", "消费零售/家居服饰", "化工材料/电子化学品"],
            "watch": "次日重点看107只涨停后的晋级率和炸板修复；若光通信继续走弱，AI硬件内部会更偏芯片、存储、材料和上游设备，而不是纯光模块扩散。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "AI芯片 / 全球资金流",
            "title": "上半年AI芯片与存储股大涨，资金继续从软件叙事切向硬件瓶颈",
            "impact": "The Guardian报道，2026年上半年AI芯片、存储和硬件公司股价显著跑赢，韩国Kospi受三星、SK海力士带动创强势表现，美光、SanDisk、西部数据等也受AI存储需求推动。",
            "whyHot": "这与Serenity的核心框架一致：当AI资本开支继续扩张，市场更愿意给不可替代的上游瓶颈、存储、材料和互连环节定价，而不是只买应用层故事。",
            "relatedThemes": ["AI硬件/CPO/半导体", "HBM", "存储芯片", "半导体材料"],
            "watch": "A股映射不要只看概念标签，优先核实是否处在真实瓶颈位：产能稀缺、客户验证、涨价传导和扩产节奏。",
            "source": "The Guardian",
            "url": "https://www.theguardian.com/business/2026/jun/29/shares-in-chipmakers-underpinning-ai-boom-surge-in-first-half-of-2026",
        },
        {
            "category": "科技",
            "heat": "韩国半导体 / HBM扩产",
            "title": "韩国推出近6000亿美元芯片扩产计划，三星与SK海力士加码HBM和先进封装",
            "impact": "Financial Times报道，韩国公布半导体产业大型投资计划，三星电子与SK海力士拟合计投入约911万亿韩元，建设晶圆厂和先进封装集群，并支持下一代DRAM、AI芯片和国防半导体。",
            "whyHot": "HBM和先进封装仍是AI服务器链条关键上游，但大规模扩产也意味着市场会同时交易短期缺货和中期供给释放。",
            "relatedThemes": ["HBM", "半导体设备", "先进封装", "半导体材料"],
            "watch": "短线看材料、设备、封测映射，长线要跟踪扩产节点；如果扩产预期过快抬升，纯涨价逻辑会被供给周期压制。",
            "source": "Financial Times",
            "url": "https://www.ft.com/content/86013b7e-41da-445a-981c-075a701dccf6",
        },
        {
            "category": "科技",
            "heat": "国产AI芯片",
            "title": "AP称英伟达中国AI芯片销售受阻，华为等本土芯片厂商份额上升",
            "impact": "AP报道，受美国出口管制和中国本土替代推进影响，英伟达在中国AI芯片市场份额显著回落，华为昇腾等国产方案加速替代。",
            "whyHot": "这条新闻直接对应国产算力链：AI芯片、服务器、交换机、电源、PCB和国产生态适配都会被资金重新评估，但国产替代仍要看制程、供给和软件生态。",
            "relatedThemes": ["国产算力", "AI硬件/CPO/半导体", "服务器", "PCB/连接器"],
            "watch": "关注真实出货、客户训练/推理部署、生态适配和供应约束；仅靠“英伟达受限”推导所有国产芯片股上涨，容易高估弹性。",
            "source": "Associated Press",
            "url": "https://apnews.com/article/1ae6228c4928ddbb43f984e9b38f49dd",
        },
        {
            "category": "科技",
            "heat": "美光 / 存储利润",
            "title": "MarketWatch称美光利润有望跃居美国头部，AI内存价格成为核心变量",
            "impact": "MarketWatch报道，市场预期美光在AI存储景气下盈利能力快速上行，DRAM和HBM供给紧张推动价格与利润率重估。",
            "whyHot": "存储从周期品变成AI服务器核心瓶颈的叙事仍在发酵，对A股存储封测、材料、模组、设备和电子化学品都有映射。",
            "relatedThemes": ["存储芯片", "HBM", "半导体材料", "电子化学品"],
            "watch": "重点区分涨价受益、库存受益和成本承压，尤其要看合同锁价、客户结构和产能利用率。",
            "source": "MarketWatch",
            "url": "https://www.marketwatch.com/story/micron-is-about-to-be-more-profitable-than-any-u-s-company-except-nvidia-and-google-3a83e343",
        },
        {
            "category": "科技",
            "heat": "自研AI芯片 / 推理ASIC",
            "title": "OpenAI与Broadcom自研推理芯片继续发酵，AI算力从GPU走向全栈定制",
            "impact": "TechRadar与Tom's Hardware报道，OpenAI和Broadcom推出面向推理工作负载的Jalapeño Intelligence Processor，强调定制ASIC、HBM和数据中心全栈协同。",
            "whyHot": "自研ASIC会改变AI硬件利润分配：光模块、交换机、HBM、先进封装、PCB和服务器整机仍受益，但单一GPU叙事会被全栈定制分流。",
            "relatedThemes": ["AI硬件/CPO/半导体", "ASIC", "先进封装", "CPO/光通信"],
            "watch": "A股映射更适合看确定性供应链环节，而不是简单寻找“OpenAI概念”；订单、认证和客户集中度是关键。",
            "source": "TechRadar / Tom's Hardware",
            "url": "https://www.techradar.com/pro/broadcom-and-openai-debut-jalapeno-intelligence-processor-plot-an-apple-like-move-to-build-the-full-stack",
        },
        {
            "category": "科技",
            "heat": "AI数据中心 / 租赁承诺",
            "title": "大型科技公司AI数据中心租赁承诺升至约8500亿美元，电力和液冷约束继续前置",
            "impact": "New York Post报道，Meta、Microsoft等大型云厂商未来数据中心租赁承诺合计超过8500亿美元，AI基础设施投入继续通过长期租赁和项目承诺扩张。",
            "whyHot": "AI数据中心建设会把需求传导到电力接入、变压器、液冷、机柜、电源、光通信和IDC工程，约束点不再只是GPU。",
            "relatedThemes": ["AI数据中心", "电力能源/算力用电", "液冷", "CPO/光通信"],
            "watch": "继续跟踪项目落地和电力指标，规划金额不能直接等同订单；融资质量、接电进度和交付能力决定兑现节奏。",
            "source": "New York Post",
            "url": "https://nypost.com/2026/06/24/business/big-tech-spending-on-data-centers-balloons-to-850b-with-meta-and-microsoft-investing-tens-of-billions/",
        },
        {
            "category": "科技",
            "heat": "机器人 / Physical AI",
            "title": "人形机器人产业化继续推进，弱市中机器人链成为涨停活口之一",
            "impact": "结合近期Agility Robotics拟上市、NVIDIA机器人安全软件、国内机器人公司量产与数据采集进展，今日A股机器人/高端制造方向仍有10只涨停。",
            "whyHot": "机器人链的交易重心正从概念走向执行器、控制器、传感器、机器视觉、整机代工和数据闭环，适合用Serenity的“真实瓶颈+客户验证”框架筛选。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "机器视觉", "工业自动化"],
            "watch": "优先看有客户、订单、量产节奏和核心零部件卡位的公司；弱市中纯题材首板若缺少回封和换手，持续性要降权。",
            "source": "AP / Axios",
            "url": "https://apnews.com/article/39f2356b9c1e167d0985b821f70079c5",
        },
    ],
    "2026-06-26": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月26日A股收盘：指数普跌，机器人/高端制造与AI硬件仍保留局部涨停活口",
            "impact": "本地收盘样本显示，上证指数-2.26%、创业板指-4.07%、A股平均股价-2.51%，涨停池60只；机器人/高端制造/汽车链13只、AI硬件/CPO/半导体12只，是弱市中仍有辨识度的两个方向。",
            "whyHot": "指数大跌时，涨停数量和封板质量比单日题材热度更重要。今天光模块指数-4.54%、光纤通信-3.79%，说明AI硬件不是普涨，而是资金只保留少数弹性和事件驱动标的。",
            "relatedThemes": ["机器人/高端制造/汽车链", "AI硬件/CPO/半导体", "CPO/光通信", "半导体材料"],
            "watch": "次日重点看高标是否补跌、机器人与AI硬件前排是否能换手承接；若大票继续杀估值，首板晋级难度会明显抬升。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "存储 / 韩国半导体",
            "title": "韩国KOSPI大幅回落，SK海力士和三星电子领跌，内存涨价交易进入高波动阶段",
            "impact": "Barron's报道，韩国KOSPI在6月26日显著回落，SK海力士、三星电子等存储龙头走弱，带动美光盘前回吐前一日财报后的涨幅。",
            "whyHot": "HBM和DRAM仍是AI供应链瓶颈，但涨价逻辑开始叠加消费电子需求承压与拥挤交易风险，A股存储、材料、封测映射不能只看涨价，还要看客户结构和业绩兑现。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片", "HBM", "半导体材料"],
            "watch": "若海外存储龙头继续大幅波动，国内存储链更适合看订单和价格传导，而不是追逐单日情绪扩散。",
            "source": "Barron's",
            "url": "https://www.barrons.com/articles/micron-stock-price-sk-hynix-samsung-kospi-459506f7",
        },
        {
            "category": "科技",
            "heat": "内存缺货 / AI算力",
            "title": "WSJ称美光财报凸显内存短缺加剧，AI客户也在寻找降低HBM依赖的技术路线",
            "impact": "WSJ报道，美光最新财报显示内存短缺较三个月前进一步加剧，但大型客户也在通过新架构、压缩算法和替代内存方案降低长期成本压力。",
            "whyHot": "这对应Serenity体系里的瓶颈判断：真正有定价权的是短期不可替代的上游约束，但如果下游开始绕开该瓶颈，估值就不能只按线性涨价外推。",
            "relatedThemes": ["AI硬件/CPO/半导体", "HBM", "存储芯片", "AI数据中心"],
            "watch": "优先看有长期供货合同、产能扩张确定性和材料设备卡位的公司；仅靠“HBM涨价”标签、没有客户验证的品种要降权。",
            "source": "Wall Street Journal",
            "url": "https://www.wsj.com/finance/the-long-term-threat-to-the-memory-chip-boom-is-innovation-bb289488",
        },
        {
            "category": "科技",
            "heat": "消费电子 / 成本传导",
            "title": "苹果因内存成本上升上调Mac与iPad价格，AI算力挤占存储供给开始传导到终端",
            "impact": "Business Insider报道，美光财报点燃AI存储交易后，苹果设备涨价消息拖累科技股情绪，市场开始评估存储成本向消费电子终端传导的影响。",
            "whyHot": "存储涨价从服务器链扩散到消费电子链，既支撑存储厂商利润，也可能压缩下游品牌和ODM毛利，A股映射要区分涨价受益方和成本承压方。",
            "relatedThemes": ["存储芯片", "消费电子/家居方向", "电子化学品", "AI硬件/CPO/半导体"],
            "watch": "观察消费电子链能否把成本转嫁给终端消费者；若销量被价格压制，存储涨价交易会从利好变成分化。",
            "source": "Business Insider",
            "url": "https://www.businessinsider.com/tech-stocks-micron-earnings-apple-price-hikes-memory-ai-chips-2026-6",
        },
        {
            "category": "科技",
            "heat": "AI芯片 / 数据中心CPU",
            "title": "高通数据中心转型继续发酵，Meta成为Dragonfly C1000 CPU关键客户",
            "impact": "MarketWatch报道，高通在6月24日投资者日提出到2029财年非手机收入400亿美元目标，并把Meta作为数据中心CPU转型的重要客户案例。",
            "whyHot": "AI数据中心竞争不再只是GPU，CPU、互连、内存架构和软件栈都会重估；这对A股的高速连接器、PCB、电源、封测和服务器链有映射价值。",
            "relatedThemes": ["AI硬件/CPO/半导体", "服务器", "数据中心", "先进封装"],
            "watch": "只看“高通挑战英伟达”容易过度简化，实际要跟踪客户订单、功耗优势、软件生态和交付节奏。",
            "source": "MarketWatch",
            "url": "https://www.marketwatch.com/story/can-qualcomm-actually-compete-with-nvidia-inside-its-bold-data-center-gamble-38ac48b3",
        },
        {
            "category": "科技",
            "heat": "HBM扩产 / ADR融资",
            "title": "SK海力士申请纳斯达克ADR融资，资金投向先进存储晶圆厂、封装与EUV设备",
            "impact": "Tom's Hardware报道，SK海力士提交ADR发行文件，拟最多融资约294亿美元，用于龙仁晶圆厂、清州先进封装厂和EUV设备。",
            "whyHot": "HBM供给紧张正在推动存储龙头直接通过资本市场融资扩产，A股映射包括半导体设备、先进封装、材料和存储模组，但新增产能也会影响中期供需预期。",
            "relatedThemes": ["HBM", "半导体设备", "先进封装", "半导体材料"],
            "watch": "短期看缺货和涨价，长期看扩产节奏；若市场开始交易2027年后供给释放，纯涨价逻辑会降温。",
            "source": "Tom's Hardware",
            "url": "https://www.tomshardware.com/tech-industry/sk-hynix-files-to-raise-up-to-29-billion-in-nasdaq-listing",
        },
        {
            "category": "科技",
            "heat": "机器人 / Physical AI",
            "title": "英伟达推出Halos机器人安全软件，继续把Physical AI能力推向人形机器人落地",
            "impact": "Axios报道，英伟达发布面向人形机器人的安全软件套件Nvidia Halos for Robotics，强调传感、仿真、检测和安全验证能力。",
            "whyHot": "机器人行情的核心正在从单纯硬件本体，转向模型、仿真、传感器、控制器和安全验证系统协同，A股机器人链需要看真实客户和量产节点。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "机器视觉", "工业自动化"],
            "watch": "弱市里机器人首板较多时，更要区分有客户/产品/订单的产业链公司与纯概念补涨票。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/22/nvidia-humanoid-ai-robotics",
        },
        {
            "category": "科技",
            "heat": "人形机器人 / 产业化",
            "title": "Agility Robotics拟借SPAC上市，融资用于扩大Digit人形机器人产能",
            "impact": "AP报道，Agility Robotics计划通过SPAC上市，估值约25亿美元，其Digit机器人已在仓储和搬运场景商业试点，投资方包括Amazon、Nvidia、SoftBank和Foxconn等。",
            "whyHot": "海外机器人公司进入资本市场会强化人形机器人产业化预期，国内映射重点是减速器、控制器、传感器、执行器、视觉和整机代工。",
            "relatedThemes": ["机器人/高端制造/汽车链", "减速器", "传感器", "工业自动化"],
            "watch": "关注量产交付和客户试点转正式订单，而不是只看融资估值；弱市中机器人方向若要持续，需要出现产业订单或龙头换手承接。",
            "source": "AP",
            "url": "https://apnews.com/article/39f2356b9c1e167d0985b821f70079c5",
        },
    ],
    "2026-06-25": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月25日A股收盘：AI硬件/CPO/半导体继续领涨，券商与创业板同步走强",
            "impact": "本地收盘样本显示，上证指数+0.23%、创业板指+2.84%、证券指数+3.43%，涨停池86只；其中AI硬件/CPO/半导体25只、算力租赁15只、电子化学品12只，是今天涨停结构的主轴。",
            "whyHot": "资金仍围绕AI算力的高速互连、芯片、存储、服务器和上游材料扩散，且创业板与券商同步放量时，风险偏好比前几个交易日更强。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "半导体材料", "券商金融"],
            "watch": "继续看前排封单质量和炸板回封，尤其是AI硬件能否从首板扩散到二板、三板；券商若冲高回落，会影响高弹性科技股的承接。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "AI芯片 / 数据中心CPU",
            "title": "高通披露Meta为数据中心CPU首个大型客户，2029年数据中心收入目标上看150亿美元",
            "impact": "高通在投资者日宣布Meta将从2028年底开始部署其C1000数据中心CPU，并把2029财年非手机业务收入目标提高到400亿美元，其中数据中心业务目标超过150亿美元。",
            "whyHot": "这说明AI数据中心的CPU侧也在加速多元化，除GPU之外，低功耗CPU、Arm生态、定制ASIC与高速互连都会争夺新增资本开支。",
            "relatedThemes": ["AI硬件/CPO/半导体", "服务器", "数据中心", "先进封装"],
            "watch": "A股映射重点看服务器电源、PCB、高速连接器、光模块和半导体IP/封测，避免把所有数据中心CPU新闻简单映射为泛半导体概念。",
            "source": "MarketWatch / Financial Times",
            "url": "https://www.marketwatch.com/story/qualcomms-stock-is-soaring-as-these-big-numbers-excite-wall-street-316d41f4",
        },
        {
            "category": "科技",
            "heat": "AI软件栈 / CUDA替代",
            "title": "高通拟约39亿美元收购Modular，补齐AI数据中心软件栈",
            "impact": "Modular提供跨硬件AI部署平台与Mojo语言，高通希望借此提升从终端到云端的AI计算软件能力，并服务其数据中心芯片战略。",
            "whyHot": "AI硬件竞争不只看芯片，也看开发者生态、编译器、推理部署和跨硬件迁移能力；这类收购会强化国产替代和异构计算软件链的关注度。",
            "relatedThemes": ["AI应用/数据要素/服务", "AI硬件/CPO/半导体", "算力软件", "边缘AI"],
            "watch": "看A股软件映射时要核实真实产品、客户和收入，纯CUDA替代叙事若没有开发者生态和落地客户，弹性容易只停留在题材层。",
            "source": "Barron's / WSJ / WIRED",
            "url": "https://www.barrons.com/articles/qualcomm-buys-modular-stock-price-247a2464",
        },
        {
            "category": "科技",
            "heat": "HBM / 存储涨价",
            "title": "美光业绩大超预期，AI推理带动存储需求继续供不应求",
            "impact": "美光公布2026财年三季度收入414.6亿美元、调整后EPS 25.11美元，并给出约500亿美元的下一季度收入指引，明显高于市场预期。",
            "whyHot": "AI从训练转向推理后，对HBM、DRAM、NAND和高带宽存储的消耗继续上升，存储价格和供给约束正在成为AI产业链的核心瓶颈之一。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片", "HBM", "半导体材料"],
            "watch": "A股重点看存储封测、材料、模组、设备与上游化学品，优先选择能从涨价或产能扩张中兑现收入的公司。",
            "source": "Investopedia / Business Insider",
            "url": "https://www.investopedia.com/micron-earnings-q3-fy2026-memory-stock-soars-ai-demand-12006096",
        },
        {
            "category": "科技",
            "heat": "韩国半导体 / HBM",
            "title": "SK海力士计划在纳斯达克发行ADR融资约296亿美元，韩国芯片股集体反弹",
            "impact": "SK海力士计划7月10日在纳斯达克挂牌ADR，融资规模约296亿美元，资金将用于扩产与先进制程设备；消息推动SK海力士和三星电子走强。",
            "whyHot": "HBM与高端存储已经成为英伟达AI加速器链条里的稀缺上游，资本市场开始直接重估韩国存储龙头的定价权和扩产能力。",
            "relatedThemes": ["AI硬件/CPO/半导体", "HBM", "存储芯片", "半导体设备"],
            "watch": "这条新闻对A股更偏上游材料、设备、封测和存储模组映射；同时要防范大规模融资带来的中期供给扩张预期。",
            "source": "Business Insider / WSJ / Investopedia",
            "url": "https://www.businessinsider.com/south-korea-kospi-stock-market-today-sk-hynix-nasdaq-listing-2026-6",
        },
        {
            "category": "科技",
            "heat": "AI数据中心 / 云资本开支",
            "title": "大型科技公司未来数据中心租赁承诺升至约8500亿美元，Meta与微软继续加码AI基建",
            "impact": "报道称主要云厂商未来租赁义务合计超过8500亿美元，Meta、微软等继续上调AI数据中心相关长期承诺。",
            "whyHot": "AI基建需求正在从一次性采购变成多年资本开支承诺，对电力、液冷、光通信、交换机、服务器和IDC工程形成持续需求牵引。",
            "relatedThemes": ["AI硬件/CPO/半导体", "AI数据中心", "电力能源/算力用电", "液冷"],
            "watch": "重点跟踪订单能见度和项目交付，不只看规划金额；电力接入、冷却、土地和融资成本会决定最终兑现节奏。",
            "source": "New York Post",
            "url": "https://nypost.com/2026/06/24/business/big-tech-spending-on-data-centers-balloons-to-850b-with-meta-and-microsoft-investing-tens-of-billions/",
        },
        {
            "category": "科技",
            "heat": "日本AI数据中心",
            "title": "黑石计划未来3到5年在日本AI数据中心投入300亿美元，目标容量超过1GW",
            "impact": "Nikkei Asia/FT报道称，黑石计划在日本AI数据中心投入约300亿美元，继续扩大亚洲AI算力基础设施布局。",
            "whyHot": "算力建设正在从美国扩展到日本、韩国、印度等地区，跨区域数据中心投资会拉动光模块、电源、液冷、变压器、机柜和施工配套需求。",
            "relatedThemes": ["AI数据中心", "CPO/光通信", "电力能源/算力用电", "液冷"],
            "watch": "看国内映射时要区分出口链、海外IDC工程链和纯概念链，优先核实公司海外客户、认证资质和产能排期。",
            "source": "Financial Times / Nikkei Asia",
            "url": "https://www.ft.com/content/88607186-a7d8-4888-9e8b-00e8f8059e1e",
        },
        {
            "category": "科技",
            "heat": "消费电子 / 存储成本",
            "title": "苹果因存储成本飙升提示产品涨价压力，AI数据中心挤占DRAM与NAND供给",
            "impact": "苹果CEO Tim Cook近期表示，受存储和内存成本上涨影响，产品涨价压力难以避免；这强化了AI需求挤占消费电子供应链的逻辑。",
            "whyHot": "当AI数据中心采购把存储供给推向紧张，消费电子也被动承受成本上升，存储涨价链不再只是服务器题材，也会传导到手机、PC和智能硬件。",
            "relatedThemes": ["存储芯片", "消费电子/家居方向", "AI硬件/CPO/半导体", "电子化学品"],
            "watch": "短线看存储涨价的业绩弹性，中线要观察终端涨价是否抑制出货；只靠涨价预期、没有库存和订单兑现的公司要降权。",
            "source": "Business Insider / Tom's Hardware",
            "url": "https://www.businessinsider.com/apple-price-increases-memory-stocks-ai-mu-sndk-wdc-aapl-2026-6",
        },
    ],
    "2026-06-24": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月24日A股结构分化，AI硬件/CPO/半导体30只涨停居首，光模块与半导体指数同步走强",
            "impact": "本地收盘样本显示上证+0.11%、创业板指+1.41%、证券指数-1.90%；涨停池98只，其中AI硬件/CPO/半导体30只、电子化学品15只、券商14只居前。",
            "whyHot": "科技主线在指数分化下仍保持扩散，半导体+2.47%、光模块+2.60%、光纤通信+1.18%，说明资金继续围绕AI算力的芯片与高速互连环节寻找强势方向。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "化工材料/电子化学品", "券商金融"],
            "watch": "关注AI硬件能否从涨停扩散延续至容量中军；券商走弱时，科技前排的封板质量和回封承接比指数更有参考价值。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "国产AI / Agent",
            "title": "智谱GLM模型被置于中美AI竞速讨论中，Agent能力成为模型竞争的重要观察点",
            "impact": "国产大模型和Agent能力的进展，映射到A股AI应用、算力、国产芯片、服务器与数据中心软件服务链。",
            "whyHot": "模型竞争正从单纯参数规模转向工具调用、复杂任务和Agent执行能力，相关投资主线需要以实际客户、调用量与商业化收入验证。",
            "relatedThemes": ["AI应用/数据要素/服务", "国产算力", "AI硬件/CPO/半导体"],
            "watch": "区分模型发布和商业化兑现，重点核验客户订单、开发者使用量与算力投入，而非只按概念联想。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/23/china-us-ai-race-glm-anthropic",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA开源Halo机器人基础模型，具身智能与Physical AI生态继续扩展",
            "impact": "机器人基础模型向开源生态扩展，A股映射到机器人本体、控制器、伺服、机器视觉、工业自动化与边缘AI硬件。",
            "whyHot": "具身智能的技术重心正在从单一硬件走向“模型+数据+执行器”协同，利好真正具备核心零部件、数据闭环或应用场景的公司。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "机器视觉", "工业自动化"],
            "watch": "重点看真实部署、客户验证和量产节奏；纯概念品种需要观察板块核心的成交与回封质量。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/23/nvidia-open-source-halo-robot-foundation-models",
        },
        {
            "category": "科技",
            "heat": "AI冷却 / 数据中心",
            "title": "NVIDIA数据中心水冷解决方案受到关注，AI集群扩容开始面对冷却与水资源约束",
            "impact": "AI数据中心冷却从机房配套升级为扩容约束之一，A股映射到液冷、冷板、CDU、泵阀、换热器、水处理与数据中心工程。",
            "whyHot": "GPU密度提升会把电力、散热和水资源一并推到关键约束位置，冷却链的订单、单机价值量和产能是比概念更关键的验证指标。",
            "relatedThemes": ["AI数据中心", "液冷/电源", "电力能源/算力用电", "高端制造"],
            "watch": "核验液冷产品认证、服务器厂或云厂商订单、交付节奏与毛利变化；没有订单时只按远期基础设施催化处理。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/22/nvidia-data-center-water-solution",
        },
        {
            "category": "科技",
            "heat": "开源AI / 算力",
            "title": "开源AI公司Reflection获得SpaceX算力支持，开源模型的训练与推理资源竞争升温",
            "impact": "训练资源获得外部支持会加速开源模型迭代，A股映射到国产算力、服务器、光通信、存储、数据中心与模型服务。",
            "whyHot": "大模型竞争最终仍受算力供给、网络互连和资本来源约束，相关映射需区分真实算力合同与泛化的概念标签。",
            "relatedThemes": ["AI硬件/CPO/半导体", "AI数据中心", "国产算力", "AI应用/数据要素/服务"],
            "watch": "看算力合同、客户信用与实际交付，尤其注意重资产建设中的融资质量和股权稀释风险。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/22/open-source-ai-gets-more-compute-from-spacex",
        },
        {
            "category": "科技",
            "heat": "HBM / 存储",
            "title": "Micron与Anthropic的HBM供应关系受到关注，AI模型训练继续推升高带宽内存需求",
            "impact": "HBM供需与AI加速器扩产高度相关，A股映射到存储芯片、封测、先进封装、材料、设备与服务器链。",
            "whyHot": "AI训练和推理对带宽的需求会向HBM、先进封装与高速互连共同传导，存储景气需要用价格、供货周期和业绩指引验证。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片", "先进封装", "半导体材料"],
            "watch": "重点看产品价格、库存、客户认证和产能利用率；避免将海外供应新闻直接等同于国内公司订单。",
            "source": "Barron's",
            "url": "https://www.barrons.com/articles/micron-stock-anthropic-ai-f93e8bd4",
        },
        {
            "category": "政策",
            "heat": "AI芯片出口",
            "title": "美国AI芯片出口策略持续牵动全球半导体供应链，贸易与安全约束仍是重要变量",
            "impact": "出口政策会影响高端GPU、网络设备、先进制程与国产替代节奏，A股映射到国产算力、半导体设备、材料与自主可控链。",
            "whyHot": "政策扰动可能改变客户采购路径与库存行为，但其影响需区分正式规则、执行细则和企业实际订单，不能只用情绪解读。",
            "relatedThemes": ["国产算力", "AI硬件/CPO/半导体", "半导体设备", "自主可控"],
            "watch": "跟踪正式政策文本、厂商指引及供应链交付；对仅靠传闻驱动的高波动个股保持风险折价。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/16/trump-ai-export-strategy-trade",
        },
        {
            "category": "科技",
            "heat": "仓储机器人",
            "title": "Amazon仓储自动化推进，机器人替代与效率提升继续影响物流和工业自动化链",
            "impact": "大型仓储自动化项目映射到移动机器人、视觉、传感器、控制系统、减速器、工业软件与物流设备。",
            "whyHot": "Physical AI的商业化路径更依赖重复、可量化的工业和物流场景；订单、部署数量和单位经济性比单一产品发布更具验证价值。",
            "relatedThemes": ["机器人/高端制造/汽车链", "物流自动化", "机器视觉", "工业软件"],
            "watch": "优先关注已进入客户仓储或工厂场景并有批量订单的公司，避免把海外案例直接映射为国内业绩。",
            "source": "Business Insider",
            "url": "https://www.businessinsider.com/amazon-warehouse-automation-moving-workers-labor-hours-robots-2026-6",
        },
    ],
    "2026-06-22": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月22日A股放量上行，券商、电子化学品与AI硬件/CPO/半导体共同扩散",
            "impact": "本地收盘样本显示上证+1.78%、创业板指+2.52%、证券指数+7.41%，134只个股封住涨停；电子化学品30只、券商22只、AI硬件/CPO/半导体18只居前。",
            "whyHot": "权重与科技方向同步走强，使行情从单纯题材轮动转为更广泛的风险偏好修复；CPO、光通信、半导体材料和机器人同时获得资金关注。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "化工材料/电子化学品", "机器人/高端制造/汽车链"],
            "watch": "关注券商带来的风险偏好能否延续，以及AI硬件前排能否从首板扩散到容量品种；多次开板个股仍以回封质量为准。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "InP/CPO",
            "title": "近期NVIDIA与Coherent推进德州Sherman工厂20亿美元AI基础设施升级，涉及AI高速互连用InP激光器",
            "impact": "项目指向高速光互连所需的InP激光器和制造能力，A股映射到CPO、光模块、光通信、光芯片、化合物半导体与高端装备。",
            "whyHot": "AI集群互连的瓶颈继续向光芯片、激光器和InP材料上游传导，与当天CPO/光模块、通信设备和电子化学品的活跃存在产业逻辑呼应。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光芯片/InP", "化工材料/电子化学品"],
            "watch": "看国内公司是否有800G/1.6T、硅光子、InP或海外客户订单的可验证证据；没有订单验证的题材股持续性需打折。",
            "source": "AP News",
            "url": "https://apnews.com/article/9bf560fa2365e4d6b57804438cda579e",
        },
        {
            "category": "科技",
            "heat": "光通信/硅光子",
            "title": "近期Corning的AI数据中心光通信布局受到关注，硅光子、CPO与光纤产能成为AI互连的重要供给环节",
            "impact": "Corning将增长重点投向AI数据中心光通信、硅光子和CPO，A股映射到光模块、光通信、光纤光缆、PCB与数据中心连接器。",
            "whyHot": "AI基础设施的约束不只在GPU，也在高速互连、光纤和光电转换；该事件提供了当天光模块、光纤通信链活跃的中期产业背景。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光纤光缆", "AI数据中心"],
            "watch": "重点核验海外客户、800G/1.6T、硅光子产品与光纤产能扩张；情绪首板需区分订单线索与概念映射。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/research/ibd-stock-of-the-day/corning-stock-artificial-intelligence-data-centers-photonics/",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "近期NVIDIA、Amazon等支持Neura Robotics最高14亿美元融资，Physical AI与人形机器人产业化升温",
            "impact": "融资面向认知机器人和人形机器人扩产，A股映射至机器人本体、控制器、伺服、减速器、机器视觉与工业自动化。",
            "whyHot": "产业进展把Physical AI从模型叙事推向产能、订单和应用场景验证，为当天机器人/高端制造方向的14只涨停提供了外部催化背景。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "工业自动化", "机器视觉"],
            "watch": "优先看核心零部件壁垒、客户认证和量产能力；没有订单与产能数据的小市值个股只按题材热度处理。",
            "source": "WSJ / The Times",
            "url": "https://www.thetimes.com/business/wsj/article/nvidia-amazon-back-neura-robotics-14-billion-fundraise-cktcg6fwd",
        },
        {
            "category": "科技",
            "heat": "AI基建",
            "title": "近期Apollo、Blackstone与Broadcom合作350亿美元AI基础设施融资，支持Anthropic算力扩张",
            "impact": "融资用于支持AI芯片、网络和数据中心部署，A股映射至AI ASIC、高速互连、PCB、先进封装、服务器与液冷链条。",
            "whyHot": "AI资本开支正在进入芯片、网络、融资和数据中心一体化建设阶段，强化了从CPO到先进封装、电源与液冷的需求预期。",
            "relatedThemes": ["AI硬件/CPO/半导体", "PCB/先进封装", "AI数据中心", "算力基础设施"],
            "watch": "跟踪A股AI硬件能否由光模块向PCB、铜连接、先进封装、服务器电源和液冷扩散，并核验订单而非只看概念。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/10/apollo-anthropic-blackstone-broadcom",
        },
        {
            "category": "财经",
            "heat": "算力用电",
            "title": "近期KKR、NVIDIA、Kuwait Investment Authority和Vistra推出100亿美元AI数据中心基础设施公司Helix",
            "impact": "Helix把NVIDIA算力、长期资本与Vistra电力资源绑定，A股映射到电力设备、储能、液冷、UPS、电源和数据中心工程。",
            "whyHot": "AI基建的瓶颈正从芯片外溢到电力接入和能源配套，给当天电力设备、数据中心配套和工业材料提供中期观察框架。",
            "relatedThemes": ["电力设备/新能源设备", "电力能源/算力用电", "AI数据中心", "液冷/电源"],
            "watch": "重点以电网接入、产能与订单为验证条件；缺少订单兑现时，只作为AI基建外溢催化，而非确定性业绩来源。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/finance/investing/kkr-launches-10b-ai-infrastructure-company-with-nvidia-vistra-47a8246b",
        },
    ],
    "2026-06-18": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月18日A股结构分化，机器人/高端制造居首，CPO/光模块继续保持强势",
            "impact": "今日上证-0.43%、创业板指+2.05%、证券指数-2.96%，但涨停池91只；机器人/高端制造19只居首，AI硬件/CPO/半导体16只，资源品/金属材料9只。",
            "whyHot": "指数层面分化明显，资金从券商等权重回撤中继续抱团机器人、CPO、光模块和上游材料，说明盘面仍围绕AI基础设施、Physical AI和供应链瓶颈展开。",
            "relatedThemes": ["机器人/高端制造/汽车链", "AI硬件/CPO/半导体", "CPO/光通信", "资源品/金属材料"],
            "watch": "看机器人能否从情绪首板扩散到核心零部件和容量中军；CPO/光模块若继续强，要观察高位票回封质量和成交承接。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "InP/CPO",
            "title": "NVIDIA与Coherent推进德州Sherman工厂20亿美元AI基础设施升级，生产用于AI高速互连的InP激光器",
            "impact": "项目围绕InP激光器和高速AI数据传输，A股映射到CPO、光模块、光通信、光芯片、化合物半导体和高端制造设备。",
            "whyHot": "AI集群互连的瓶颈正在上移到光芯片、激光器和InP材料，符合今天CPO/光模块和机器人/高端制造同时活跃的产业逻辑。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光芯片/InP", "机器人/高端制造/汽车链"],
            "watch": "看国内光通信链是否有800G/1.6T、硅光子、InP或海外客户订单线索；没有订单验证的小票持续性要打折。",
            "source": "AP News",
            "url": "https://apnews.com/article/9bf560fa2365e4d6b57804438cda579e",
        },
        {
            "category": "科技",
            "heat": "光通信/硅光子",
            "title": "Corning因AI数据中心光通信布局获关注，硅光子、CPO和光纤产能成为AI互连瓶颈",
            "impact": "Corning把增长重心转向AI数据中心光通信、硅光子和CPO，A股映射到光模块、光通信、光纤光缆、PCB和数据中心连接器。",
            "whyHot": "AI集群的瓶颈不只在GPU，也在高速互连、光纤和光电转换；这与今天光模块和光纤通信延续强势一致。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光纤光缆", "AI数据中心"],
            "watch": "重点看有海外客户、800G/1.6T产品、硅光子或光纤产能扩张的公司；纯情绪小票需要观察次日换手承接。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/research/ibd-stock-of-the-day/corning-stock-artificial-intelligence-data-centers-photonics/",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA、Amazon等支持Neura Robotics最高14亿美元融资，Physical AI和人形机器人产业化升温",
            "impact": "Neura融资用于扩产认知机器人和人形机器人，A股映射到机器人本体、控制器、伺服、减速器、机器视觉和工业自动化。",
            "whyHot": "资金正在把Physical AI从模型叙事推向产能、订单和真实场景验证，和今天机器人/高端制造方向涨停集中相互印证。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "工业自动化", "机器视觉"],
            "watch": "重点看有核心零部件壁垒、真实客户认证和量产能力的公司；单纯概念小票持续性要打折。",
            "source": "WSJ / The Times",
            "url": "https://www.thetimes.com/business/wsj/article/nvidia-amazon-back-neura-robotics-14-billion-fundraise-cktcg6fwd",
        },
        {
            "category": "科技",
            "heat": "AI基建",
            "title": "Apollo、Blackstone与Broadcom合作350亿美元AI基础设施融资，支持Anthropic算力扩张",
            "impact": "融资用于帮助Anthropic租用由Broadcom参与开发的Google芯片，并部署在Fluidstack数据中心，A股映射到AI ASIC、高速互连、PCB、先进封装和服务器链。",
            "whyHot": "AI资本开支正在从单一GPU采购进入芯片、网络、融资和数据中心一体化阶段，会继续强化上游硬件瓶颈的估值弹性。",
            "relatedThemes": ["AI硬件/CPO/半导体", "PCB/先进封装", "AI数据中心", "算力基础设施"],
            "watch": "看A股AI硬件是否能从光模块扩散到PCB、铜连接、先进封装、服务器电源和液冷等更宽链条。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/10/apollo-anthropic-blackstone-broadcom",
        },
        {
            "category": "财经",
            "heat": "算力用电",
            "title": "KKR、NVIDIA、Kuwait Investment Authority和Vistra推出100亿美元AI数据中心基础设施公司Helix",
            "impact": "Helix把NVIDIA算力、KKR资本和Vistra电力资源绑定到AI数据中心建设，A股映射到电力设备、储能、液冷、UPS、电源和数据中心工程。",
            "whyHot": "AI基建的瓶颈正在从芯片扩散到电力接入和能源配套，能解释电力设备、算力用电和数据中心设备的中期关注度。",
            "relatedThemes": ["电力设备/新能源设备", "电力能源/算力用电", "AI数据中心", "液冷/电源"],
            "watch": "看电力设备和数据中心配套是否有订单、产能和毛利改善；没有订单验证时，只能当作AI基建外溢催化。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/finance/investing/kkr-launches-10b-ai-infrastructure-company-with-nvidia-vistra-47a8246b",
        },
    ],
    "2026-06-17": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月17日A股结构分化，AI硬件/CPO/半导体继续占据涨停池核心",
            "impact": "今日上证+0.40%、创业板指+1.56%，但A股平均股价-0.48%；涨停池86只，其中AI硬件/CPO/半导体30只、机器人/高端制造12只、化工材料/电子化学品12只居前。",
            "whyHot": "指数修复并不均衡，资金继续集中到AI数据中心上游瓶颈、光通信、半导体材料和机器人方向，说明主线仍是硬件扩产和供应链卡位。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "机器人/高端制造/汽车链", "化工材料/电子化学品"],
            "watch": "看CPO、半导体和电子化学品是否由小票连板扩散到容量中军；若炸板次数继续上升，次日重点观察回封质量。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "光通信/硅光子",
            "title": "Corning因AI数据中心光通信布局获关注，硅光子、CPO和光纤产能成为AI互连瓶颈",
            "impact": "Corning把增长重心转向AI数据中心光通信、硅光子和CPO，A股映射到光模块、光通信、光纤光缆、PCB和数据中心连接器。",
            "whyHot": "AI集群的瓶颈不只在GPU，也在高速互连、光纤和光电转换；这与今天光模块、光纤通信和半导体方向继续走强一致。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光纤光缆", "AI数据中心"],
            "watch": "重点看有海外客户、800G/1.6T产品、硅光子或光纤产能扩张的公司；纯情绪小票需要观察次日换手承接。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/research/ibd-stock-of-the-day/corning-stock-artificial-intelligence-data-centers-photonics/",
        },
        {
            "category": "科技",
            "heat": "AI基建",
            "title": "Apollo、Blackstone与Broadcom合作350亿美元AI基础设施融资，支持Anthropic算力扩张",
            "impact": "融资用于帮助Anthropic租用由Broadcom参与开发的Google芯片，并部署在Fluidstack数据中心，A股映射到AI ASIC、高速互连、PCB、先进封装和服务器链。",
            "whyHot": "AI资本开支正在从单一GPU采购进入芯片、网络、融资和数据中心一体化阶段，会继续强化上游硬件瓶颈的估值弹性。",
            "relatedThemes": ["AI硬件/CPO/半导体", "PCB/先进封装", "AI数据中心", "算力基础设施"],
            "watch": "看A股AI硬件是否能从光模块扩散到PCB、铜连接、先进封装、服务器电源和液冷等更宽链条。",
            "source": "Axios",
            "url": "https://www.axios.com/2026/06/10/apollo-anthropic-blackstone-broadcom",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA、Amazon等支持Neura Robotics最高14亿美元融资，Physical AI和人形机器人产业化升温",
            "impact": "Neura融资用于扩产认知机器人和人形机器人，A股映射到机器人本体、控制器、伺服、减速器、机器视觉和工业自动化。",
            "whyHot": "资金正在把Physical AI从模型叙事推向产能、订单和真实场景验证，和今天机器人/高端制造方向涨停集中相互印证。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "工业自动化", "机器视觉"],
            "watch": "重点看有核心零部件壁垒、真实客户认证和量产能力的公司；单纯概念小票持续性要打折。",
            "source": "WSJ",
            "url": "https://www.wsj.com/tech/ai/nvidia-amazon-back-neura-robotics-1-4-billion-fundraise-ff630662",
        },
        {
            "category": "政策",
            "heat": "国产AI算力",
            "title": "报道称中国拟建设约2万亿元国家AI数据中心网格，并推动80%国产芯片占比",
            "impact": "若规划落地，将强化国产AI芯片、服务器、光通信、电源、液冷、数据中心建设和运营商算力网络需求。",
            "whyHot": "国产化约束会把AI需求传导到半导体设备、先进封装、PCB、光通信和电力基础设施，符合今天AI硬件和半导体的资金方向。",
            "relatedThemes": ["AI硬件/CPO/半导体", "国产算力", "AI数据中心", "电力设备/新能源设备"],
            "watch": "看后续是否有国家部委、运营商或地方项目的正式落地文件；未正式落地前，按产业预期而非确定订单处理。",
            "source": "Tom's Hardware",
            "url": "https://www.tomshardware.com/tech-industry/china-drafts-295-billion-plan-to-build-a-national-ai-data-center-grid-running-on-80-percent-domestic-chips",
        },
        {
            "category": "财经",
            "heat": "算力用电",
            "title": "KKR、NVIDIA、Kuwait Investment Authority和Vistra推出100亿美元AI数据中心基础设施公司Helix",
            "impact": "Helix把NVIDIA算力、KKR资本和Vistra电力资源绑定到AI数据中心建设，A股映射到电力设备、储能、液冷、UPS、电源和数据中心工程。",
            "whyHot": "AI基建的瓶颈正在从芯片扩散到电力接入和能源配套，能解释电力设备、算力用电和数据中心设备的中期关注度。",
            "relatedThemes": ["电力设备/新能源设备", "电力能源/算力用电", "AI数据中心", "液冷/电源"],
            "watch": "看电力设备和数据中心配套是否有订单、产能和毛利改善；没有订单验证时，只能当作AI基建外溢催化。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/finance/investing/kkr-launches-10b-ai-infrastructure-company-with-nvidia-vistra-47a8246b",
        },
    ],
    "2026-06-16": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月16日A股结构分化，CPO/光通信、半导体和机器人方向继续占据涨停池核心",
            "impact": "今日上证-0.11%，但创业板指+1.72%、A股平均股价+1.63%；涨停池117只，其中AI硬件/CPO/半导体31只、机器人/高端制造18只、化工材料/电子化学品17只居前。",
            "whyHot": "指数分化但AI硬件链继续扩散，光模块、光纤通信和半导体指数均延续强势，说明资金仍围绕AI数据中心上游瓶颈和硬件扩产做主线抱团。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "机器人/高端制造/汽车链", "化工材料/电子化学品"],
            "watch": "看CPO和半导体是否从连板情绪扩散到容量中军；若高位票炸板增加，次日要重点看前排承接和回封质量。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "光通信/硅光子",
            "title": "Corning因AI数据中心光通信布局获关注，硅光子、CPO和光纤产能成为AI互连瓶颈",
            "impact": "Corning将增长重心转向AI数据中心光通信和硅光子，A股映射到光模块、光通信、光纤光缆、PCB和数据中心连接器。",
            "whyHot": "AI集群的瓶颈不只在GPU，也在高速互连、光纤和光电转换；这和今天光模块、光纤通信继续走强高度一致。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光纤光缆", "AI数据中心"],
            "watch": "重点看有海外客户、800G/1.6T产品、硅光子或光纤产能扩张的公司；纯情绪小票需要观察次日换手承接。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/research/ibd-stock-of-the-day/corning-stock-artificial-intelligence-data-centers-photonics/",
        },
        {
            "category": "科技",
            "heat": "AI基建",
            "title": "Broadcom、Apollo和Blackstone推出350亿美元AI XPV平台，目标到2028年建设20GW算力容量",
            "impact": "平台以Broadcom芯片、网络方案和长期资本绑定AI数据中心扩张，A股映射到AI ASIC、交换芯片、高速互连、PCB、先进封装和服务器链。",
            "whyHot": "AI资本开支正在从单一GPU采购进入芯片、网络、融资和数据中心一体化阶段，会继续强化上游硬件瓶颈的估值弹性。",
            "relatedThemes": ["AI硬件/CPO/半导体", "PCB/先进封装", "AI数据中心", "算力基础设施"],
            "watch": "看A股AI硬件是否能从光模块扩散到PCB、铜连接、先进封装、服务器电源和液冷等更宽链条。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/tech/ai/broadcom-apollo-blackstone-launch-35-billion-ai-infrastructure-platform-8fc8f65e",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA、Amazon等支持Neura Robotics最高14亿美元融资，Physical AI和人形机器人产业化升温",
            "impact": "Neura融资用于扩产认知机器人和人形机器人，A股映射到机器人本体、控制器、伺服、减速器、机器视觉和工业自动化。",
            "whyHot": "资金正在把Physical AI从模型叙事推向产能、订单和真实场景验证，和今天机器人/高端制造方向涨停集中相互印证。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "工业自动化", "机器视觉"],
            "watch": "重点看有核心零部件壁垒、真实客户认证和量产能力的公司；单纯概念小票持续性要打折。",
            "source": "WSJ",
            "url": "https://www.wsj.com/tech/ai/nvidia-amazon-back-neura-robotics-1-4-billion-fundraise-ff630662",
        },
        {
            "category": "政策",
            "heat": "国产AI算力",
            "title": "报道称中国拟建设约2万亿元国家AI数据中心网格，并推动80%国产芯片占比",
            "impact": "若规划落地，将强化国产AI芯片、服务器、光通信、电源、液冷、数据中心建设和运营商算力网络需求。",
            "whyHot": "国产化约束会把AI需求传导到半导体设备、先进封装、PCB、光通信和电力基础设施，符合今天AI硬件和半导体的资金方向。",
            "relatedThemes": ["AI硬件/CPO/半导体", "国产算力", "AI数据中心", "电力设备/新能源设备"],
            "watch": "看后续是否有国家部委、运营商或地方项目的正式落地文件；未正式落地前，按产业预期而非确定订单处理。",
            "source": "Tom's Hardware",
            "url": "https://www.tomshardware.com/tech-industry/china-drafts-295-billion-plan-to-build-a-national-ai-data-center-grid-running-on-80-percent-domestic-chips",
        },
        {
            "category": "财经",
            "heat": "算力用电",
            "title": "KKR、NVIDIA、Kuwait Investment Authority和Vistra推出100亿美元AI数据中心基础设施公司Helix",
            "impact": "Helix把NVIDIA算力、KKR资本和Vistra电力资源绑定到AI数据中心建设，A股映射到电力设备、储能、液冷、UPS、电源和数据中心工程。",
            "whyHot": "AI基建的瓶颈正在从芯片扩散到电力接入和能源配套，能解释电力设备、算力用电和数据中心设备的中期关注度。",
            "relatedThemes": ["电力设备/新能源设备", "电力能源/算力用电", "AI数据中心", "液冷/电源"],
            "watch": "看电力设备和数据中心配套是否有订单、产能和毛利改善；没有订单验证时，只能当作AI基建外溢催化。",
            "source": "Barron's",
            "url": "https://www.barrons.com/articles/kkr-nvidia-kuwait-ai-infrastructure-helix-data-centers-36b89c3d",
        },
    ],
    "2026-06-15": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月15日A股强修复，AI硬件/CPO/半导体与机器人方向成为涨停池核心",
            "impact": "今日上证+1.61%、创业板指+5.30%、A股平均股价+3.83%，涨停池145只；AI硬件/CPO/半导体45只、机器人/高端制造26只、化工材料/电子化学品20只居前。",
            "whyHot": "指数和题材同步修复，半导体、光模块、光纤通信曲线均明显上行，说明资金重新回到AI硬件和高端制造的主线抱团。",
            "relatedThemes": ["AI硬件/CPO/半导体", "机器人/高端制造/汽车链", "化工材料/电子化学品", "资源品/金属材料"],
            "watch": "看AI硬件能否从光模块、PCB、半导体材料扩散到容量中军；若次日只剩小票加速，分歧承接要谨慎。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "光纤/数据中心",
            "title": "Amazon与Corning达成数十亿美元光纤供应协议，扩充AI数据中心连接基础设施",
            "impact": "Amazon数据中心扩张直接增加光纤、光缆和连接器需求，A股映射到光模块、光通信、光纤光缆、PCB和数据中心设备。",
            "whyHot": "AI集群瓶颈不只在GPU，也在高速互连和物理网络层；这与今天光模块、光纤通信方向大涨高度一致。",
            "relatedThemes": ["AI硬件/CPO/半导体", "CPO/光通信", "光纤光缆", "AI数据中心"],
            "watch": "看光通信链是否有海外大客户订单、产能扩张和高端产品结构升级支撑，避免只交易情绪弹性。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/tech/amazon-enters-agreement-with-corning-for-optical-fiber-for-data-centers-352c7fa7",
        },
        {
            "category": "科技",
            "heat": "AI基建",
            "title": "Broadcom、Apollo和Blackstone推出350亿美元AI XPV平台，目标到2028年建设20GW算力容量",
            "impact": "平台以Broadcom芯片、网络方案和长期资本绑定AI数据中心扩张，A股映射到AI ASIC、交换芯片、高速互连、PCB、先进封装和服务器链。",
            "whyHot": "这说明AI资本开支开始从单一GPU采购进入芯片、网络、融资和数据中心一体化阶段，利好上游硬件瓶颈。",
            "relatedThemes": ["AI硬件/CPO/半导体", "PCB/先进封装", "AI数据中心", "算力基础设施"],
            "watch": "看A股AI硬件是否能从光模块扩散到PCB、铜连接、先进封装和服务器电源等更宽链条。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/tech/ai/broadcom-apollo-blackstone-launch-35-billion-ai-infrastructure-platform-8fc8f65e",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA、Amazon等支持Neura Robotics最高14亿美元融资，Physical AI和人形机器人产业化升温",
            "impact": "Neura融资用于扩产认知机器人和人形机器人，A股映射到机器人本体、控制器、伺服、减速器、机器视觉和工业自动化。",
            "whyHot": "资金正在把Physical AI从模型叙事推向产能、订单和真实场景验证，和今天机器人/高端制造方向涨停集中相互印证。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "工业自动化", "机器视觉"],
            "watch": "重点看有核心零部件壁垒、真实客户认证和量产能力的公司；单纯概念小票持续性要打折。",
            "source": "WSJ",
            "url": "https://www.wsj.com/tech/ai/nvidia-amazon-back-neura-robotics-1-4-billion-fundraise-ff630662",
        },
        {
            "category": "政策",
            "heat": "国产AI算力",
            "title": "报道称中国拟建设约2万亿元国家AI数据中心网格，并推动80%国产芯片占比",
            "impact": "若规划落地，将强化国产AI芯片、服务器、光通信、电源、液冷、数据中心建设和运营商算力网络需求。",
            "whyHot": "国产化约束会把AI需求传导到半导体设备、先进封装、PCB、光通信和电力基础设施，符合今天AI硬件和半导体的资金方向。",
            "relatedThemes": ["AI硬件/CPO/半导体", "国产算力", "AI数据中心", "电力设备/新能源设备"],
            "watch": "看后续是否有国家部委、运营商或地方项目的正式落地文件；未正式落地前，按产业预期而非确定订单处理。",
            "source": "Tom's Hardware",
            "url": "https://www.tomshardware.com/tech-industry/china-drafts-295-billion-plan-to-build-a-national-ai-data-center-grid-running-on-80-percent-domestic-chips",
        },
        {
            "category": "财经",
            "heat": "算力用电",
            "title": "KKR、NVIDIA、Kuwait Investment Authority和Vistra推出100亿美元AI数据中心基础设施公司Helix",
            "impact": "Helix把NVIDIA算力、KKR资本和Vistra电力资源绑定到AI数据中心建设，A股映射到电力设备、储能、液冷、UPS、电源和数据中心工程。",
            "whyHot": "AI基建的瓶颈正在从芯片扩散到电力接入和能源配套，能解释电力设备、算力用电和数据中心设备的中期关注度。",
            "relatedThemes": ["电力设备/新能源设备", "电力能源/算力用电", "AI数据中心", "液冷/电源"],
            "watch": "看电力设备和数据中心配套是否有订单、产能和毛利改善；没有订单验证时，只能当作AI基建外溢催化。",
            "source": "Barron's",
            "url": "https://www.barrons.com/articles/kkr-nvidia-kuwait-ai-infrastructure-helix-data-centers-36b89c3d",
        },
    ],
    "2026-06-12": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月12日A股指数修复，机器人、高端制造、资源金属和化工材料成为涨停池核心",
            "impact": "今日上证+1.12%、创业板指+0.50%、证券指数+3.50%，涨停池89只；机器人/高端制造16只、资源品/金属材料15只、化工材料/电子化学品14只居前。",
            "whyHot": "指数修复但半导体、光模块仍偏弱，资金从AI硬件短线分歧中切到机器人、航空高端制造、钼铜等资源品和化工材料，体现顺周期与上游瓶颈并行。",
            "relatedThemes": ["机器人/高端制造/汽车链", "资源品/金属材料", "化工材料/电子化学品", "证券"],
            "watch": "看机器人和资源金属能否从首板扩散到容量中军；若券商继续放量，市场风险偏好会支撑题材轮动延续。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA、Amazon等支持Neura Robotics最高14亿美元融资，Physical AI和人形机器人产业化升温",
            "impact": "Neura融资用于扩产认知机器人和人形机器人，目标到2030年制造数百万台机器人，A股映射到机器人本体、控制器、伺服、减速器、机器视觉和工业自动化。",
            "whyHot": "这类融资把Physical AI从模型叙事推到产能和订单验证阶段，和今天机器人/高端制造方向涨停集中相互印证。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "工业自动化", "机器视觉"],
            "watch": "重点看有核心零部件壁垒、真实客户认证和量产能力的公司；单纯概念小票持续性要打折。",
            "source": "WSJ / Barron's",
            "url": "https://www.wsj.com/tech/ai/nvidia-amazon-back-neura-robotics-1-4-billion-fundraise-ff630662",
        },
        {
            "category": "财经",
            "heat": "资源金属",
            "title": "铜价接近高位后震荡，市场继续交易AI用电、供应短缺和潜在关税带来的资源品弹性",
            "impact": "铜价高位震荡会提升市场对铜、钼、锗等上游资源的关注，A股映射到金钼股份、洛阳钼业、铜陵有色等资源品方向。",
            "whyHot": "AI数据中心、电网扩容和制造业补库都绕不开基础金属，资源品在指数修复日容易成为顺周期弹性和稀缺瓶颈的交集。",
            "relatedThemes": ["资源品/金属材料", "电力能源/算力用电", "高股息资源"],
            "watch": "看资源股是否有价格、库存和产量约束共振；若只是指数修复日补涨，次日承接需要更谨慎。",
            "source": "Investor's Business Daily",
            "url": "https://www.investors.com/news/copper-price-trump-tariffs-loom-bhp-rio-fcx-mining-stocks-buy-points/",
        },
        {
            "category": "科技",
            "heat": "Apple AI",
            "title": "NVIDIA保密计算支持Apple Private Cloud Compute扩容，Apple Intelligence服务端推理接入Blackwell GPU",
            "impact": "Apple Intelligence服务端推理需要高性能GPU、安全计算和云基础设施，A股映射到AI服务器、先进封装、端侧AI、苹果链和数据中心设备。",
            "whyHot": "苹果AI不是单纯端侧更新，私密云推理会继续强化推理算力、服务器链和先进封装的中期需求。",
            "relatedThemes": ["AI硬件/CPO/半导体", "端侧AI", "苹果链", "AI数据中心"],
            "watch": "今天AI硬件短线承压，后续要看服务器、先进封装和苹果链是否有订单线索支撑，而不是只做发布会情绪。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/nvidia-confidential-computing-apple-private-cloud-compute/",
        },
        {
            "category": "科技",
            "heat": "本地AI",
            "title": "NVIDIA优化Google DeepMind DiffusionGemma，推动本地AI在RTX、DGX Spark和GeForce GPU上运行",
            "impact": "本地低延迟AI、AI PC和工作站推理会带动GPU、存储、散热、电源、端侧AI和消费电子硬件链需求。",
            "whyHot": "当云端AI硬件出现短线分歧时，本地推理和AI PC是资金寻找新分支的重要方向。",
            "relatedThemes": ["AI硬件/CPO/半导体", "端侧AI", "消费电子", "AI应用/数据要素/服务"],
            "watch": "看端侧AI和消费电子链是否有产品周期、换机预期和真实订单跟上；没有订单验证的情绪扩散不宜高估。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/rtx-ai-garage-local-gemma-diffusion/",
        },
        {
            "category": "科技",
            "heat": "AI制造",
            "title": "Axios报道Jeff Bezos关联工业AI公司Prometheus完成120亿美元融资，AI制造与智能工厂热度升温",
            "impact": "工业AI大额融资强化AI进入制造、设计和原型验证环节的趋势，A股映射到工业软件、自动化、机器人、智能制造和数据中心基础设施。",
            "whyHot": "AI从互联网应用扩散到制造业流程，和今天高端制造、机器人、航空链的资金偏好形成产业逻辑共振。",
            "relatedThemes": ["机器人/高端制造/汽车链", "AI应用/数据要素/服务", "工业软件", "智能制造"],
            "watch": "看A股工业AI能否出现真实订单和软件收入弹性；纯概念公司仍需避开估值空转。",
            "source": "Axios",
            "url": "https://www.axios.com/newsletters/axios-pro-rata-c007d2f6-d2d2-41cc-96e2-ea8c5b760f11",
        },
    ],
    "2026-06-11": [
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "6月11日A股收盘分化，半导体、电子化学品和稀缺资源方向成为涨停池核心",
            "impact": "今日指数整体回落，上证-0.16%、创业板指-1.13%、A股平均股价-0.73%，但涨停池仍有69只，AI硬件/CPO/半导体、化工材料/电子化学品、资源品/金属材料三条线最集中。",
            "whyHot": "弱指数环境下仍有成组涨停，说明资金不是普涨修复，而是在半导体材料、电子特气、钨锗等上游瓶颈方向做结构性抱团。",
            "relatedThemes": ["AI硬件/CPO/半导体", "化工材料/电子化学品", "资源品/金属材料"],
            "watch": "看半导体材料和稀缺资源能否从小票封板扩散到有产能、客户认证和价格弹性的容量票。",
            "source": "本地行情数据：东方财富涨停池与指数接口",
            "url": "",
        },
        {
            "category": "科技",
            "heat": "本地AI",
            "title": "NVIDIA优化Google DeepMind DiffusionGemma，推动本地AI在RTX、DGX Spark和GeForce GPU上运行",
            "impact": "事件指向本地低延迟AI、AI PC、工作站和端侧推理，A股映射到AI芯片、服务器、消费电子、端侧AI和算力硬件链。",
            "whyHot": "DiffusionGemma强调并行生成和本地运行，会强化市场对高性能GPU、AI PC、边缘推理和端侧模型部署的关注。",
            "relatedThemes": ["AI硬件/CPO/半导体", "端侧AI", "消费电子", "AI应用/数据要素/服务"],
            "watch": "看AI硬件能否从云端GPU叙事扩展到本地推理、工作站和AI PC换机，重点观察核心零部件和服务器链承接。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/rtx-ai-garage-local-gemma-diffusion/",
        },
        {
            "category": "科技",
            "heat": "Apple AI",
            "title": "NVIDIA保密计算支持Apple Private Cloud Compute扩容，Apple Intelligence服务端推理接入Blackwell GPU",
            "impact": "这条新闻把Apple Intelligence、Google Cloud和NVIDIA Blackwell连接起来，A股映射到端侧AI、苹果链、服务器、先进封装和数据中心基础设施。",
            "whyHot": "苹果AI并不只靠端侧，服务端私密推理需要高性能GPU和安全计算架构，能提高市场对AI推理基础设施的重估。",
            "relatedThemes": ["AI硬件/CPO/半导体", "端侧AI", "苹果链", "AI数据中心"],
            "watch": "看苹果链是否有真实硬件升级和订单反馈；若只停留在WWDC情绪，持续性要等产业链验证。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/nvidia-confidential-computing-apple-private-cloud-compute/",
        },
        {
            "category": "科技",
            "heat": "HBM/内存",
            "title": "NVIDIA与SK海力士签署多年期技术合作，推进下一代AI内存和AI工厂建设",
            "impact": "事件直接指向HBM、下一代内存、先进封装和AI服务器扩容，A股映射到存储芯片、半导体材料、先进封装、PCB和测试设备。",
            "whyHot": "AI基础设施的瓶颈从GPU外溢到内存、封装和材料，和今天半导体材料、电子化学品涨停集中相互印证。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片/HBM", "半导体材料", "PCB/先进封装"],
            "watch": "看存储、先进封装和电子化学品是否有持续放量，而不是只停留在单日涨停情绪。",
            "source": "NVIDIA Newsroom",
            "url": "https://nvidianews.nvidia.com/news/nvidia-and-sk-hynix-announce-multiyear-technology-partnership-to-advance-memory-for-ai-factories",
        },
        {
            "category": "政策",
            "heat": "AI数据",
            "title": "国家数据局发布行业高质量数据集建设方案，国家层面首次系统部署数据赋能AI",
            "impact": "方案聚焦科学研究、工业制造、低空经济、具身智能等重点领域，A股映射到数据要素、数据标注、AI应用和行业智能化。",
            "whyHot": "高质量数据集是模型训练和行业AI落地的核心燃料，政策会提升数据资源、数据基础设施和AI应用公司的关注度。",
            "relatedThemes": ["AI应用/数据要素/服务", "数据标注", "行业大模型", "具身智能"],
            "watch": "看数据要素和AI应用是否从政策催化转为订单与应用闭环，优先关注有行业数据和客户场景的公司。",
            "source": "国家数据局/央视新闻",
            "url": "https://www.nda.gov.cn/sjj/swdt/mtsy/0608/20260608214755016924597_pc.html",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "NVIDIA与LG集团建设AI Factory，合作覆盖机器人、自动驾驶、数据中心和GPU云",
            "impact": "事件把Physical AI、机器人、自动驾驶、AI数据中心和GPU云放到同一条产业链，A股映射到机器人本体、伺服控制、机器视觉、工业自动化和数据中心设备。",
            "whyHot": "今天机器人/高端制造方向仍有涨停扩散，海外AI Factory和Physical AI事件能强化产业链从概念到场景落地的叙事。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "AI数据中心", "边缘AI"],
            "watch": "看机器人链是否出现有订单、有控制器/伺服/机器视觉壁垒的中军承接，而不是只做情绪轮动。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/nvidia-and-lg-group-ai-factory/",
        },
    ],
    "2026-06-09": [
        {
            "category": "政策",
            "heat": "机器人政策",
            "title": "工信部、国务院国资委启动2026年度人形机器人与具身智能实景实训专项行动",
            "impact": "专项行动把人形机器人从样机展示推向真实生产生活场景验证，A股映射到机器人本体、伺服电机、减速器、传感器、机器视觉、工业软件和应用服务商。",
            "whyHot": "政策明确要打造实景实训空间、组建创新应用联合体、攻关实用化作业技能，能把机器人主题从概念催化推向场景落地和订单验证。",
            "relatedThemes": ["机器人/高端制造/汽车链", "具身智能", "工业自动化", "机器视觉"],
            "watch": "看机器人链是否从情绪板扩散到有真实应用场景、整机交付和核心零部件壁垒的容量票。",
            "source": "人民网",
            "url": "https://finance.people.com.cn/n1/2026/0609/c1004-40736724.html",
        },
        {
            "category": "政策",
            "heat": "AI数据",
            "title": "国家数据局发布行业高质量数据集建设方案，国家层面首次系统部署数据赋能AI",
            "impact": "方案聚焦科学研究、工业制造、智慧能源、交通运输、金融服务等重点领域，以及低空经济、具身智能、智能驾驶等创新领域，A股映射到数据要素、数据标注、AI应用、算力和行业智能化。",
            "whyHot": "高质量数据集是模型训练和行业AI落地的核心燃料，政策首次系统部署会提升数据资源、数据基础设施和AI应用公司的关注度。",
            "relatedThemes": ["AI应用/数据要素/服务", "数据标注", "行业大模型", "智能驾驶/低空经济"],
            "watch": "看数据要素和AI应用是否有政策驱动的持续性，重点区分有行业数据、客户场景和商业闭环的公司。",
            "source": "国家数据局/央视新闻",
            "url": "https://www.nda.gov.cn/sjj/swdt/mtsy/0608/20260608214755016924597_pc.html",
        },
        {
            "category": "科技",
            "heat": "苹果WWDC",
            "title": "WWDC26：Apple发布新一代Apple Intelligence、Siri AI和一系列软件升级",
            "impact": "Apple AI和Siri升级会影响端侧AI、苹果链、消费电子、AI应用和开发者生态预期，A股映射到端侧AI芯片、声学/光学、消费电子零部件和AI应用服务。",
            "whyHot": "苹果生态如果重新强化AI入口，市场会重新定价端侧AI硬件换机、开发者工具和本地模型部署机会。",
            "relatedThemes": ["端侧AI", "消费电子", "苹果链", "AI应用/数据要素/服务"],
            "watch": "看苹果链和端侧AI是否出现真实订单或产品升级线索；若只有发布会情绪，持续性要等产业链反馈确认。",
            "source": "Apple Newsroom",
            "url": "https://www.apple.com.cn/newsroom/2026/06/apple-unveils-next-generation-of-apple-intelligence-siri-ai-and-more/",
        },
        {
            "category": "科技",
            "heat": "HBM/内存",
            "title": "英伟达与SK海力士签署多年期技术合作，推进下一代AI内存和AI基础设施",
            "impact": "事件直接指向HBM、下一代内存、AI加速器配套和数据中心扩容，A股映射到存储芯片、半导体材料、先进封装、PCB、服务器和测试设备。",
            "whyHot": "AI基础设施的真实瓶颈正在从GPU扩散到HBM、内存和先进封装，符合市场今天半导体、PCB和材料链走强的新闻催化。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片/HBM", "半导体材料", "PCB/先进封装"],
            "watch": "看HBM/存储、先进封装、电子化学品和AI服务器容量票能否持续放量，而不是只停留在小票情绪冲板。",
            "source": "NVIDIA Newsroom",
            "url": "https://nvidianews.nvidia.com/news/nvidia-and-sk-hynix-announce-multiyear-technology-partnership-to-advance-memory-for-ai-factories",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "英伟达与LG集团建设AI Factory，合作覆盖机器人、自动驾驶、数据中心和GPU云",
            "impact": "这条新闻把黄仁勋韩国行与Physical AI落地连接起来，A股映射到机器人本体、伺服电机、机器视觉、工业自动化、数据中心设备和边缘AI。",
            "whyHot": "LG合作不是单一芯片采购，而是AI工厂、机器人基础模型和工业场景组合，能强化机器人/高端制造主线的产业叙事。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "AI数据中心", "边缘AI"],
            "watch": "看机器人链是否由政策和海外产业催化共振，扩散到有订单、有控制器/伺服/机器视觉壁垒的中军承接。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/nvidia-and-lg-group-ai-factory/",
        },
        {
            "category": "财经",
            "heat": "A股盘面",
            "title": "A股科技股大涨，半导体、PCB和AI硬件方向成为6月9日盘面核心",
            "impact": "盘面从前一日弱指数转为科技股修复，上证重回4000点，创业板和科创方向更强，A股映射到半导体、PCB、AI硬件、机器人和数据要素的联动修复。",
            "whyHot": "今日市场不是单条新闻驱动，而是海外AI链、国内数据政策、机器人专项行动和半导体产业预期共同推动风险偏好修复。",
            "relatedThemes": ["AI硬件/CPO/半导体", "PCB/先进封装", "机器人/高端制造/汽车链", "AI应用/数据要素/服务"],
            "watch": "看科技股强修复后能否转成连续主线，重点观察容量票、首板晋级率和次日分歧承接。",
            "source": "每日经济新闻",
            "url": "https://www.nbd.com.cn/articles/2026-06-09/4421119.html",
        },
    ],
    "2026-06-08": [
        {
            "category": "科技",
            "heat": "黄仁勋访韩",
            "title": "英伟达与SK海力士签署多年期技术合作，推进下一代AI内存和AI基础设施",
            "impact": "事件直接指向HBM、下一代内存、AI加速器配套和数据中心扩容，A股映射到存储芯片、半导体材料、先进封装、服务器和PCB链。",
            "whyHot": "黄仁勋访韩期间，市场关注点从单纯GPU扩产延伸到HBM和内存供应约束；这比普通板块轮动更接近真实产业催化。",
            "relatedThemes": ["AI硬件/CPO/半导体", "存储芯片/HBM", "半导体材料", "AI服务器"],
            "watch": "看HBM/存储、先进封装、电子化学品和AI服务器容量票能否出现持续放量，而不是只看小票情绪冲板。",
            "source": "NVIDIA Newsroom",
            "url": "https://nvidianews.nvidia.com/news/nvidia-and-sk-hynix-announce-multiyear-technology-partnership-to-advance-memory-for-ai-factories",
        },
        {
            "category": "科技",
            "heat": "韩国数据中心",
            "title": "黄仁勋称英伟达将在韩国新万金建立数据中心，回应现代汽车集团相关建议",
            "impact": "这条新闻把英伟达韩国行落到具体AI基础设施投资地点，A股映射到数据中心、电力设备、液冷、服务器、IDC建设和AI算力基础设施。",
            "whyHot": "市场不只关注黄仁勋访问本身，更关注是否形成可追踪的AI基础设施落地项目；新万金数据中心会强化韩国AI Valley和算力建设叙事。",
            "relatedThemes": ["AI数据中心", "电力能源/算力用电", "液冷/电力设备", "AI服务器"],
            "watch": "看电力、液冷、服务器和IDC链条是否出现容量票承接；若只有概念小票冲高，持续性要打折。",
            "source": "韩联社",
            "url": "https://cn.yna.co.kr/view/ACK20260608003600881",
        },
        {
            "category": "科技",
            "heat": "Physical AI",
            "title": "英伟达与LG集团建设AI Factory，合作方向覆盖机器人、自动驾驶、数据中心和GPU云",
            "impact": "这条新闻把黄仁勋韩国行与Physical AI落地连接起来，A股映射到机器人本体、伺服电机、机器视觉、工业自动化、数据中心设备和边缘AI。",
            "whyHot": "LG合作不是单一芯片采购，而是AI工厂、机器人基础模型和工业场景的组合，能强化机器人/高端制造主线的产业叙事。",
            "relatedThemes": ["机器人/高端制造/汽车链", "Physical AI", "AI数据中心", "边缘AI"],
            "watch": "看机器人链是否由情绪首板扩散到有订单、有控制器/伺服/机器视觉壁垒的中军承接。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com/blog/nvidia-and-lg-group-ai-factory/",
        },
        {
            "category": "科技",
            "heat": "AI云",
            "title": "NVIDIA与NAVER Cloud扩大AI基础设施合作，建设面向全球需求的AI Factory",
            "impact": "事件指向主权AI云、AI Factory和GPU云服务扩张，A股可映射到算力租赁、数据中心、液冷、电力设备、光模块和服务器供应链。",
            "whyHot": "NAVER是韩国本土云和互联网核心公司，合作强化韩国AI云基础设施建设，并提升市场对AI算力需求外溢的关注。",
            "relatedThemes": ["AI算力/云基础设施", "CPO/光通信", "液冷/电力设备", "服务器"],
            "watch": "看光模块、液冷、电源、电网和服务器链条是否出现由海外AI云订单驱动的趋势承接。",
            "source": "NVIDIA Newsroom",
            "url": "https://nvidianews.nvidia.com/news/naver-ai-infrastructure",
        },
        {
            "category": "科技",
            "heat": "AI制造",
            "title": "英伟达与三星AI Factory项目推进，三星半导体AI工厂规划使用超过5万块英伟达GPU",
            "impact": "三星AI工厂把GPU需求与半导体制造数字孪生、EDA、制程优化连接起来，映射到半导体设备、EDA、先进制造软件和AI服务器。",
            "whyHot": "这不是消费电子新闻，而是AI正在进入半导体制造流程本身，产业链会关注EDA加速、工厂仿真和先进制程效率提升。",
            "relatedThemes": ["半导体设备", "EDA/工业软件", "AI服务器", "先进制造"],
            "watch": "看A股半导体设备、工业软件和服务器链能否从新闻催化转成订单或业绩线索。",
            "source": "NVIDIA Newsroom",
            "url": "https://nvidianews.nvidia.com/news/south-korea-ai-infrastructure",
        },
        {
            "category": "科技",
            "heat": "苹果WWDC",
            "title": "苹果WWDC26于6月8日开幕，官方预告AI进展、软件平台和开发者工具更新",
            "impact": "Apple AI进展会影响端侧AI、消费电子、AI应用生态和苹果链预期，A股映射到消费电子、AI终端、端侧模型、AR/视觉交互和软件生态。",
            "whyHot": "苹果如果在AI能力、Siri或开发者工具上补课，市场会重新评估端侧AI硬件升级和应用生态机会。",
            "relatedThemes": ["端侧AI", "消费电子", "AI应用/数据要素/服务", "苹果链"],
            "watch": "看发布会后端侧AI、苹果链和AI应用方向是否有真实产品更新支撑，避免只炒预期。",
            "source": "Apple Newsroom",
            "url": "https://www.apple.com/newsroom/2026/05/apple-kicks-off-worldwide-developers-conference-on-june-8/",
        },
        {
            "category": "财经",
            "heat": "科技股情绪",
            "title": "黄仁勋在首尔称AI基础设施仍处早期，并把科技股回调视为买入机会",
            "impact": "这条消息影响风险偏好和AI基础设施估值锚，A股映射到AI硬件、数据中心、电力和机器人链的情绪修复。",
            "whyHot": "在全球科技股调整背景下，英伟达CEO对AI基建周期的表态会影响资金是否继续给AI产业链高估值。",
            "relatedThemes": ["AI基础设施", "AI硬件/CPO/半导体", "电力能源/算力用电", "机器人/高端制造/汽车链"],
            "watch": "看美股AI链和A股硬件链是否同步止跌；若龙头承接弱，新闻只能当情绪修复而不是趋势确认。",
            "source": "联合早报",
            "url": "https://www.zaobao.com.sg/finance/world/story20260608-9171714",
        },
    ]
}

THEME_BY_INDUSTRY = {
    "元件": "AI硬件/CPO/半导体",
    "光学光电": "AI硬件/CPO/半导体",
    "通信设备": "AI硬件/CPO/半导体",
    "消费电子": "AI硬件/CPO/半导体",
    "半导体": "AI硬件/CPO/半导体",
    "其他电子": "AI硬件/CPO/半导体",
    "电子化学": "AI硬件/CPO/半导体",
    "军工电子": "AI硬件/CPO/半导体",
    "计算机设": "AI应用/数据要素/服务",
    "IT服务Ⅱ": "AI应用/数据要素/服务",
    "软件开发": "AI应用/数据要素/服务",
    "专业服务": "AI应用/数据要素/服务",
    "广告营销": "AI应用/数据要素/服务",
    "数字媒体": "AI应用/数据要素/服务",
    "电力": "电力能源/算力用电",
    "煤炭开采": "资源品/煤炭/高股息",
    "焦炭Ⅱ": "资源品/煤炭/高股息",
    "金属新材": "资源品/金属材料",
    "工业金属": "资源品/金属材料",
    "小金属": "资源品/金属材料",
    "冶钢原料": "资源品/金属材料",
    "炼化及贸": "化工材料/电子化学品",
    "化学原料": "化工材料/电子化学品",
    "化学制品": "化工材料/电子化学品",
    "塑料": "化工材料/电子化学品",
    "玻璃玻纤": "化工材料/电子化学品",
    "电池": "化工材料/电子化学品",
    "农化制品": "化工材料/电子化学品",
    "通用设备": "机器人/高端制造/汽车链",
    "专用设备": "机器人/高端制造/汽车链",
    "轨交设备": "机器人/高端制造/汽车链",
    "自动化设": "机器人/高端制造/汽车链",
    "电机Ⅱ": "机器人/高端制造/汽车链",
    "航空装备": "机器人/高端制造/汽车链",
    "航天装备": "机器人/高端制造/汽车链",
    "汽车零部": "机器人/高端制造/汽车链",
    "商用车": "机器人/高端制造/汽车链",
    "其他电源": "电力设备/新能源设备",
    "光伏设备": "电力设备/新能源设备",
    "电网设备": "电力设备/新能源设备",
    "房地产开": "地产基建/城市更新",
    "基础建设": "地产基建/城市更新",
    "装修建材": "地产基建/城市更新",
    "工程咨询": "地产基建/城市更新",
    "专业工程": "地产基建/城市更新",
    "环境治理": "环保/公用事业",
    "环保设备": "环保/公用事业",
    "小家电": "消费零售/家居服饰",
    "家居用品": "消费零售/家居服饰",
    "家电零部": "消费零售/家居服饰",
    "服装家纺": "消费零售/家居服饰",
    "饰品": "消费零售/家居服饰",
    "休闲食品": "消费零售/家居服饰",
    "饮料乳品": "消费零售/家居服饰",
    "一般零售": "消费零售/家居服饰",
    "包装印刷": "消费零售/家居服饰",
    "造纸": "消费零售/家居服饰",
    "白酒Ⅱ": "消费零售/家居服饰",
    "化学纤维": "化工材料/电子化学品",
    "医疗器械": "医药医疗",
    "生物制品": "医药医疗",
    "航运港口": "航运港口/交运",
    "贸易Ⅱ": "贸易/综合",
}


def now_text():
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S +08:00")


def fetch_json(url, params=None, referer="https://quote.eastmoney.com/", retries=4, timeout=28):
    full_url = url
    if params:
        full_url = url + "?" + urllib.parse.urlencode(params)
    last_error = None
    for attempt in range(retries):
        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": referer,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "close",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(0.4 * (attempt + 1))
    raise last_error


def fetch_zt_pool(date_compact):
    rows = []
    meta = {}
    for page in range(10):
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": str(page),
            "pagesize": "50",
            "sort": "fbt:asc",
            "date": date_compact,
            "_": int(time.time() * 1000),
        }
        payload = fetch_json(
            "https://push2ex.eastmoney.com/getTopicZTPool",
            params=params,
            referer="https://quote.eastmoney.com/ztb/detail",
        )
        data = payload.get("data") or {}
        meta = {"qdate": data.get("qdate"), "tc": data.get("tc")}
        pool = data.get("pool") or []
        rows.extend(pool)
        if len(pool) < 50:
            break
    return rows, meta


def fetch_kline(secid, date_compact, limit=190):
    params = {
        "secid": secid,
        "klt": "101",
        "fqt": "1",
        "lmt": str(limit),
        "end": date_compact,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "_": int(time.time() * 1000),
    }
    hosts = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://push2.eastmoney.com/api/qt/stock/kline/get",
        "https://push2test.eastmoney.com/api/qt/stock/kline/get",
    )
    last_error = None
    for host in hosts:
        try:
            payload = fetch_json(host, params=params, retries=3, timeout=20)
            points = []
            for row in (payload.get("data") or {}).get("klines") or []:
                date, open_, close, high, low, volume, amount, amplitude, pct, change, turnover = row.split(",")
                points.append(
                    {
                        "date": date,
                        "open": round(float(open_), 2),
                        "close": round(float(close), 2),
                        "high": round(float(high), 2),
                        "low": round(float(low), 2),
                        "volume": float(volume),
                        "pct": round(float(pct), 2),
                        "change": round(float(change), 2),
                    }
                )
            if points:
                return points
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"kline failed {secid}: {last_error}")


def fetch_sina_kline(symbol, limit=190):
    url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData"
    params = {"symbol": symbol, "scale": "240", "ma": "no", "datalen": str(limit)}
    rows = fetch_json(url, params=params, referer="https://finance.sina.com.cn/", retries=4, timeout=20)
    points = []
    previous_close = None
    for row in rows or []:
        close = float(row.get("close") or 0)
        change = close - previous_close if previous_close else 0
        pct = (change / previous_close * 100) if previous_close else 0
        points.append(
            {
                "date": row.get("day"),
                "open": round(float(row.get("open") or 0), 3),
                "close": round(close, 3),
                "high": round(float(row.get("high") or 0), 3),
                "low": round(float(row.get("low") or 0), 3),
                "volume": float(row.get("volume") or 0),
                "pct": round(pct, 2),
                "change": round(change, 3),
            }
        )
        previous_close = close
    if not points:
        raise RuntimeError(f"sina kline failed {symbol}: empty rows")
    return points


def pct_limit_for_series(series_id):
    return {
        "shanghai": 8,
        "chinext": 12,
        "securities": 12,
        "avg_price": 8,
    }.get(series_id, 20)


def fetch_stable_eastmoney_kline(series_id, secid, date_compact, limit=190):
    best = None
    best_abs_pct = float("inf")
    threshold = pct_limit_for_series(series_id)
    for attempt in range(8):
        points = fetch_kline(secid, date_compact, limit=limit)
        latest = next((point for point in reversed(points) if point["date"] == f"{date_compact[:4]}-{date_compact[4:6]}-{date_compact[6:8]}"), None)
        if not latest:
            continue
        abs_pct = abs(float(latest.get("pct") or 0))
        if abs_pct < best_abs_pct:
            best = points
            best_abs_pct = abs_pct
        if abs_pct <= threshold:
            return points
        time.sleep(0.3 * (attempt + 1))
    if best and best_abs_pct <= threshold:
        return best
    raise RuntimeError(f"{series_id} kline pct abnormal after retries: {best_abs_pct:.2f}%")


def fetch_eastmoney_quote_point(secid, target_date):
    params = {
        "secid": secid,
        "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f59,f60,f169,f170,f171",
        "_": int(time.time() * 1000),
    }
    hosts = (
        "https://push2.eastmoney.com/api/qt/stock/get",
        "https://push2his.eastmoney.com/api/qt/stock/get",
        "https://push2test.eastmoney.com/api/qt/stock/get",
    )
    last_error = None
    for attempt in range(8):
        for host in hosts:
            try:
                payload = fetch_json(host, params=params, retries=2, timeout=12)
                data = payload.get("data") or {}
                scale = 10 ** int(data.get("f59") or 2)
                pct = round(float(data.get("f170") or 0) / 100, 2)
                if abs(pct) > pct_limit_for_series("avg_price"):
                    continue
                return {
                    "date": target_date,
                    "open": round(float(data.get("f46") or 0) / scale, 2),
                    "close": round(float(data.get("f43") or 0) / scale, 2),
                    "high": round(float(data.get("f44") or 0) / scale, 2),
                    "low": round(float(data.get("f45") or 0) / scale, 2),
                    "volume": float(data.get("f47") or 0),
                    "pct": pct,
                    "change": round(float(data.get("f169") or 0) / scale, 2),
                }
            except Exception as exc:
                last_error = exc
        time.sleep(0.3 * (attempt + 1))
    if secid == "47.800005":
        return fetch_all_a_average_point(target_date)
    raise RuntimeError(f"quote failed {secid}: {last_error}")


def safe_number(value):
    try:
        if value in (None, "", "-"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_all_a_average_point(target_date):
    rows = []
    for page in range(1, 90):
        params = {
            "pn": page,
            "pz": 100,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f2,f3,f5,f12,f14,f15,f16,f17",
            "_": int(time.time() * 1000),
        }
        payload = fetch_json("https://push2delay.eastmoney.com/api/qt/clist/get", params=params, retries=4, timeout=20)
        diff = (payload.get("data") or {}).get("diff") or []
        rows.extend(diff)
        if len(diff) < 100:
            break
    valid = [
        row
        for row in rows
        if safe_number(row.get("f2")) > 0
        and safe_number(row.get("f17")) > 0
        and safe_number(row.get("f15")) > 0
        and safe_number(row.get("f16")) > 0
        and abs(safe_number(row.get("f3"))) <= 30
    ]
    if len(valid) < 1500:
        raise RuntimeError(f"all-A average fallback has too few rows: {len(valid)}")
    close = sum(safe_number(row.get("f2")) for row in valid) / len(valid)
    pct = sum(safe_number(row.get("f3")) for row in valid) / len(valid)
    previous_close = close / (1 + pct / 100) if pct > -99 else close
    return {
        "date": target_date,
        "open": round(sum(safe_number(row.get("f17")) for row in valid) / len(valid), 2),
        "close": round(close, 2),
        "high": round(sum(safe_number(row.get("f15")) for row in valid) / len(valid), 2),
        "low": round(sum(safe_number(row.get("f16")) for row in valid) / len(valid), 2),
        "volume": sum(safe_number(row.get("f5")) for row in valid),
        "pct": round(pct, 2),
        "change": round(close - previous_close, 2),
        "cachedReason": "官方平均股价quote临时不可用，使用全A有效样本均值估算",
    }


def format_time(value):
    raw = str(int(value or 0)).zfill(6)
    return f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}" if raw != "000000" else ""


def code_with_market(row):
    return str(row.get("c") or "") + (".SH" if row.get("m") == 1 else ".SZ")


def money(value):
    value = float(value or 0)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿"
    if value >= 10_000:
        return f"{value / 10_000:.0f}万"
    return f"{value:.0f}"


def theme_for(row):
    return THEME_BY_INDUSTRY.get(row.get("hybk") or "", "其他轮动")


def reason_for(theme):
    mapping = {
        "AI硬件/CPO/半导体": "半导体、光学光电、元件和通信设备继续活跃，资金围绕AI硬件、CPO、存储芯片和电子化学品寻找弹性。",
        "电力能源/算力用电": "迎峰度夏、电力负荷和AI数据中心用电预期共振，电力方向继续承担资金承接。",
        "资源品/煤炭/高股息": "煤炭和焦炭维持逆势防御与高股息逻辑，大有能源继续打开短线高度。",
        "资源品/金属材料": "金属材料和工业金属更多体现资源品轮动和材料端弹性。",
        "化工材料/电子化学品": "电子化学品、化学原料和塑料材料强势，既有半导体材料映射，也有低位材料补涨。",
        "机器人/高端制造/汽车链": "通用设备、专用设备、汽车零部件和轨交设备活跃，受机器人、制造业设备和汽车链轮动带动。",
        "电力设备/新能源设备": "电力设备和新能源设备补涨，更多与电力、储能、光伏和电源链条相关。",
        "地产基建/城市更新": "地产、基建和工程咨询局部轮动，但不是当天第一主线。",
        "消费零售/家居服饰": "消费、家居、饰品和包装方向有扩散，主要承担轮动补涨。",
        "AI应用/数据要素/服务": "AI应用、IT服务和软件端局部活跃，强度弱于AI硬件和材料端。",
    }
    return mapping.get(theme, "非主线个股以事件驱动和低位轮动为主，持续性需要次日确认。")


def stock_position(ladder):
    if ladder >= 4:
        return "空间核心"
    if ladder >= 3:
        return "高度核心"
    if ladder == 2:
        return "连板前排"
    return "首板扩散"


def stock_obj(row):
    ladder = int(row.get("lbc") or row.get("zttj", {}).get("ct") or 1)
    price = round(float(row.get("p") or 0) / 1000, 3)
    theme = theme_for(row)
    return {
        "code": code_with_market(row),
        "name": row.get("n") or "",
        "theme": theme,
        "reason": reason_for(theme),
        "position": stock_position(ladder),
        "firstLimitTime": format_time(row.get("fbt")),
        "lastLimitTime": format_time(row.get("lbt")),
        "consecutive": ladder,
        "reopenCount": int(row.get("zbc") or 0),
        "pct": round(float(row.get("zdp") or 0), 2),
        "price": price,
        "amount": money(row.get("amount")),
        "amountRaw": round(float(row.get("amount") or 0), 2),
        "sealFund": money(row.get("fund")),
        "turnover": round(float(row.get("hs") or 0), 2),
        "category": row.get("hybk") or "未分类",
    }


def board_text(height):
    height = int(height or 0)
    return "首板" if height <= 1 else f"{height}连板"


def format_pct(value):
    number = float(value or 0)
    prefix = "+" if number > 0 else ""
    return f"{prefix}{number:.2f}%"


def join_names(rows, limit=4):
    names = []
    for item in rows[:limit]:
        if isinstance(item, dict):
            names.append(item.get("name") or "")
        else:
            names.append(str(item))
    names = [name for name in names if name]
    if not names:
        return "暂无"
    return "、".join(names) + ("等" if len(rows) > limit else "")


def theme_category(theme):
    if any(keyword in theme for keyword in ("AI", "机器人", "半导体", "电子", "光", "通信")):
        return "科技"
    return "财经"


def chart_snapshot(source, target_date):
    snapshot = {}
    for series in (source or {}).get("series", []):
        latest = next((point for point in reversed(series.get("points", [])) if point.get("date") == target_date), None)
        if latest:
            snapshot[series["id"]] = latest
        elif series.get("latestDate") == target_date:
            snapshot[series["id"]] = {
                "date": target_date,
                "close": series.get("latestClose"),
                "pct": series.get("latestPct"),
                "change": series.get("latestChange"),
            }
    return snapshot


def top_theme_name(by_theme, candidates, exclude=None):
    blocked = set(exclude or [])
    for name in candidates:
        if name in by_theme and name not in blocked:
            return name
    for name in by_theme:
        if name not in blocked:
            return name
    return None


def build_summary(target_date, date_compact, meta, stocks, themes, by_theme, charts):
    high_board = sorted([stock for stock in stocks if stock["consecutive"] >= 2], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
    max_height = high_board[0]["consecutive"] if high_board else max((stock["consecutive"] for stock in stocks), default=1)
    top_theme = themes[0] if themes else None
    second_theme = themes[1] if len(themes) > 1 else None
    third_theme = themes[2] if len(themes) > 2 else None
    tech_theme = top_theme_name(by_theme, ["AI硬件/CPO/半导体", "AI应用/数据要素/服务", "化工材料/电子化学品"])
    multi_board_count = sum(1 for stock in stocks if stock["consecutive"] >= 2)
    reopen_count = sum(1 for stock in stocks if stock["reopenCount"] > 0)
    early_count = sum(1 for stock in stocks if stock["firstLimitTime"] and stock["firstLimitTime"] <= "09:35:00")

    summary = [
        f"{target_date}收盘，东方财富涨停池 qdate={date_compact}、tc={meta.get('tc')}；最高高度为{board_text(max_height)}，{join_names(high_board or stocks, 3)}处在连板前列。",
    ]
    if charts.get("shanghai") and charts.get("chinext") and charts.get("avg_price"):
        index_pcts = [charts[key].get("pct", 0) for key in ("shanghai", "chinext", "avg_price")]
        if all(value > 0 for value in index_pcts):
            index_context = "指数修复下资金风险偏好回升，科技成长与题材弹性更容易扩散"
        elif all(value < 0 for value in index_pcts):
            index_context = "指数承压下资金更偏结构性抱团"
        else:
            index_context = "指数分化下资金更重视主线强弱和前排承接"
        summary.append(
            f"指数端，上证{format_pct(charts['shanghai'].get('pct'))}，创业板指{format_pct(charts['chinext'].get('pct'))}，A股平均股价{format_pct(charts['avg_price'].get('pct'))}，{index_context}。"
        )
    if top_theme:
        theme_text = f"{top_theme['name']}{top_theme['count']}只居前"
        if second_theme:
            theme_text += f"，{second_theme['name']}{second_theme['count']}只紧随"
        if third_theme:
            theme_text += f"，{third_theme['name']}{third_theme['count']}只跟随"
        summary.append(f"涨停分布上，{theme_text}，主线仍以题材轮动和局部扩散为主。")
    if tech_theme:
        summary.append(
            f"科技方向里，{tech_theme}{len(by_theme.get(tech_theme, []))}只涨停，{join_names(sorted(by_theme[tech_theme], key=lambda item: (item['consecutive'], item['amountRaw']), reverse=True), 4)}提供辨识度。"
        )
    summary.append(
        f"封板质量方面，2板及以上共有{multi_board_count}只，{reopen_count}只个股出现过开板，早盘09:35前完成首封的有{early_count}只，次日更要看前排承接而不是只看总数。"
    )
    return summary


def build_leaders(stocks, themes, by_theme):
    leaders = []
    used_themes = set()
    high_board = sorted([stock for stock in stocks if stock["consecutive"] >= 2], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
    if high_board:
        max_height = high_board[0]["consecutive"]
        leaders.append(
            {
                "type": "空间核心",
                "stocks": join_names(high_board, 3),
                "theme": high_board[0]["theme"],
                "logic": f"最高高度来到{board_text(max_height)}，{join_names(high_board, 3)}是短线情绪最直接的锚点。",
            }
        )
        used_themes.add(high_board[0]["theme"])

    if themes:
        top_name = themes[0]["name"]
        top_rows = sorted(by_theme[top_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        leaders.append(
            {
                "type": "主线热点",
                "stocks": join_names(top_rows, 4),
                "theme": top_name,
                "logic": f"{top_name}当天共有{len(top_rows)}只涨停，{join_names(top_rows, 4)}带动了最明显的板块扩散。",
            }
        )
        used_themes.add(top_name)

    tech_name = top_theme_name(by_theme, ["AI硬件/CPO/半导体", "AI应用/数据要素/服务", "化工材料/电子化学品"], exclude=used_themes)
    if tech_name:
        tech_rows = sorted(by_theme[tech_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        leaders.append(
            {
                "type": "科技活跃",
                "stocks": join_names(tech_rows, 4),
                "theme": tech_name,
                "logic": f"{tech_name}维持活跃，{join_names(tech_rows, 4)}提供了当天科技线的辨识度与弹性。",
            }
        )
        used_themes.add(tech_name)

    defend_name = top_theme_name(by_theme, ["资源品/煤炭/高股息", "电力能源/算力用电", "电力设备/新能源设备"], exclude=used_themes)
    if defend_name:
        defend_rows = sorted(by_theme[defend_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
        leaders.append(
            {
                "type": "防御承接",
                "stocks": join_names(defend_rows, 4),
                "theme": defend_name,
                "logic": f"{defend_name}有{len(defend_rows)}只涨停，{join_names(defend_rows, 4)}承担了弱指数环境下的资金承接。",
            }
        )
    elif len(themes) > 1:
        fallback_name = next((theme["name"] for theme in themes[1:] if theme["name"] not in used_themes), None)
        if fallback_name:
            fallback_rows = sorted(by_theme[fallback_name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)
            leaders.append(
                {
                    "type": "轮动补涨",
                    "stocks": join_names(fallback_rows, 4),
                    "theme": fallback_name,
                    "logic": f"{fallback_name}当天也有{len(fallback_rows)}只涨停，{join_names(fallback_rows, 4)}承担轮动扩散角色，持续性要看次日确认。",
                }
            )
    return leaders[:4]


def build_warnings(stocks, charts):
    warnings = []
    reopen_count = sum(1 for stock in stocks if stock["reopenCount"] > 0)
    first_board_count = sum(1 for stock in stocks if stock["consecutive"] == 1)
    total = len(stocks)

    if charts.get("shanghai") and charts.get("chinext") and charts.get("avg_price"):
        if all(charts[key].get("pct", 0) < 0 for key in ("shanghai", "chinext", "avg_price")):
            warnings.append("指数与平均股价同步走弱，若高标和主线前排不能继续承接，追高容易演变成隔日兑现。")
    if reopen_count >= max(10, total // 3):
        warnings.append(f"{reopen_count}只涨停股出现过开板，封板质量不算稳，明天更应重视回封强度和溢价反馈。")
    if first_board_count >= max(20, total // 2):
        warnings.append(f"首板占比达到{first_board_count}/{total}，说明扩散多于共振，接力最好围绕少数高辨识度核心。")
    if not warnings:
        warnings.append("连板与首板分布相对均衡，但次日仍要重点观察高标溢价和主线前排的承接质量。")
    return warnings[:3]


def clamp_score(value):
    return max(0, min(100, int(round(value))))


def serenity_grade(score):
    if score >= 78:
        return "A"
    if score >= 64:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def serenity_bottleneck_reason(stock, upstream_hits):
    category = stock.get("category") or ""
    theme = stock.get("theme") or ""
    if category in ("金属新材", "小金属", "冶钢原料"):
        return "上游材料/稀缺资源卡位，符合 Serenity 偏好的原料瓶颈映射；若具备稀缺产能、客户认证或定价权，才可进一步确认供应链垄断属性。"
    if category in ("电子化学", "半导体", "元件", "光学光电", "通信设备", "其他电子", "军工电子"):
        return "处在AI硬件、半导体或光通信上游环节，符合 Serenity 寻找“下游扩产必须支付的瓶颈层”的方法；重点核验是否有少数供应、认证壁垒或关键客户。"
    if category in ("专用设备", "自动化设", "通用设备", "电机Ⅱ", "轨交设备", "航空装备", "航天装备"):
        return "属于机器人/高端制造设备链，贴近 Serenity 的 physical AI 与自动化基础设施框架；A 评价来自上游设备卡位、主线强度和封板质量共振。"
    if category in ("电力", "电网设备", "其他电源", "光伏设备"):
        return "映射算力用电和电力基础设施瓶颈，符合 Serenity 把AI扩产传导到电力/电网约束的框架；需核验订单和产能约束。"
    if "AI" in theme or upstream_hits:
        return "具备AI/硬件/上游关键词，按 Serenity 框架可作为供应链瓶颈候选；是否达到垄断或少数供应仍需公告、客户和产能证据验证。"
    return "A 评价主要来自首板强度、主线排名和封板质量；供应链垄断属性暂未从现有数据确认，需要人工复核基本面。"


def build_serenity_a_reason(stock, upstream_hits, reasons):
    bottleneck = serenity_bottleneck_reason(stock, upstream_hits)
    evidence = "；".join(reasons[:3])
    if evidence:
        return f"{bottleneck} 盘面证据：{evidence}。"
    return bottleneck


def score_white_hair_candidate(stock, theme_rank):
    stock_text = "".join(
        str(stock.get(key) or "")
        for key in ("name", "code", "theme", "position", "category")
    )
    category_text = "".join(str(stock.get(key) or "") for key in ("name", "code", "category"))
    score = 40
    reasons = []
    risks = []

    demand_score = SERENITY_DEMAND_THEME_SCORE.get(stock["theme"], 0)
    if demand_score:
        score += demand_score
        reasons.append(f"{stock['theme']}贴近AI/机器人/电力/材料需求链")

    upstream_hits = [keyword for keyword in SERENITY_UPSTREAM_KEYWORDS if keyword in category_text]
    if upstream_hits:
        add_score = min(18, 6 * len(upstream_hits))
        score += add_score
        reasons.append(f"上游/瓶颈关键词：{'、'.join(upstream_hits[:3])}")

    rank = theme_rank.get(stock["theme"])
    if rank and rank <= 3:
        score += 8
        reasons.append(f"所属主线强度排名第{rank}")
    elif rank and rank <= 6:
        score += 4
        reasons.append(f"所属主线仍在涨停扩散区")

    first_time = stock.get("firstLimitTime") or ""
    if first_time and first_time <= "09:35:00":
        score += 6
        reasons.append("早盘完成封板，资金确认较快")
    elif first_time and first_time > "13:30:00":
        score -= 8
        risks.append("尾盘封板，次日承接验证要求更高")

    reopen_count = int(stock.get("reopenCount") or 0)
    if reopen_count == 0:
        score += 6
        reasons.append("封板未开，筹码稳定性较好")
    else:
        score -= min(14, reopen_count * 4)
        risks.append(f"封板后开板{reopen_count}次")

    amount_raw = float(stock.get("amountRaw") or 0)
    if amount_raw >= 1_000_000_000:
        score += 7
        reasons.append("成交额过10亿，具备容量票观察价值")
    elif amount_raw >= 500_000_000:
        score += 5
        reasons.append("成交额过5亿，流动性可观察")
    elif amount_raw >= 200_000_000:
        score += 3
        reasons.append("成交额过2亿，低位启动有基本流动性")
    else:
        score -= 4
        risks.append("成交额偏小，容量不足")

    turnover = float(stock.get("turnover") or 0)
    if 2 <= turnover <= 12:
        score += 4
        reasons.append("换手处于可承接区间")
    elif turnover > 18:
        score -= 6
        risks.append("换手偏高，分歧较重")

    if any(keyword in stock_text for keyword in SERENITY_WEAK_KEYWORDS) and not upstream_hits:
        score -= 10
        risks.append("偏传统轮动，缺少Serenity式供应链瓶颈特征")

    if stock["theme"] == "其他轮动" and not upstream_hits:
        score -= 8
        risks.append("题材归因不清，供应链映射不足")

    score = clamp_score(score)
    grade = serenity_grade(score)
    return {
        "code": stock["code"],
        "name": stock["name"],
        "theme": stock["theme"],
        "category": stock["category"],
        "score": score,
        "grade": grade,
        "firstLimitTime": stock.get("firstLimitTime") or "",
        "amount": stock.get("amount") or "",
        "amountRaw": amount_raw,
        "turnover": stock.get("turnover"),
        "reopenCount": reopen_count,
        "serenityReason": "；".join(reasons[:4]) or "首板样本，但供应链优势仍需人工复核",
        "serenityAReason": build_serenity_a_reason(stock, upstream_hits, reasons),
        "risk": "；".join(risks[:3]) or "暂无明显结构性扣分，仍需补充基本面和公告核验",
    }


def build_white_hair_picks(stocks, themes):
    theme_rank = {theme["name"]: index + 1 for index, theme in enumerate(themes)}
    first_boards = [stock for stock in stocks if int(stock.get("consecutive") or 0) == 1]
    scored = [score_white_hair_candidate(stock, theme_rank) for stock in first_boards]
    picks = [item for item in scored if item["grade"] == "A"]
    picks.sort(key=lambda item: (-item["score"], item["firstLimitTime"], -item["amountRaw"]))
    return {
        "title": "白毛严选",
        "source": "仅从当天首板中筛选；按 Serenity 方法论的供应链瓶颈、上游稀缺、AI/机器人/电力/材料需求、主线强度、封板质量和风险扣分生成 A 评价。",
        "methodology": [
            "优先：AI硬件/CPO/半导体、电子化学品、机器人/高端制造、电力/算力用电、上游材料。",
            "加分：上游瓶颈关键词、强主线排名靠前、早盘封板、未开板、成交额与换手可承接。",
            "扣分：题材归因不清、尾盘封板、多次开板、成交额过小、纯传统轮动且缺少供应链映射。",
        ],
        "totalFirstBoard": len(first_boards),
        "aCount": len(picks),
        "items": picks,
    }


def build_market_news(target_date):
    rows = CURATED_MARKET_NEWS_BY_DATE.get(target_date, [])
    if rows:
        return rows
    return [
        {
            "category": "提示",
            "heat": "待补充",
            "title": f"{target_date} 真实新闻尚未维护",
            "impact": "该板块只展示已核验新闻事件，不再用盘面主线归纳冒充新闻。",
            "whyHot": "请补充英伟达、苹果、AI、芯片、机器人、产业政策等真实事件后重新生成日报。",
            "relatedThemes": [],
            "watch": "维护 CURATED_MARKET_NEWS_BY_DATE 后重新运行 update_daily_report.py。",
            "source": "本地新闻清单",
            "url": "",
        }
    ]


def update_charts(target_date, date_compact):
    charts = json.loads(CHARTS.read_text(encoding="utf-8"))
    for series in charts["series"]:
        if series.get("source") == "sina" and series.get("symbol"):
            points = fetch_sina_kline(series["symbol"], limit=190)
        elif series["id"] == "avg_price":
            points = list(series.get("points", [])) + [fetch_eastmoney_quote_point(CHART_SECIDS[series["id"]], target_date)]
        else:
            points = fetch_stable_eastmoney_kline(series["id"], CHART_SECIDS[series["id"]], date_compact, limit=190)
        latest = next((point for point in reversed(points) if point["date"] == target_date), None)
        if not latest:
            raise RuntimeError(f"{series['id']} missing {target_date}")
        cached_latest = next((point for point in reversed(series.get("points", [])) if point.get("date") == target_date), None)
        if cached_latest and abs(float(latest.get("pct") or 0)) > 15 and abs(float(cached_latest.get("pct") or 0)) <= 15:
            latest = cached_latest
            series["cachedReason"] = "行情接口返回异常涨跌幅，保留本地已核验缓存点"
        else:
            series.pop("cachedReason", None)
        merged = {point["date"]: point for point in series.get("points", [])}
        merged[target_date] = latest
        series["points"] = [merged[key] for key in sorted(merged)]
        first = series["points"][0]
        series["latestDate"] = latest["date"]
        series["latestClose"] = latest["close"]
        series["latestPct"] = latest["pct"]
        series["latestChange"] = latest["change"]
        series["latestTime"] = now_text()
        series["rangePct"] = round((latest["close"] / first["close"] - 1) * 100, 2) if first["close"] else 0
    charts["updatedAt"] = now_text()
    CHARTS.write_text(json.dumps(charts, ensure_ascii=False, indent=2), encoding="utf-8")
    return charts


def update_report(target_date, charts_data=None):
    date_compact = target_date.replace("-", "")
    rows, meta = fetch_zt_pool(date_compact)
    if str(meta.get("qdate")) != date_compact:
        raise RuntimeError(f"zt pool qdate mismatch: {meta}")
    stocks = [stock_obj(row) for row in rows]
    by_theme = defaultdict(list)
    for stock in stocks:
        by_theme[stock["theme"]].append(stock)
    theme_names = sorted(by_theme, key=lambda name: (len(by_theme[name]), max(item["consecutive"] for item in by_theme[name])), reverse=True)
    themes = []
    for name in theme_names:
        leaders = sorted(by_theme[name], key=lambda item: (item["consecutive"], item["amountRaw"]), reverse=True)[:6]
        themes.append({"name": name, "count": len(by_theme[name]), "catalyst": reason_for(name), "leaders": [item["name"] for item in leaders]})
    charts = chart_snapshot(charts_data or json.loads(CHARTS.read_text(encoding="utf-8")), target_date)
    ladder = []
    for height in sorted({stock["consecutive"] for stock in stocks}, reverse=True):
        same_height = sorted([stock for stock in stocks if stock["consecutive"] == height], key=lambda item: item["firstLimitTime"])
        top = same_height[:12]
        main_theme = Counter(item["theme"] for item in same_height).most_common(1)[0][0]
        ladder.append(
            {
                "height": "首板" if height == 1 else f"{height}连板",
                "stocks": "、".join(item["name"] for item in top) + ("等" if len(same_height) > 12 else ""),
                "theme": main_theme,
                "note": f"共{len(same_height)}只；代表个股：" + "、".join(f"{item['name']}({item['firstLimitTime']})" for item in top[:5]) + "。",
            }
        )
    report = {
        "date": target_date,
        "session": "收盘复盘",
        "title": "A股涨停复盘报告",
        "market": {
            "limitUpCount": int(meta.get("tc") or len(rows)),
            "dataSource": f"东方财富涨停池 getTopicZTPool(date={date_compact}) 返回 qdate={meta.get('qdate')}、tc={meta.get('tc')}；指数和板块K线来自东方财富日K接口；市场与科技新闻雷达结合公开财经/科技报道归档。",
            "sampleScope": f"收盘口径纳入东方财富专题涨停池 qdate={date_compact} 且收盘仍封涨停的A股样本，共{len(rows)}只；不纳入盘中炸板未封回或旧日期数据。",
        },
        "summary": build_summary(target_date, date_compact, meta, stocks, themes, by_theme, charts),
        "themes": themes,
        "ladder": ladder,
        "leaders": build_leaders(stocks, themes, by_theme),
        "stats": [{"category": item["name"], "count": item["count"]} for item in themes],
        "stocks": stocks,
        "whiteHairPicks": build_white_hair_picks(stocks, themes),
        "newHighScope": "收盘报告已生成，创新高模块待 scripts/update_screeners.py 补算。",
        "newHighStocks": [],
        "maConvergenceScope": "收盘报告已生成，均线粘合模块待 scripts/update_screeners.py 补算。",
        "maConvergenceStocks": [],
        "warnings": build_warnings(stocks, charts),
        "pdf": None,
        "marketNews": build_market_news(target_date),
    }
    data = json.loads(REPORTS.read_text(encoding="utf-8"))
    data["reports"] = [item for item in data.get("reports", []) if item.get("date") != target_date]
    data["reports"].insert(0, report)
    data["updatedAt"] = now_text()
    REPORTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Update daily A-share report and market charts")
    parser.add_argument("--date", required=True, help="Trading date, for example 2026-06-04")
    args = parser.parse_args()
    date_compact = args.date.replace("-", "")
    charts = update_charts(args.date, date_compact)
    update_report(args.date, charts)
    print(f"Updated report and charts for {args.date}")
    print([(series["id"], series["latestDate"], series["latestPct"]) for series in charts["series"]])


if __name__ == "__main__":
    main()
