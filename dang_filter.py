# -*- coding: utf-8 -*-
"""
===================================
Dang氏投资筛选器 - 价值投资核心配置
===================================

基于 Mr. Dang 的投资心法，实现行业筛选、估值判断、股息率分析等功能。

核心理念：
1. 商业模式"求"字诀 - 只投"2求"以上企业
2. 生产资料至上 - 银行、有色、矿产优先
3. PE估值铁律 - 周期股30PE跑路，科技股300PE不碰
4. 止盈30% - 短期涨幅超30%坚决止盈
5. 补仓逻辑 - 跌10%以上才考虑补仓
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class IndustryTier(Enum):
    """行业等级"""
    PREFERRED = "优选行业"      # 生产资料类，高股息
    NORMAL = "普通行业"         # 一般行业
    CAUTION = "谨慎行业"        # 需要额外关注
    BLACKLIST = "黑名单行业"    # Dang氏明确不碰


class StockType(Enum):
    """股票类型（用于PE估值判断）"""
    CYCLICAL = "周期股"         # 有色、钢铁、煤炭等
    BANKING = "银行股"          # 银行
    TECH = "科技股"             # 科技成长
    CONSUMER = "消费股"         # 消费类
    DEFAULT = "其他"


# ========================================
# Dang氏行业分类配置
# ========================================

# 优选行业（生产资料类）- Dang氏最爱
PREFERRED_INDUSTRIES = [
    "银行", "国有大型银行", "股份制银行", "城商行", "农商行",
    "有色金属", "铜", "铝", "锌", "锡", "黄金", "稀土",
    "煤炭", "煤炭开采",
    "石油", "石油开采",
    "矿产", "铁矿", "锂矿",
    "电力", "水电", "火电", "核电",
    "高速公路", "港口", "机场",
]

# 黑名单行业 - Dang氏明确不碰
BLACKLIST_INDUSTRIES = [
    # 内卷严重
    "光伏", "光伏设备", "光伏电池", "组件",
    "电池", "锂电池", "动力电池", "储能电池",
    "电动车", "新能源车", "新能源汽车", "整车",
    # 不可预测
    "影视", "电影", "传媒", "游戏", "手游",
    # 商业模式差
    "房地产", "地产", "房地产开发", "物业",
    # 中游绞肉机（除非成本最低）
    "光伏组件", "电池组件",
]

# 谨慎行业 - 需要额外关注
CAUTION_INDUSTRIES = [
    "证券", "保险",  # 不透明金融
    "医药", "生物医药",  # 政策风险
    "白酒",  # 估值常年偏高
    "半导体", "芯片",  # 波动大
]


# ========================================
# Dang氏PE估值阈值配置
# ========================================

PE_THRESHOLDS: Dict[StockType, Dict[str, float]] = {
    StockType.CYCLICAL: {
        "ideal": 10,      # 理想买入PE
        "acceptable": 15, # 可接受PE
        "warning": 20,    # 警告PE（挂旗杆风险）
        "danger": 30,     # 危险PE（坚决跑路）
    },
    StockType.BANKING: {
        "ideal": 4,
        "acceptable": 6,
        "warning": 8,
        "danger": 12,
    },
    StockType.TECH: {
        "ideal": 20,
        "acceptable": 40,
        "warning": 100,
        "danger": 300,    # Dang氏铁律：300PE不碰
    },
    StockType.CONSUMER: {
        "ideal": 15,
        "acceptable": 25,
        "warning": 35,
        "danger": 50,
    },
    StockType.DEFAULT: {
        "ideal": 12,
        "acceptable": 20,
        "warning": 30,
        "danger": 50,
    },
}


# ========================================
# Dang氏股息率配置
# ========================================

DIVIDEND_CONFIG = {
    "excellent": 5.0,    # 5%+，优秀，Dang氏最爱
    "good": 3.0,         # 3-5%，良好
    "acceptable": 1.0,   # 1-3%，可接受
    "poor": 0.0,         # 不分红，"耍流氓"
}


# ========================================
# Dang氏交易配置
# ========================================

# 止盈配置
PROFIT_TAKE_THRESHOLD = 30.0    # 涨幅30%止盈
PROFIT_TAKE_EXTREME = 50.0      # 涨幅50%强烈止盈

# 补仓配置
REBUY_DROP_THRESHOLD = 10.0     # 跌10%才考虑补仓
REBUY_DROP_IDEAL = 15.0         # 跌15%是理想补仓点

# 乖离率配置（Dang氏相对宽容）
BIAS_WARNING = 8.0              # 乖离率警告阈值（原5%）
BIAS_DANGER = 12.0              # 乖离率危险阈值


# ========================================
# 评分权重配置
# ========================================

SCORE_WEIGHTS = {
    # 基本面（60分）
    "valuation": 25,        # 估值合理性
    "dividend": 20,         # 股息率
    "business_model": 15,   # 商业模式/行业
    
    # 技术面（40分）
    "trend": 15,            # 趋势状态
    "bias": 10,             # 乖离率
    "volume": 10,           # 量能配合
    "support": 5,           # 支撑有效
}

# 风险扣分项
RISK_PENALTIES = {
    "profit_take_warning": -10,   # 涨幅超30%
    "shareholder_selling": -5,    # 大股东减持
    "blacklist_industry": -5,     # 黑名单行业
    "pe_too_high": -5,            # PE过高
    "no_dividend": -3,            # 不分红
}


# ========================================
# Dang氏筛选器类
# ========================================

@dataclass
class DangAnalysisResult:
    """Dang氏分析结果"""
    # 行业分析
    industry_tier: IndustryTier = IndustryTier.NORMAL
    industry_comment: str = ""
    
    # 估值分析
    stock_type: StockType = StockType.DEFAULT
    pe_status: str = "未知"      # 理想/可接受/警告/危险
    pe_score: int = 0            # 估值得分 (0-25)
    pe_comment: str = ""
    
    # 股息分析
    dividend_status: str = "未知"  # 优秀/良好/可接受/差
    dividend_score: int = 0       # 股息得分 (0-20)
    dividend_comment: str = ""
    
    # 交易信号
    profit_take_alert: bool = False   # 止盈警告
    rebuy_opportunity: bool = False   # 补仓机会
    
    # 风险项
    risk_items: list = None
    risk_penalty: int = 0
    
    # 总评
    fundamental_score: int = 0    # 基本面总分 (0-60)
    dang_comment: str = ""        # Dang氏风格点评
    
    def __post_init__(self):
        if self.risk_items is None:
            self.risk_items = []


class DangFilter:
    """
    Dang氏投资筛选器
    
    用于对股票进行价值投资维度的分析和评分
    """
    
    def __init__(self):
        pass
    
    def classify_industry(self, industry: str) -> Tuple[IndustryTier, str]:
        """
        对行业进行分类
        
        Args:
            industry: 行业名称
            
        Returns:
            (行业等级, 点评)
        """
        if not industry:
            return IndustryTier.NORMAL, "行业信息缺失"
        
        # 检查黑名单
        for blacklist in BLACKLIST_INDUSTRIES:
            if blacklist in industry:
                return IndustryTier.BLACKLIST, f"⚠️ {industry}属于Dang氏黑名单行业，内卷严重或商业模式差"
        
        # 检查优选行业
        for preferred in PREFERRED_INDUSTRIES:
            if preferred in industry:
                return IndustryTier.PREFERRED, f"✅ {industry}是Dang氏优选的生产资料类行业"
        
        # 检查谨慎行业
        for caution in CAUTION_INDUSTRIES:
            if caution in industry:
                return IndustryTier.CAUTION, f"⚡ {industry}需要额外关注政策和估值风险"
        
        return IndustryTier.NORMAL, f"{industry}属于普通行业"
    
    def classify_stock_type(self, industry: str) -> StockType:
        """
        判断股票类型（用于PE估值判断）
        
        Args:
            industry: 行业名称
            
        Returns:
            股票类型
        """
        if not industry:
            return StockType.DEFAULT
        
        # 银行
        if "银行" in industry:
            return StockType.BANKING
        
        # 周期股
        cyclical_keywords = ["有色", "煤炭", "钢铁", "石油", "化工", "矿", "水泥", "航运"]
        for kw in cyclical_keywords:
            if kw in industry:
                return StockType.CYCLICAL
        
        # 科技股
        tech_keywords = ["科技", "软件", "互联网", "半导体", "芯片", "AI", "人工智能", "云计算"]
        for kw in tech_keywords:
            if kw in industry:
                return StockType.TECH
        
        # 消费股
        consumer_keywords = ["白酒", "食品", "饮料", "家电", "服装", "零售", "消费"]
        for kw in consumer_keywords:
            if kw in industry:
                return StockType.CONSUMER
        
        return StockType.DEFAULT
    
    def evaluate_pe(self, pe: Optional[float], stock_type: StockType) -> Tuple[str, int, str]:
        """
        评估PE估值
        
        Args:
            pe: 市盈率
            stock_type: 股票类型
            
        Returns:
            (状态, 得分, 点评)
        """
        if pe is None or pe <= 0:
            return "未知", 10, "PE数据缺失或为负，无法判断"
        
        thresholds = PE_THRESHOLDS.get(stock_type, PE_THRESHOLDS[StockType.DEFAULT])
        
        if pe <= thresholds["ideal"]:
            return "理想", 25, f"✅ PE={pe:.1f}，估值极具吸引力，Dang氏认可的好价格"
        elif pe <= thresholds["acceptable"]:
            return "可接受", 20, f"✅ PE={pe:.1f}，估值合理，可以考虑建仓"
        elif pe <= thresholds["warning"]:
            return "警告", 10, f"⚠️ PE={pe:.1f}，估值偏高，容易'挂旗杆'"
        else:
            return "危险", 0, f"❌ PE={pe:.1f}，估值过高，Dang氏铁律：坚决不碰！"
    
    def evaluate_dividend(self, dividend_yield: Optional[float]) -> Tuple[str, int, str]:
        """
        评估股息率
        
        Args:
            dividend_yield: 股息率（%）
            
        Returns:
            (状态, 得分, 点评)
        """
        if dividend_yield is None:
            return "未知", 5, "股息数据缺失"
        
        if dividend_yield >= DIVIDEND_CONFIG["excellent"]:
            return "优秀", 20, f"✅ 股息率{dividend_yield:.2f}%，这才是Dang氏最爱的生产资料！"
        elif dividend_yield >= DIVIDEND_CONFIG["good"]:
            return "良好", 15, f"✅ 股息率{dividend_yield:.2f}%，分红稳定，值得关注"
        elif dividend_yield >= DIVIDEND_CONFIG["acceptable"]:
            return "可接受", 8, f"⚡ 股息率{dividend_yield:.2f}%，分红一般，看其他因素"
        else:
            return "差", 0, f"⚠️ 股息率{dividend_yield:.2f}%或不分红，Dang氏说这是'耍流氓'"
    
    def check_profit_take(self, price_change_pct: Optional[float]) -> Tuple[bool, str]:
        """
        检查是否触发止盈
        
        Args:
            price_change_pct: 涨幅百分比（相对买入价或近期低点）
            
        Returns:
            (是否止盈, 点评)
        """
        if price_change_pct is None:
            return False, ""
        
        if price_change_pct >= PROFIT_TAKE_EXTREME:
            return True, f"🔴 涨幅{price_change_pct:.1f}%，Dang氏铁律：超50%必须止盈，不管后面涨多少那是别人的钱！"
        elif price_change_pct >= PROFIT_TAKE_THRESHOLD:
            return True, f"🟠 涨幅{price_change_pct:.1f}%，达到30%止盈线，Dang氏建议落袋为安"
        
        return False, ""
    
    def check_rebuy_opportunity(self, price_drop_pct: Optional[float]) -> Tuple[bool, str]:
        """
        检查是否有补仓机会
        
        Args:
            price_drop_pct: 从高点下跌百分比
            
        Returns:
            (是否可补仓, 点评)
        """
        if price_drop_pct is None:
            return False, ""
        
        if price_drop_pct >= REBUY_DROP_IDEAL:
            return True, f"✅ 下跌{price_drop_pct:.1f}%，达到理想补仓位，可拉开距离建仓"
        elif price_drop_pct >= REBUY_DROP_THRESHOLD:
            return True, f"⚡ 下跌{price_drop_pct:.1f}%，可考虑小额补仓"
        
        return False, "跌幅不足10%，Dang氏说不要急着补仓"
    
    def analyze(
        self,
        industry: str = "",
        pe: Optional[float] = None,
        dividend_yield: Optional[float] = None,
        price_change_pct: Optional[float] = None,
        price_from_high_pct: Optional[float] = None,
        shareholder_selling: bool = False,
    ) -> DangAnalysisResult:
        """
        综合分析
        
        Args:
            industry: 行业名称
            pe: 市盈率
            dividend_yield: 股息率
            price_change_pct: 涨幅百分比
            price_from_high_pct: 距离高点跌幅
            shareholder_selling: 是否有大股东减持
            
        Returns:
            DangAnalysisResult
        """
        result = DangAnalysisResult()
        
        # 1. 行业分析
        result.industry_tier, result.industry_comment = self.classify_industry(industry)
        result.stock_type = self.classify_stock_type(industry)
        
        # 2. 估值分析
        result.pe_status, result.pe_score, result.pe_comment = self.evaluate_pe(pe, result.stock_type)
        
        # 3. 股息分析
        result.dividend_status, result.dividend_score, result.dividend_comment = self.evaluate_dividend(dividend_yield)
        
        # 4. 止盈检查
        result.profit_take_alert, profit_comment = self.check_profit_take(price_change_pct)
        if profit_comment:
            result.risk_items.append(profit_comment)
        
        # 5. 补仓机会检查
        result.rebuy_opportunity, rebuy_comment = self.check_rebuy_opportunity(price_from_high_pct)
        
        # 6. 风险项和扣分
        if result.profit_take_alert:
            result.risk_penalty += RISK_PENALTIES["profit_take_warning"]
        
        if shareholder_selling:
            result.risk_penalty += RISK_PENALTIES["shareholder_selling"]
            result.risk_items.append("⚠️ 大股东减持，心里要有疙瘩")
        
        if result.industry_tier == IndustryTier.BLACKLIST:
            result.risk_penalty += RISK_PENALTIES["blacklist_industry"]
            result.risk_items.append(result.industry_comment)
        
        if result.pe_status == "危险":
            result.risk_penalty += RISK_PENALTIES["pe_too_high"]
            result.risk_items.append(result.pe_comment)
        
        if result.dividend_status == "差":
            result.risk_penalty += RISK_PENALTIES["no_dividend"]
        
        # 7. 计算基本面总分
        industry_score = {
            IndustryTier.PREFERRED: 15,
            IndustryTier.NORMAL: 10,
            IndustryTier.CAUTION: 5,
            IndustryTier.BLACKLIST: 0,
        }.get(result.industry_tier, 10)
        
        result.fundamental_score = result.pe_score + result.dividend_score + industry_score + result.risk_penalty
        result.fundamental_score = max(0, min(60, result.fundamental_score))  # 限制在0-60
        
        # 8. 生成Dang氏风格点评
        result.dang_comment = self._generate_dang_comment(result)
        
        return result
    
    def _generate_dang_comment(self, result: DangAnalysisResult) -> str:
        """生成Dang氏风格点评"""
        comments = []
        
        # 止盈优先
        if result.profit_take_alert:
            comments.append("兄弟，该止盈就止盈，后面涨多少那是别人的钱。")
        
        # 行业点评
        if result.industry_tier == IndustryTier.PREFERRED:
            comments.append("生产资料到手，拿着踏实。有的，兄弟，有的。")
        elif result.industry_tier == IndustryTier.BLACKLIST:
            comments.append("这种内卷行业，大家都觉得自己能卷死对手，最后一起死。我不碰。")
        
        # 估值点评
        if result.pe_status == "危险":
            comments.append(f"300PE的科技股，故事讲得再好，没有信仰，跌下来你拿不住。")
        elif result.pe_status == "理想":
            comments.append("这个估值，模糊的正确远胜精确的错误，干就完了。")
        
        # 股息点评
        if result.dividend_status == "优秀":
            comments.append("5%以上的股息，这才是我要的生产资料。")
        elif result.dividend_status == "差":
            comments.append("不分红？那不是耍流氓嘛。")
        
        if not comments:
            comments.append("继续观察，鄙人不善择时。")
        
        return " ".join(comments)


# ========================================
# 便捷函数
# ========================================

def analyze_stock_dang_style(
    industry: str = "",
    pe: Optional[float] = None,
    dividend_yield: Optional[float] = None,
    price_change_pct: Optional[float] = None,
) -> DangAnalysisResult:
    """
    Dang氏风格分析便捷函数
    
    Args:
        industry: 行业名称
        pe: 市盈率
        dividend_yield: 股息率
        price_change_pct: 涨幅百分比
        
    Returns:
        DangAnalysisResult
    """
    filter = DangFilter()
    return filter.analyze(
        industry=industry,
        pe=pe,
        dividend_yield=dividend_yield,
        price_change_pct=price_change_pct,
    )


if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    # 测试代码
    filter = DangFilter()
    
    # 测试1: 银行股
    print("=" * 50)
    print("测试1: 招商银行")
    result = filter.analyze(
        industry="银行",
        pe=5.5,
        dividend_yield=5.8,
    )
    print(f"行业: {result.industry_tier.value} - {result.industry_comment}")
    print(f"PE: {result.pe_status} ({result.pe_score}分) - {result.pe_comment}")
    print(f"股息: {result.dividend_status} ({result.dividend_score}分) - {result.dividend_comment}")
    print(f"基本面总分: {result.fundamental_score}/60")
    print(f"Dang氏点评: {result.dang_comment}")
    
    # 测试2: 光伏股
    print("\n" + "=" * 50)
    print("测试2: 某光伏企业")
    result = filter.analyze(
        industry="光伏设备",
        pe=35,
        dividend_yield=0.5,
    )
    print(f"行业: {result.industry_tier.value} - {result.industry_comment}")
    print(f"PE: {result.pe_status} ({result.pe_score}分) - {result.pe_comment}")
    print(f"股息: {result.dividend_status} ({result.dividend_score}分) - {result.dividend_comment}")
    print(f"基本面总分: {result.fundamental_score}/60")
    print(f"Dang氏点评: {result.dang_comment}")
    
    # 测试3: 高估值科技股
    print("\n" + "=" * 50)
    print("测试3: 某科技股（PE 350）")
    result = filter.analyze(
        industry="科技",
        pe=350,
        dividend_yield=0,
        price_change_pct=45,
    )
    print(f"行业: {result.industry_tier.value} - {result.industry_comment}")
    print(f"PE: {result.pe_status} ({result.pe_score}分) - {result.pe_comment}")
    print(f"股息: {result.dividend_status} ({result.dividend_score}分) - {result.dividend_comment}")
    print(f"止盈警告: {result.profit_take_alert}")
    print(f"风险项: {result.risk_items}")
    print(f"基本面总分: {result.fundamental_score}/60")
    print(f"Dang氏点评: {result.dang_comment}")
