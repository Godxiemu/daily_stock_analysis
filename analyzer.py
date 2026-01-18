# -*- coding: utf-8 -*-
"""
===================================
天阶·天地融合分析系统 - AI 大脑层 (Ultimate Ver.)
===================================

核心职责：
1. 承载《天阶功法》全套心法 (MOV协议/五步精算法/A-B-C定锚/渣男博弈)
2. 调度 Gemini/OpenAI 模型进行深度逻辑推演
3. 输出符合天阶体系的深度研报 (JSON)
"""

import json
import logging
import time
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# 引入重试机制，防止网络波动
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# 尝试导入配置，如果没有则使用默认Mock防止报错
try:
    from config import get_config
except ImportError:
    class MockConfig:
        gemini_api_key = None
        gemini_model = "gemini-2.0-flash"
        openai_api_key = None
        openai_base_url = None
        openai_model = "gpt-4o"
    def get_config(): return MockConfig()

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# 天阶功法核心系统提示词 (The Bible - 完整落地版)
# 包含：宏观加减法、A/B/C类资产定锚、真假财报识别、渣男交易策略
# -------------------------------------------------------------------------

TIANJIE_SYSTEM_PROMPT = """## Role & Identity
你是**“天地融合·天阶投资大师”**（Mr. Dang 风格）。
你不是一个只会报数据的机器人，你是一位深谙中国资本市场人性与国运的资深操盘手。
你兼具天阶的**宏观精算眼光**（国家焦虑、A/B/C分类定锚）与地阶的**冷酷博弈心法**（斩三尸、渣男心法）。

**核心任务**：
在噪音中寻找符合“国家焦虑”的资产，用“五步精算法”锁定击球区，并用“盲盒可视化”拆解财务谎言。

---

## Part 1: Core Philosophy (核心心法)

### 1. 天道 (The Macro - 只有顺势才能生存)
* **国家焦虑论**：投资的本质是捕捉国家因不安全感产生的资源调配红利。
    * *案例*：能源安全 -> 煤炭/石油/光伏； 科技封锁 -> 半导体/国产软件； 粮食安全 -> 种业/化肥。
* **加减法则**：
    * **加法行业**：国家急需突破的瓶颈（高端制造、卡脖子技术）。特点：政策扶持，容忍泡沫。
    * **减法行业**：国家想要淘汰的过剩产能（高能耗、低技术、污染）。特点：供给侧改革，存量博弈，巨头通吃（剩者为王）。
    * **熔断行业**：教培、高利贷、无技术高能耗。**直接判死刑。**

### 2. 地道 (The Micro - 财报是皮，物理是骨)
* **皮骨论**：财报数字可以造假，但物理常识不会。
    * *验证*：用“耗电量”、“运价”、“排他性牌照”、“矿石品位”去验证利润的真实性。
* **A/B/C 资产分类定锚（至关重要）**：
    * **A类 (收息/公用/防守)**：水电、高速、银行、运营商。
        * *锚点*：**股息率** (底线4%，理想6%+) + **现金流覆盖率**。
        * *逻辑*：只买跌下来的高股息，不买涨上去的市梦率。
    * **B类 (周期/资源/博弈)**：煤炭、有色、化工、海运、养殖。
        * *锚点*：**PB (重置成本)** + **PE (周期位置)** + **商品价格趋势**。
        * *逻辑*：在高PE（业绩差）时买入，在低PE（业绩好）时卖出。关注“供给侧逻辑”（有没有新矿投产？）。
    * **C类 (真成长/进攻)**：具备“2求”属性的品牌、制造、科技。
        * *锚点*：**PEG** (成长性性价比) + **渗透率** (0-20%最佳)。
        * *逻辑*：必须有“物理壁垒”（技术独占、品牌垄断）。警惕“伪成长”（靠烧钱买营收）。
    * **垃圾类**：0求（求爷爷告奶奶）、两头受气、现金流为负、依靠政府补贴存活。-> **建议直接做空或熔断。**

### 3. 人道 (The Execution - 渣男心法)
* **斩三尸**：
    * *破锚定*：不要在乎持仓成本，只看未来。
    * *破贪婪*：乖离率（Bias）过大（>5%）时，那是给别人的利润，严禁追高。
    * *破恐惧*：缩量回踩支撑位（MA5/MA10/MA20）是天赐良机。
* **损不足而奉有余**：
    * **多头排列（MA5>MA10>MA20）**：这是“余”，必须持有或加仓。
    * **空头排列（MA5<MA10<MA20）**：这是“不足”，必须断舍离，不要补仓！不要补仓！
* **渣男交易**：逻辑在（趋势好、基本面硬）时深情梭哈，逻辑破（趋势坏、逻辑证伪）时立即分手，绝不纠缠。

---

## Part 2: 🎯 Mandatory Online Verification (MOV 协议)

**在分析任何股票时，必须严格按顺序执行以下步骤：**

### Step 1: 生存权审查 (The Gatekeeper)
1.  **"求"字定级**：
    * **3求 (帝王)**：上游求合作，下游求发货，政府求驻留。（极稀缺）
    * **2求 (诸侯)**：拥有不可再生资源或行政壁垒（上帝模式）。（核心资产）
    * **1求 (平民)**：平等博弈，随行就市。（大部分制造业）
    * **0求 (奴隶)**：上游涨价无法传导，下游压款无法拒绝。**-> 拒绝评级，直接淘汰。**
2.  **加减法判定**：顺应国运（加法）还是逆势而为？

### Step 3: 估值精算 & 验真 (The Math)
1.  **真实EPS修正**：
    * `真实EPS ≈ (归母净利 - 永续债利息) ÷ (最新总股本 - 库存股)`
    * *注意*：如果公司有大量永续债，必须扣除利息，否则PE是假的。
2.  **谎言粉碎机 (Truth Check)**：
    * **真钱含量** = `(经营性现金流净额 / 归母净利润)`。
    * *红线*：如果长期 < 80%，且不是处于高速扩张期的C类公司，标记为**“纸面富贵”**（甚至造假）。
    * *分红验证*：只有真金白银分到股民手里的钱，才是真的。长期不分红的都是耍流氓。

---

## Part 3: Output Format (输出报告 - JSON Only)

必须严格按照以下 JSON 格式输出，不要输出多余的 Markdown 标记或寒暄。
语言风格要求：**辛辣、直接、一针见血**（Mr. Dang 风格）。不要说模棱两可的废话。

```json
{
    "core_conclusion": {
        "verdict": "战略买入 / 观察 / 垃圾(熔断) / 建议做空 / 获利了结",
        "signal_color": "RED(卖出)/GREEN(买入)/YELLOW(观望)",
        "one_sentence_reason": "一句话辛辣概括：顺应了什么国运？是渣女还是良配？（例如：'这只是个给银行打工的0求奴隶，趁早割肉' 或 '国家急需的硬科技，缩量回踩就是送钱'）"
    },
    "business_audit": {
        "asset_class": "A类(收息)/B类(周期)/C类(成长)/垃圾类",
        "qiu_level": "3求/2求/1求/0求",
        "macro_direction": "国家加法/国家减法/中性/逆势",
        "physical_moat": "列出搜到的硬数据（如：矿石品位、单耗、排他性牌照、门店数量）",
        "virtual_factory": "虚拟工厂简评 (成本优势/上下游议价权)"
    },
    "value_calculation": {
        "valuation_anchor": "使用的锚点 (如 PB/PE/股息率/PEG)",
        "current_val": "当前数值 (如 1.2倍PB)",
        "target_val": "合理估值/目标价位",
        "truth_check": "真金白银 / 纸面富贵 / 数据存疑 (基于现金流与净利比)",
        "dividend_analysis": "分红意愿及能力评价 (铁公鸡 vs 现金奶牛)"
    },
    "scumbag_execution": {
        "trend_status": "天阶强势 / 多头排列 / 震荡 / 空头排列",
        "technical_signal": "输入的技术信号 (如: 缩量回踩 MA5)",
        "bias_check": "乖离率状态 (安全/适中/贪婪-禁止追高)",
        "action_guide": "基于渣男心法的具体操作建议 (例如：'均线发散，拿住别动' 或 '跌破MA20，立即分手')"
    },
    "spicy_comment": "模仿Mr. Dang的口吻，不少于100字的深度犀利点评。结合宏观、行业地位和博弈心理。要骂醒韭菜，也要指明方向。"
}
"""

@dataclass
class TianjieAnalysisResult:
    """天阶分析结果封装"""
    code: str
    name: str
    # 核心结论
    verdict: str = "观察"
    signal_color: str = "YELLOW"
    reason: str = ""

    # 商业模式审计
    asset_class: str = "未知"    # A/B/C
    qiu_level: str = "未知"      # 0-3求
    macro_direction: str = ""    # 加法/减法
    physical_moat: str = ""      # 物理壁垒
    virtual_factory: str = ""

    # 价值精算
    valuation_anchor: str = ""
    current_val: str = ""
    target_val: str = ""
    truth_check: str = ""        # 真假财报
    dividend_analysis: str = ""

    # 渣男执行
    action_guide: str = "观望"
    trend_status: str = ""
    technical_signal: str = ""
    bias_check: str = ""

    # 辛辣点评
    spicy_comment: str = ""

    # 系统元数据
    success: bool = False
    error_message: Optional[str] = None
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，方便前端展示"""
        return {
            "code": self.code,
            "name": self.name,
            "verdict": self.verdict,
            "signal_color": self.signal_color,
            "reason": self.reason,
            "business_audit": {
                "asset_class": self.asset_class,
                "qiu_level": self.qiu_level,
                "macro_direction": self.macro_direction,
                "physical_moat": self.physical_moat,
                "virtual_factory": self.virtual_factory
            },
            "valuation": {
                "anchor": self.valuation_anchor,
                "value": self.current_val,
                "target": self.target_val,
                "truth": self.truth_check,
                "dividend": self.dividend_analysis
            },
            "execution": {
                "status": self.trend_status,
                "signal": self.technical_signal,
                "bias": self.bias_check,
                "guide": self.action_guide
            },
            "spicy_comment": self.spicy_comment
        }

class GeminiAnalyzer:
    """
    天阶分析器 - 全能版 (Gemini / OpenAI 兼容)
    """
    def __init__(self, api_key: Optional[str] = None):
        self.config = get_config()
        self._api_key = api_key or self.config.gemini_api_key
        self._model = None
        self._openai_client = None
        self._use_openai = False
        
        self._init_models()
        
    def _init_models(self):
        """初始化 AI 模型 (优先 Gemini，失败则尝试 OpenAI)"""
        # 1. 尝试初始化 Gemini
        if self._api_key and not str(self._api_key).startswith("your"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._model = genai.GenerativeModel(
                    model_name=self.config.gemini_model,
                    system_instruction=TIANJIE_SYSTEM_PROMPT
                )
                logger.info("✅ Gemini 模型初始化成功")
                return
            except Exception as e:
                logger.warning(f"⚠️ Gemini 初始化失败: {e}")

        # 2. 尝试初始化 OpenAI (DeepSeek/GPT/Kimi)
        if self.config.openai_api_key and not str(self.config.openai_api_key).startswith("your"):
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(
                    api_key=self.config.openai_api_key,
                    base_url=self.config.openai_base_url
                )
                self._use_openai = True
                logger.info(f"✅ OpenAI 兼容模型初始化成功 (Model: {self.config.openai_model})")
                return
            except Exception as e:
                logger.error(f"❌ OpenAI 初始化失败: {e}")
        
        logger.error("❌ 未找到可用的 AI 模型配置。请检查 config.py")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
    def analyze(self, context: Dict[str, Any], news_context: Optional[str] = None) -> TianjieAnalysisResult:
        """
        执行天阶分析
        Args:
            context: 包含代码、名称、价格、技术指标(StockTrendAnalyzer输出)、财务数据的字典
            news_context: 搜索到的新闻文本
        """
        code = context.get('code', 'Unknown')
        name = context.get('stock_name', 'Unknown')
        
        if not self._model and not self._openai_client:
            return TianjieAnalysisResult(code=code, name=name, error_message="AI 模型未初始化")

        try:
            # 1. 构造深度 Prompt
            prompt = self._format_tianjie_prompt(context, name, news_context)
            
            # 2. 调用 AI
            response_text = ""
            logger.info(f"⚡ 天阶大师正在审视 {name}({code})...")
            
            if self._use_openai and self._openai_client:
                # OpenAI 调用方式
                response = self._openai_client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[
                        {"role": "system", "content": TIANJIE_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content
            elif self._model:
                # Gemini 调用方式
                response = self._model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.4, "response_mime_type": "application/json"}
                )
                response_text = response.text
            
            # 3. 解析结果
            return self._parse_tianjie_response(response_text, code, name)
            
        except Exception as e:
            logger.error(f"分析失败 [{code}]: {e}")
            return TianjieAnalysisResult(code=code, name=name, success=False, error_message=str(e))

    def _format_tianjie_prompt(self, context: Dict[str, Any], name: str, news_context: Optional[str]) -> str:
        """
        将技术面、财务面、消息面整合成“大师”需要的输入
        """
        code = context.get('code')
        today = context.get('today', {})
        rt = context.get('realtime', {}) # 实时财务数据
        
        # --- 提取技术面数据 (由 stock_analyzer.py 提供) ---
        trend_info = context.get('trend_analysis', {})
        # 如果 trend_info 为空，给予默认值
        tech_signal = trend_info.get('signal_desc', '数据不足')
        bias_ma5 = trend_info.get('bias_ma5', 0.0)
        trend_status = trend_info.get('trend_status', '未知')
        trend_strength = trend_info.get('trend_strength', 0)
        volume_status = trend_info.get('volume_status', '未知')
        risk_factors = trend_info.get('risk_factors', [])
        
        # --- 提取财务数据 (优先使用 realtime 中的数据) ---
        pe_ttm = rt.get('pe_ttm') or rt.get('pe_ratio', '未知')
        pb_mrq = rt.get('pb_mrq') or rt.get('pb_ratio', '未知')
        div_yield = rt.get('dividend_yield_ttm') or rt.get('dividend_yield', '未知')
        total_mv = rt.get('total_mv', '未知')
        
        # 构造 prompt
        prompt = f"""
请对 {name} ({code}) 进行《天阶功法》深度审计。
1. 基础数据 (The Facts)
当前价格：{today.get('close', '未知')}
估值指标：PE(TTM)={pe_ttm} | PB(MRQ)={pb_mrq} | 股息率={div_yield}%
总市值：{total_mv}
2. 技术面透视 (The Execution - 渣男指标)
趋势状态：{trend_status} (强度: {trend_strength}/100)
均线信号：{tech_signal}
贪婪指数 (乖离率 MA5)：{bias_ma5:.2f}%  (注意：>5%为贪婪/追高风险)
量能博弈：{volume_status}
潜在风险：{', '.join(risk_factors) if risk_factors else '无明显技术风险'}
3. 舆情与基本面线索 (The Context)
{news_context if news_context else "无外部搜索数据，请基于你对该公司的固有知识储备（行业地位、主营业务）进行分析。"}
4. 执行指令 (Analysis Request)
请执行 MOV (Mandatory Online Verification) 协议，步骤如下：
Gatekeeper (定性)：
判断该行业是国家做“加法”（如半导体/新能源）还是“减法”（如地产/高能耗）？
判定“求”字等级 (0-3求)。如果是0求（奴隶），直接判死刑。
Anchor (定锚)：
确定资产类别 (A类/B类/C类)，并选择唯一的估值尺子。
A类看股息+现金流；B类看PB+商品周期；C类看PEG+渗透率。不要乱用指标！
Math (验真)：
基于 PE/PB/股息率，判断当前价格是“黄金坑”还是“杀猪盘”？
推演其现金流是否健康（是否存在“纸面富贵”风险）。
Execution (博弈)：
结合技术面（乖离率、趋势状态），给出最终的“渣男”操作建议（梭哈、观望、分手）。
请输出完整的 JSON 报告。
"""
        return prompt

    def _parse_tianjie_response(self, text: str, code: str, name: str) -> TianjieAnalysisResult:
        try:
            # 清理 Markdown 标记，防止模型输出 ```json ... ```
            clean_text = re.sub(r'^```json\s*', '', text)
            clean_text = re.sub(r'^```\s*', '', clean_text)
            clean_text = re.sub(r'\s*```$', '', clean_text)
            clean_text = clean_text.strip()
            
            data = json.loads(clean_text)
            
            core = data.get('core_conclusion', {})
            audit = data.get('business_audit', {})
            val = data.get('value_calculation', {})
            exc = data.get('scumbag_execution', {})
            
            return TianjieAnalysisResult(
                code=code,
                name=name,
                success=True,
                
                # 核心结论
                verdict=core.get('verdict', '观察'),
                signal_color=core.get('signal_color', 'YELLOW'),
                reason=core.get('one_sentence_reason', ''),
                
                # 商业模式
                asset_class=audit.get('asset_class', '未知'),
                qiu_level=audit.get('qiu_level', '未知'),
                macro_direction=audit.get('macro_direction', ''),
                physical_moat=audit.get('physical_moat', ''),
                virtual_factory=audit.get('virtual_factory', ''),
                
                # 价值精算
                valuation_anchor=val.get('valuation_anchor', ''),
                current_val=str(val.get('current_val', '')),
                target_val=str(val.get('target_val', '')),
                truth_check=val.get('truth_check', ''),
                dividend_analysis=val.get('dividend_analysis', ''),
                
                # 渣男执行
                trend_status=exc.get('trend_status', ''),
                action_guide=exc.get('action_guide', '观望'),
                technical_signal=exc.get('technical_signal', ''),
                bias_check=exc.get('bias_check', ''),
                
                # 辛辣点评
                spicy_comment=data.get('spicy_comment', ''),
                
                raw_response=text
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e} | Raw Response: {text[:200]}...")
            return TianjieAnalysisResult(
                code=code, 
                name=name, 
                success=False, 
                error_message=f"AI 返回格式错误: {text[:100]}", 
                raw_response=text
            )
        except Exception as e:
            logger.error(f"分析结果处理异常: {e}")
            return TianjieAnalysisResult(code=code, name=name, success=False, error_message=str(e), raw_response=text)

def get_analyzer():
    return GeminiAnalyzer()
