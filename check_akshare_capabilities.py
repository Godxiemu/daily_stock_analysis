# -*- coding: utf-8 -*-
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import logging
import sys
import io

# Set encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_history_valuation(code):
    """验证获取历史估值分位能力"""
    logger.info(f"正在获取 {code} 的历史估值数据 (可能较慢)...")
    try:
        # 尝试 stock_zh_valuation_baidu (A股个股估值)
        try:
             # indicator='市盈率(TTM)'
             df_pe = ak.stock_zh_valuation_baidu(symbol=code, indicator="市盈率(TTM)", period="近10年")
        except AttributeError:
             logger.warning("stock_zh_valuation_baidu 未找到")
             return False
        
        if df_pe.empty:
            logger.error("获取百度估值数据失败: 返回空数据")
            return False
        
        if 'date' in df_pe.columns:
             df_pe['trade_date'] = pd.to_datetime(df_pe['date'])
             val_col = 'value'
        elif 'value' in df_pe.columns:
             df_pe['trade_date'] = df_pe.index
             val_col = 'value'
        else:
             logger.error(f"百度数据列名异常: {df_pe.columns}")
             return False
             
        # 筛选近10年
        ten_years_ago = datetime.now() - timedelta(days=365*10)
        df_10y = df_pe[df_pe['trade_date'] > ten_years_ago].copy()
        
        if df_10y.empty:
            logger.warning("无近10年数据")
            df_10y = df_pe
            
        current_pe = df_10y[val_col].iloc[-1]
        
        # 计算分位
        pe_rank = (df_10y[val_col] < current_pe).mean() * 100
        
        logger.info(f"历史数据(PE-TTM)获取成功! (条数: {len(df_10y)})")
        logger.info(f"   当前 PE(TTM): {current_pe:.2f} (10年分位: {pe_rank:.1f}%)")
        
        return True

    except Exception as e:
        logger.error(f"历史估值获取异常: {e}")
        return False

def check_peer_comparison(code):
    """验证同业比价获取能力"""
    logger.info(f"正在分析 {code} 的同业数据...")
    try:
        # 1. 获取个股资料中的行业
        info = ak.stock_individual_info_em(symbol=code)
        industry_row = info[info['item'] == '行业']
        if industry_row.empty:
            logger.error("无法识别行业")
            return False
            
        industry = industry_row.iloc[0]['value']
        logger.info(f"   识别行业: {industry}")
        
        # 2. 获取该行业所有股票
        peers_df = ak.stock_board_industry_cons_em(symbol=industry)
        
        if peers_df.empty:
            logger.warning(f"无法获取 {industry} 行业成分股")
            return False
        
        # 3. 寻找总市值列 (Fuzzy Match)
        mv_col = None
        for col in peers_df.columns:
            if '市值' in col and '总' in col:
                mv_col = col
                break
        
        if not mv_col:
            # Fallback: try just '市值'
            for col in peers_df.columns:
                if '市值' in col:
                    mv_col = col
                    break
        
        if not mv_col:
            logger.error(f"无法找到市值列, 现有列名: {peers_df.columns.tolist()}")
            return False
            
        # 排序
        peers_df.sort_values(by=mv_col, ascending=False, inplace=True)
        top_peers = peers_df.head(5)
        
        logger.info(f"获取同业成功! {industry} 行业共 {len(peers_df)} 只股票")
        logger.info(f"   行业龙头示例: {top_peers['名称'].tolist()}")
        
        return True
        
    except Exception as e:
        logger.error(f"同业数据获取异常: {e}")
        return False

if __name__ == "__main__":
    test_code = '600036' # 招商银行
    print(f"=== AkShare 数据能力验证 ({test_code}) ===")
    
    # 验证能力 1: 10年估值分位
    can_get_history = check_history_valuation(test_code)
    
    print("\n" + "-"*30 + "\n")
    
    # 验证能力 2: 同业比价
    can_get_peer = check_peer_comparison(test_code)
    
    print("\n" + "="*30)
    if can_get_history and can_get_peer:
        print("结论: AkShare 完全支持完整升级方案！")
    else:
        print("结论: 部分数据可能存在获取困难。")
