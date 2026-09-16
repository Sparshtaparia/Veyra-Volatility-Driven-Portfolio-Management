import sys
import pandas as pd
from datetime import date

from quant_engine.backtest.models import PipelineBacktestConfig
from quant_engine.backtest.pipeline_engine import PipelineBacktester
from quant_engine.backtest.benchmarks import compute_equal_weight_benchmark
from quant_engine.data.provider import YahooChartProvider


def main():
    print("Starting Veyra Backtest (Phase 1-8 pipeline)")
    
    # Configure Backtest
    # Use 3 diverse large-cap stocks to keep the GARCH model stable
    # GARCH needs ~252 observations, so we need enough history before start_date
    config = PipelineBacktestConfig(
        start_date=date(2022, 1, 1),
        end_date=date(2023, 12, 31),
        universe=["SPY", "QQQ", "TLT"],
        rebalance_threshold=0.03,
        transaction_cost_bps=5.0,
        slippage_bps=2.0
    )
    
    provider = YahooChartProvider()
    
    print("Fetching benchmark data (Equal Weight)...")
    # Benchmark runs over the evaluation period
    benchmark_returns = compute_equal_weight_benchmark(
        provider, config.universe, config.start_date, config.end_date
    )
    
    print("Running PipelineBacktester...")
    tester = PipelineBacktester(provider, config)
    result = tester.run("Phase 9 Validation", benchmark_returns)
    
    print("\n--- BACKTEST RESULTS ---")
    print(f"Evaluations: {result.evaluations_count}")
    print(f"Rebalances:  {result.rebalances_count}")
    
    m = result.metrics
    b = result.benchmark_metrics
    
    def pct(v):
        return f"{v * 100:.2f}%"
        
    print(f"\nMetric           | Veyra       | Benchmark (EW)")
    print(f"-----------------|-------------|---------------")
    print(f"Total Return     | {pct(m.total_return):<11} | {pct(b.total_return)}")
    print(f"CAGR             | {pct(m.cagr):<11} | {pct(b.cagr)}")
    print(f"Volatility (Ann) | {pct(m.volatility):<11} | {pct(b.volatility)}")
    print(f"Max Drawdown     | {pct(m.max_drawdown):<11} | {pct(b.max_drawdown)}")
    print(f"Sharpe Ratio     | {m.sharpe:<11.2f} | {b.sharpe:.2f}")
    
    print("\nThreshold History:")
    for r in result.records:
        print(f"  {r.evaluation_date}: {r.adaptive_threshold:.4f} (Rebalanced: {r.rebalance_executed})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
