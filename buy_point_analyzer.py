"""
复合技术买点分析器

结合短期技术信号和 MA120（半年线）的复合买点分析系统
输出标签化的买卖建议
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BuyPointResult:
    """买点分析结果"""
    # 买点标签: ⭐最佳买点 / 🟢良好买点 / 🟡观望 / 🔴规避
    label: str
    label_text: str
    
    # 短期信号
    short_signal: str  # 缩量回踩 / 放量突破 / 无信号 / 破位
    short_signal_detail: str
    
    # MA120 状态
    ma120_status: str  # 价格<MA120 / 价格≈MA120 / 价格>MA120
    ma120_deviation: float  # 相对MA120的偏离度 (%)
    
    # 关键价位
    add_price: Optional[float]  # 加仓位
    take_profit_price: Optional[float]  # 止盈位
    stop_loss_price: Optional[float]  # 止损位
    
    # 当前建议
    current_advice: str
    
    # 原始数据
    current_price: float
    ma5: float
    ma10: float
    ma20: float
    ma120: float
    volume_ratio: float


class BuyPointAnalyzer:
    """复合买点分析器"""
    
    def __init__(self):
        pass
    
    def analyze(
        self, 
        df: pd.DataFrame, 
        realtime_quote: Optional[Dict[str, Any]] = None
    ) -> Optional[BuyPointResult]:
        """
        分析买点
        
        Args:
            df: 历史K线数据 (需包含 close, ma5, ma10, ma20, ma120, volume_ratio)
            realtime_quote: 实时行情 (可选)
            
        Returns:
            BuyPointResult 或 None
        """
        if df is None or df.empty or len(df) < 5:
            logger.warning("数据不足，无法分析买点")
            return None
        
        try:
            # 获取最新数据
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # 使用实时价格或最新收盘价
            current_price = float(realtime_quote.get('current_price', latest['close'])) if realtime_quote else float(latest['close'])
            
            # 获取均线数据
            ma5 = float(latest.get('ma5', 0))
            ma10 = float(latest.get('ma10', 0))
            ma20 = float(latest.get('ma20', 0))
            ma120 = float(latest.get('ma120', 0))
            volume_ratio = float(latest.get('volume_ratio', 1.0))
            
            # 如果数据库中没有 ma120，尝试从历史数据动态计算
            if ma120 <= 0 and len(df) >= 20:
                # 计算 MA120（需要至少20条数据，使用可用的全部数据）
                close_series = df['close'].astype(float)
                if len(close_series) >= 120:
                    ma120 = close_series.tail(120).mean()
                else:
                    # 数据不足120天，使用所有可用数据计算
                    ma120 = close_series.mean()
                logger.info(f"动态计算 MA120 = {ma120:.2f} (基于 {len(close_series)} 天数据)")
            
            if ma120 <= 0:
                logger.warning("MA120 数据无效（数据不足）")
                return None
            
            # 1. 计算 MA120 状态和偏离度
            ma120_deviation = ((current_price - ma120) / ma120) * 100
            if ma120_deviation < -3:
                ma120_status = "价格<MA120"
            elif ma120_deviation <= 3:
                ma120_status = "价格≈MA120"
            else:
                ma120_status = "价格>MA120"
            
            # 2. 判断短期信号
            short_signal, short_signal_detail = self._analyze_short_signal(
                current_price, ma5, ma10, ma20, volume_ratio, df
            )
            
            # 3. 综合判定标签
            label, label_text = self._determine_label(short_signal, ma120_status, ma120_deviation)
            
            # 4. 计算关键价位
            add_price = round(ma10, 2) if ma10 > 0 else None
            take_profit_price = self._calculate_take_profit(df, current_price)
            stop_loss_price = round(ma20 * 0.98, 2) if ma20 > 0 else None  # MA20 下方 2%
            
            # 5. 生成当前建议
            current_advice = self._generate_advice(label, short_signal, ma120_status, current_price, add_price)
            
            return BuyPointResult(
                label=label,
                label_text=label_text,
                short_signal=short_signal,
                short_signal_detail=short_signal_detail,
                ma120_status=ma120_status,
                ma120_deviation=round(ma120_deviation, 2),
                add_price=add_price,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                current_advice=current_advice,
                current_price=round(current_price, 2),
                ma5=round(ma5, 2),
                ma10=round(ma10, 2),
                ma20=round(ma20, 2),
                ma120=round(ma120, 2),
                volume_ratio=round(volume_ratio, 2)
            )
            
        except Exception as e:
            logger.error(f"买点分析失败: {e}")
            return None
    
    def _analyze_short_signal(
        self, 
        price: float, 
        ma5: float, 
        ma10: float, 
        ma20: float, 
        volume_ratio: float,
        df: pd.DataFrame
    ) -> tuple:
        """分析短期信号"""
        
        # 计算乖离率
        bias_ma5 = ((price - ma5) / ma5) * 100 if ma5 > 0 else 0
        bias_ma10 = ((price - ma10) / ma10) * 100 if ma10 > 0 else 0
        
        # 判断均线排列
        is_bullish = ma5 > ma10 > ma20 if all([ma5, ma10, ma20]) else False
        
        # 缩量回踩型（优先）
        if volume_ratio < 0.8 and abs(bias_ma10) < 3 and is_bullish:
            return "缩量回踩", f"量比{volume_ratio:.2f}, 回踩MA10, 均线多头"
        
        if volume_ratio < 0.8 and abs(bias_ma5) < 2:
            return "缩量回踩", f"量比{volume_ratio:.2f}, 回踩MA5"
        
        # 放量突破型
        if volume_ratio > 1.5 and bias_ma5 > 0 and bias_ma5 < 5:
            # 检查是否突破前高
            recent_high = df['high'].tail(20).max() if len(df) >= 20 else df['high'].max()
            if price >= recent_high * 0.98:
                return "放量突破", f"量比{volume_ratio:.2f}, 接近前高"
        
        # 破位信号
        if price < ma20 and volume_ratio > 1.2:
            return "破位", f"跌破MA20, 量比{volume_ratio:.2f}"
        
        # 乖离过大（追高风险）
        if bias_ma5 > 5 or bias_ma10 > 8:
            return "乖离过大", f"MA5乖离{bias_ma5:.1f}%, 追高风险"
        
        return "无信号", "等待明确信号"
    
    def _determine_label(self, short_signal: str, ma120_status: str, ma120_deviation: float) -> tuple:
        """综合判定标签"""
        
        # 破位 → 规避
        if short_signal == "破位":
            return "🔴", "规避"
        
        # 乖离过大 → 观望
        if short_signal == "乖离过大":
            return "🟡", "观望"
        
        # 有短期信号
        if short_signal in ["缩量回踩", "放量突破"]:
            # MA120 加分
            if ma120_status == "价格<MA120":
                return "⭐", "最佳买点"
            elif ma120_status == "价格≈MA120":
                return "🟢", "良好买点"
            else:
                return "🟢", "良好买点"
        
        # 无信号但在 MA120 以下
        if ma120_status == "价格<MA120" and ma120_deviation < -5:
            return "🟡", "观望(价值区)"
        
        return "🟡", "观望"
    
    def _calculate_take_profit(self, df: pd.DataFrame, current_price: float) -> Optional[float]:
        """计算止盈位（前高压力）"""
        try:
            if len(df) < 20:
                return None
            recent_high = df['high'].tail(60).max()
            if recent_high > current_price * 1.03:  # 至少有3%空间
                return round(recent_high, 2)
            return None
        except:
            return None
    
    def _generate_advice(
        self, 
        label: str, 
        short_signal: str, 
        ma120_status: str, 
        current_price: float,
        add_price: Optional[float]
    ) -> str:
        """生成当前建议"""
        
        if label == "⭐":
            if short_signal == "缩量回踩":
                return f"可分批建仓，回踩{add_price}元附近可加仓"
            else:
                return "可适量建仓，注意控制仓位"
        
        elif label == "🟢":
            if short_signal == "缩量回踩":
                return f"可小仓试探，等待回踩{add_price}元加仓"
            else:
                return "可关注，突破后轻仓跟进"
        
        elif label == "🔴":
            return "建议暂时规避，等待企稳信号"
        
        else:  # 🟡
            if ma120_status == "价格<MA120":
                return "处于价值区，可等待短期买点信号"
            else:
                return "暂无明确信号，继续观察"
    
    def to_report_section(self, result: BuyPointResult) -> list:
        """生成报告板块内容"""
        lines = [
            "#### 📊 技术面买点分析",
            "",
            f"**{result.label} {result.label_text}**",
            "",
            f"├─ 短期信号：{result.short_signal} ({result.short_signal_detail})",
            f"├─ MA120状态：{result.ma120_status} ({result.ma120_deviation:+.1f}%)",
            f"└─ 量比：{result.volume_ratio}",
            "",
        ]
        
        # 当前建议
        lines.append(f"📌 **建议**：{result.current_advice}")
        lines.append("")
        
        # 关键价位
        key_prices = []
        if result.add_price:
            key_prices.append(f"加仓:{result.add_price}")
        if result.take_profit_price:
            key_prices.append(f"止盈:{result.take_profit_price}")
        if result.stop_loss_price:
            key_prices.append(f"止损:{result.stop_loss_price}")
        
        if key_prices:
            lines.append(f"💼 关键位：{' | '.join(key_prices)}")
            lines.append("")
        
        return lines
