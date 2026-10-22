from pathlib import Path
import argparse
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.experiments import run_experiments

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='运行实验三全部场景与参数对比')
    parser.add_argument('--max-side', type=int, default=1200)
    args = parser.parse_args()
    run_experiments(ROOT, args.max_side)
