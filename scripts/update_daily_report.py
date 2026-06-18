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
        "items": picks[:12],
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
