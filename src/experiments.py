"""可复现的三场景实验、参数消融、受控亮度变化及三图扩展。"""
import csv
import json
import platform
import os
import sys
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .stitching import (read_image, save_image, extract_features, estimate_homography,
                        stitch_pair, draw_matches, warp_layers, blend_layers, StitchingError)

SCENES = {'boat': ('boat1.jpg', 'boat2.jpg'),
          'budapest': ('budapest1.jpg', 'budapest2.jpg'),
          'newspaper': ('newspaper1.jpg', 'newspaper2.jpg')}


def panel(path, images, titles, columns=2):
    rows = (len(images) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(14, 4 * rows), squeeze=False)
    for ax, image, title in zip(axes.flat, images, titles):
        ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax.set_title(title, fontsize=11); ax.axis('off')
    for ax in list(axes.flat)[len(images):]:
        ax.axis('off')
    fig.tight_layout(); fig.savefig(path, dpi=130, bbox_inches='tight'); plt.close(fig)


def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def run_experiments(root, max_side=1200):
    root = Path(root); out = root / 'results'; out.mkdir(exist_ok=True)
    cv2.setNumThreads(1)
    summary, sweep = [], []
    all_images = []; titles = []
    for name, files in SCENES.items():
        a, b = [read_image(root / 'data' / file, max_side) for file in files]
        all_images.extend([a, b]); titles.extend([files[0], files[1]])
        fit = stitch_pair(a, b)
        for mode in ('feather', 'overwrite'):
            save_image(out / f'{name}_{mode}.jpg', fit[mode])
        save_image(out / f'{name}_matches.jpg', draw_matches(a, b, fit))
        kp = cv2.drawKeypoints(a, fit['features_a'].keypoints[:500], None,
                               flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        save_image(out / f'{name}_keypoints.jpg', kp)
        panel(out / f'{name}_comparison.png', [fit['overwrite'], fit['feather']],
              ['Direct overwrite (reference baseline)', 'Distance feather blending'])
        row = dict(scene=name, input_a=files[0], input_b=files[1],
                   width_a=a.shape[1], height_a=a.shape[0], width_b=b.shape[1], height_b=b.shape[0],
                   **fit['metrics'])
        summary.append(row)
        (out / f'{name}_homography.json').write_text(json.dumps(
            {'direction': 'B_to_A', 'H': fit['H'].tolist(), 'T': fit['T'].tolist()}, indent=2), encoding='utf-8')
        features = (fit['features_a'], fit['features_b'])
        for ratio in (0.55, 0.65, 0.70, 0.75, 0.85):
            for threshold in (2.0, 5.0):
                try:
                    result = estimate_homography(a, b, ratio, threshold, features)
                    m = result['metrics']
                    sweep.append(dict(scene=name, ratio=ratio, ransac_threshold_px=threshold,
                                      good_matches=m['good_matches'], inliers=m['inliers'],
                                      inlier_ratio=m['inlier_ratio'], inlier_rmse_px=m['inlier_rmse_px'], status='ok'))
                except StitchingError as e:
                    sweep.append(dict(scene=name, ratio=ratio, ransac_threshold_px=threshold,
                                      good_matches='', inliers='', inlier_ratio='', inlier_rmse_px='', status=str(e)))
        print(name, json.dumps(fit['metrics']), flush=True)
    panel(out / 'inputs.png', all_images, titles)
    write_csv(out / 'metrics.csv', summary); write_csv(out / 'parameter_sweep.csv', sweep)
    # 固定基础 H，只改变 B 的亮度，隔离几何估计与曝光变化。
    a, b = [read_image(root/'data'/f, max_side) for f in SCENES['boat']]
    basic = stitch_pair(a, b)
    darker = np.clip(b.astype(np.float32)*0.65, 0, 255).astype(np.uint8)
    layers, masks, _ = warp_layers([a, darker], [np.eye(3), basic['H']])
    hard, soft = [blend_layers(layers, masks, mode) for mode in ('overwrite', 'feather')]
    save_image(out/'boat_dark_overwrite.jpg', hard); save_image(out/'boat_dark_feather.jpg', soft)
    panel(out/'brightness_comparison.png', [hard, soft],
          ['B intensity x 0.65: overwrite', 'B intensity x 0.65: feather (no exposure correction)'])
    # 三图以 boat2 为统一参考，直接估计左右图到参考图的变换。
    images = [read_image(root/'data'/f'boat{i}.jpg', max_side) for i in (1,2,3)]
    f1 = estimate_homography(images[1], images[0]); f3 = estimate_homography(images[1], images[2])
    layers, masks, T = warp_layers(images, [f1['H'], np.eye(3), f3['H']])
    triple = blend_layers(layers, masks)
    save_image(out/'boat_three_images.jpg', triple)
    triple_info = dict(reference='boat2.jpg', width=triple.shape[1], height=triple.shape[0],
                       boat1_to_boat2=f1['metrics'], boat3_to_boat2=f3['metrics'],
                       H1=f1['H'].tolist(), H3=f3['H'].tolist(), T=T.tolist())
    (out/'three_image_metrics.json').write_text(json.dumps(triple_info, indent=2), encoding='utf-8')
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, scene in zip(axes, SCENES):
        for threshold, style in [(2.0, '-o'), (5.0, '-s')]:
            rows = [r for r in sweep if r['scene']==scene and r['ransac_threshold_px']==threshold and r['status']=='ok']
            ax.plot([r['ratio'] for r in rows], [r['inlier_ratio'] for r in rows], style, label=f'RANSAC {threshold:g} px')
        ax.set(title=scene, xlabel='Lowe ratio', ylabel='Inlier fraction', ylim=(0,1.05))
        ax.grid(alpha=.25); ax.legend()
    fig.tight_layout(); fig.savefig(out/'parameter_sweep.png',dpi=160); plt.close(fig)
    environment = dict(python=platform.python_version(), platform=platform.platform(),
                       opencv=cv2.__version__, numpy=np.__version__, matplotlib=matplotlib.__version__,
                       max_side=max_side, seed=42, opencv_threads=1,
                       conda_environment=os.environ.get('CONDA_DEFAULT_ENV', Path(sys.prefix).name),
                       conda_runtime=(Path(sys.prefix)/'conda-meta').is_dir(),
                       note='Timing is one run, including feature extraction, warping and two blending modes; excludes IO.')
    (out/'environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary, sweep, triple_info
