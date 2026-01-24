# -*- coding: utf-8 -*-
"""
===================================
Dang氏预期股息率分析器
===================================

核心逻辑：基于Mr. Dang的"真实股息率"（预期股息率）测算五步法
公式：预期股息率 = (预测EPS * 预测派息率) / 当前股价

Author: Godxiemu (User) / Antigravity (Agent)
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from data_provider.akshare_fetcher import AkshareFetcher # Reuse random sleep logic if needed, or just import akshare
import akshare as ak

logger = logging.getLogger(__name__)

class DividendAnalyzer:
    """
    股息率分析器
    """
    
    def __init__(self):
        pass

    def get_dividend_history(self, code: str) -> pd.DataFrame:
        """获取分红历史数据"""
        try:
            # ak.stock_fhps_detail_ths 返回: 报告期, 分红方案说明, 股利支付率, etc.
            df = ak.stock_fhps_detail_ths(symbol=code)
            return df
        except Exception as e:
            logger.warning(f"获取分红历史失败 {code}: {e}")
            return pd.DataFrame()

    def calculate_avg_payout_ratio(self, df: pd.DataFrame, years: int = 3) -> float:
        """
        计算平均股利支付率 (Payout Ratio)
        
        Args:
            df: 分红历史 DataFrame
            years: 计算最近几年 (默认3年)
            
        Returns:
            float: 平均支付率 (0.0 - 1.0)
        """
        if df.empty:
            return 0.0
            
        # 筛选"年报"数据 (中期分红通常只是补充，但也可能包含。通常PayoutRatio是基于全年的)
        # akshare数据的'报告期'如 '2023年报', '2023中报'
        # '股利支付率' 列通常只有年报有完整统计，或者是单次的。
        # 让我们过滤出 '年报'
        annual_df = df[df['报告期'].str.contains('年报', na=False)].copy()
        
        # 排序：报告期降序 (最近的在前)
        annual_df.sort_values(by='报告期', ascending=False, inplace=True)
        
        # 取最近N年
        recent = annual_df.head(years)
        
        payouts = []
        for val in recent['股利支付率']:
            if pd.isna(val) or val == '--':
                continue
            # 格式可能为 '30.5%'
            try:
                payout = float(val.strip('%')) / 100.0
                if 0 < payout < 2.0: # 过滤异常值 (大于200%可能是一次性分配)
                    payouts.append(payout)
            except:
                continue
                
        if not payouts:
            return 0.0
            
        return sum(payouts) / len(payouts)

    def get_stock_type(self, code: str) -> str:
        """获取股票类型 (bank/cyclical/tech/utility/other)"""
        try:
            # 获取个股信息
            # ak.stock_individual_info_em(symbol="600036") -> 
            # item | value
            # 行业 | 银行
            df = ak.stock_individual_info_em(symbol=code)
            industry_row = df[df['item'] == '行业']
            if not industry_row.empty:
                industry = industry_row.iloc[0]['value']
                
                if '银行' in industry:
                    return 'bank'
                elif any(x in industry for x in ['煤炭', '有色', '钢铁', '石油', '化工', '海运']):
                    return 'cyclical'
                elif any(x in industry for x in ['科技', '软件', '半导体', '电子']):
                    return 'tech'
                elif any(x in industry for x in ['电力', '水务', '燃气', '高速']):
                    return 'utility'
            return 'default'
        except:
            return 'default'

    def calculate_expected_yield(
        self, 
        code: str, 
        current_price: float, 
        pe_dynamic: float, 
        stock_type: str = None  # Changed to optional
    ) -> Tuple[float, str]:
        """
        计算 Dang氏预期股息率
        
        Args:
            code: 股票代码
            current_price: 当前价格
            pe_dynamic: 动态市盈率
            stock_type: 股票类型 (可选，未指定则自动获取)
            
        Returns:
            (expected_yield, reason)
        """
        if current_price <= 0 or (pe_dynamic is None or pe_dynamic <= 0):
            return 0.0, "价格或PE数据无效"
            
        # 0. 自动获取类型
        if not stock_type:
            stock_type = self.get_stock_type(code)
            
        # 1. 计算基础数据的 预测EPS (Forecast EPS)
        # 逻辑：EPS_Dynamic = Current_Price / PE_Dynamic
        # 这是一个基于当前业绩(年化)的预测
        eps_forecast = current_price / pe_dynamic
        
        # 2. 获取平均派息率 (Base Payout Ratio)
        df = self.get_dividend_history(code)
        if df.empty:
            # 如果没有历史数据，给一个保守默认值
            # 银行/公用事业给30%，其他给0? 
            # Dang氏逻辑：不分红就是耍流氓 -> 0
            base_payout = 0.30 if stock_type in ['bank', 'utility'] else 0.0
            reason_payout = "无历史数据(默认)"
        else:
            base_payout = self.calculate_avg_payout_ratio(df)
            reason_payout = f"三年平均{base_payout*100:.1f}%"
            
        # 3. 行业与类型修正 (Dang Correction)
        final_payout = base_payout
        correction_log = []
        
        if stock_type == 'bank': 
            # A类：稳健型
            # 银行通常稳定，且有30%底线要求
            if final_payout < 0.30:
                final_payout = 0.30
                correction_log.append("银行修正(底线30%)")
        elif stock_type == 'cyclical':
            # B类：周期型
            # 周期高点(PE极低)时，往往为了过冬会降低分红率 -> 保守估计
            pass 
        
        # TODO: 更多复杂的修正逻辑需要读取财报/公告，目前暂无法自动化
        # 比如："大股东缺钱纠正"、"承诺公告纠正"
        
        expected_dividend = eps_forecast * final_payout
        expected_yield = (expected_dividend / current_price) * 100
        
        reason = (
            f"预测EPS {eps_forecast:.2f} (基于PE动{pe_dynamic:.1f}) x "
            f"派息率 {final_payout*100:.1f}% ({reason_payout}{''.join(correction_log)})"
        )
        
        return expected_yield, reason

