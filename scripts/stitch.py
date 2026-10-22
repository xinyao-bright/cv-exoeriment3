from pathlib import Path
import argparse
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.stitching import read_image, stitch_pair, save_image, draw_matches

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='拼接两张重叠照片，H 方向为 B -> A')
    parser.add_argument('a'); parser.add_argument('b')
    parser.add_argument('--output', default='results/custom.jpg')
    parser.add_argument('--ratio', type=float, default=.7)
    parser.add_argument('--ransac', type=float, default=5.)
    args = parser.parse_args()
    a,b = read_image(args.a), read_image(args.b)
    fit = stitch_pair(a,b,args.ratio,args.ransac)
    save_image(args.output,fit['feather'])
    save_image(Path(args.output).with_name(Path(args.output).stem+'_matches.jpg'),draw_matches(a,b,fit))
    print(json.dumps(fit['metrics'],indent=2))
