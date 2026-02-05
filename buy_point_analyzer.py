import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np

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
    ma120_status: str  # 价格小于MA120 / 价格≈MA120 / 价格大于MA120
    ma120_deviation: float  # 相对MA120的偏离度 (%)
    
    # 关键价位
    add_price: Optional[float] = None # 加仓位
    add_price_desc: str = ""  # 加仓位描述（如：MA20支撑/黄金分割0.618）
    take_profit_price: Optional[float] = None # 止盈位
    stop_loss_price: Optional[float] = None # 止损位
    
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
            return None
            
        try:
            # 获取最新数据 (使用最后一行)
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 基础数据
            current_price = float(latest['close'])
            if realtime_quote and realtime_quote.get('price', 0) > 0:
                current_price = float(realtime_quote['price'])
                
            # 获取均线数据
            ma5 = float(latest.get('ma5', 0))
            ma10 = float(latest.get('ma10', 0))
            ma20 = float(latest.get('ma20', 0))
            ma120 = float(latest.get('ma120', 0))
            volume_ratio = float(latest.get('volume_ratio', 1.0))
            
            # 如果数据库中没有 ma120，尝试从历史数据动态计算
            if ma120 <= 0 and len(df) >= 20:
                # 计算 MA120
                close_series = df['close'].astype(float)
                if len(close_series) >= 120:
                    ma120 = close_series.tail(120).mean()
                else:
                    ma120 = close_series.mean()
                logger.debug(f"动态计算 MA120 = {ma120:.2f}")
            
            if ma120 <= 0:
                logger.warning("MA120 数据无效（数据不足）")
                return None
            
            # 1. 计算 MA120 状态和偏离度
            ma120_deviation = ((current_price - ma120) / ma120) * 100
            if ma120_deviation < -3:
                ma120_status = "价格小于MA120"
            elif ma120_deviation <= 3:
                ma120_status = "价格≈MA120"
            else:
                ma120_status = "价格大于MA120"
            
            # 2. 判断短期信号
            short_signal, short_signal_detail = self._analyze_short_signal(
                current_price, ma5, ma10, ma20, volume_ratio, df
            )
            
            # 3. 综合判定标签
            label, label_text = self._determine_label(short_signal, ma120_status, ma120_deviation)
            
            # 4. 计算关键价位 (优化逻辑)
            ma_dict = {
                'MA5': ma5, 'MA10': ma10, 'MA20': ma20, 'MA120': ma120
            }
            add_price, add_price_desc = self._calculate_support_price(df, current_price, ma_dict)
            
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
                add_price_desc=add_price_desc,
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
    ) -> Tuple[str, str]:
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
                return "放量突破", f"量比{volume_ratio:.2f}, 突破近期高点"
            else:
                return "放量上行", f"量比{volume_ratio:.2f}, 均线上方"
                
        # 破位型（MA20作为生命线）
        if ma20 > 0 and price < ma20 * 0.98:
            return "破位", "跌破MA20支撑"
            
        # 乖离过大（短期风险）
        if bias_ma5 > 5 or bias_ma10 > 8:
            return "乖离过大", f"MA5乖离{bias_ma5:.1f}%, 追高风险"
        
        return "无信号", "等待明确信号"
    
    def _determine_label(self, short_signal: str, ma120_status: str, ma120_deviation: float) -> Tuple[str, str]:
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
            if ma120_status == "价格小于MA120":
                return "⭐", "最佳买点"
            elif ma120_status == "价格≈MA120":
                return "🟢", "良好买点"
            else:
                return "🟢", "良好买点"
        
        # 无信号但在 MA120 以下
        if ma120_status == "价格小于MA120" and ma120_deviation < -5:
            return "🟡", "观望(价值区)"
        
        return "🟡", "观望"
    
    
    def _calculate_support_price(
        self, 
        df: pd.DataFrame, 
        current_price: float, 
        ma_dict: dict
    ) -> Tuple[Optional[float], str]:
        """
        计算支撑位（加仓点）
        策略：黄金分割 + 均线共振
        """
        try:
            if len(df) < 60:
                # 数据不足，仅使用均线
                candidates = []
                for name, val in ma_dict.items():
                    if 0 < val < current_price:
                        candidates.append((val, f"{name}支撑"))
                
                if candidates:
                    # 返回最大的那个（最近的支撑）
                    best = max(candidates, key=lambda x: x[0])
                    return round(best[0], 2), best[1]
                return None, ""
            
            # 1. 计算黄金分割位 (近60日)
            recent_high = df['high'].tail(60).max()
            recent_low = df['low'].tail(60).min()
            price_range = recent_high - recent_low
            
            fib_levels = {
                0.382: recent_high - price_range * 0.382,
                0.500: recent_high - price_range * 0.500,
                0.618: recent_high - price_range * 0.618
            }
            
            # 2. 寻找共振（黄金分割 ±1.5% 范围内有均线）
            resonance_supports = []
            
            for ratio, fib_price in fib_levels.items():
                if fib_price >= current_price: continue  # 只找下方的
                
                # 检查是否有均线在此位置附近
                matched_mas = []
                for ma_name, ma_val in ma_dict.items():
                    if abs(ma_val - fib_price) / fib_price < 0.015:  # 1.5% 误差内
                        matched_mas.append(ma_name)
                
                if matched_mas:
                    desc = f"黄金分割{ratio:.3f} + {'/'.join(matched_mas)}共振"
                    resonance_supports.append((fib_price, desc))
                else:
                    # 单纯黄金分割支撑（权重较低）
                    desc = f"黄金分割{ratio:.3f}支撑"
                    resonance_supports.append((fib_price, desc))
            
            # 3. 加入单纯均线支撑（作为补充）
            for ma_name, ma_val in ma_dict.items():
                if 0 < ma_val < current_price:
                    # 避免与黄金分割重复（如果已经在共振里了，就不加了）
                    is_duplicate = False
                    for res_p, _ in resonance_supports:
                        if abs(res_p - ma_val) / ma_val < 0.015:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        resonance_supports.append((ma_val, f"{ma_name}支撑"))
            
            if not resonance_supports:
                return None, ""
            
            # 4. 选择最优支撑
            # 优先选共振，其次选最近的
            # 这里简化逻辑：直接选下方最近的一个强支撑
            
            # 过滤掉太近的（比如只差 0.5%），除非是暴跌后的反弹
            valid_supports = [s for s in resonance_supports if s[0] < current_price * 0.995]
            
            if not valid_supports:
                # 如果都很近，或者没有下方的，返回空
                return None, ""
            
            # 按价格从高到低排序（离现价最近的）
            valid_supports.sort(key=lambda x: x[0], reverse=True)
            
            # 返回最近的一个
            best_support = valid_supports[0]
            return round(best_support[0], 2), best_support[1]
            
        except Exception as e:
            logger.warning(f"计算支撑位失败: {e}")
            return None, ""

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
            if ma120_status == "价格小于MA120":
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
            if result.add_price_desc:
                key_prices.append(f"加仓:{result.add_price}({result.add_price_desc})")
            else:
                key_prices.append(f"加仓:{result.add_price}")
        
        if result.take_profit_price:
            key_prices.append(f"止盈:{result.take_profit_price}")
            
        if result.stop_loss_price:
            key_prices.append(f"止损:{result.stop_loss_price}")
            
        if key_prices:
            lines.append(f"💼 关键位：{' | '.join(key_prices)}")
            
        lines.append("")
        return lines
