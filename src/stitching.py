"""SIFT + FLANN + RANSAC 的透明实现，不调用 cv2.Stitcher。"""
from dataclasses import dataclass
from pathlib import Path
import time
import cv2
import numpy as np


class StitchingError(ValueError):
    """输入、匹配或几何估计不满足拼接条件。"""


@dataclass
class Features:
    keypoints: list
    descriptors: np.ndarray


def read_image(path, max_side=1200):
    """兼容中文路径；等比例缩小以控制 SIFT 和画布内存。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'图像不存在: {path}')
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise StitchingError(f'无法解码图像: {path}')
    scale = min(1.0, max_side / max(image.shape[:2]))
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image


def save_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, data = cv2.imencode(path.suffix, image)
    if not ok:
        raise IOError(f'图像编码失败: {path}')
    data.tofile(str(path))


def extract_features(image, nfeatures=5000):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kp, des = cv2.SIFT_create(nfeatures=nfeatures).detectAndCompute(gray, None)
    if des is None or len(kp) < 4:
        raise StitchingError('有效 SIFT 特征不足；请使用有纹理且存在重叠的照片。')
    return Features(kp, des.astype(np.float32))


def estimate_homography(a, b, ratio=0.7, ransac_threshold=5.0, features=None):
    """匹配 query=A, train=B；返回的 H 始终将 B 坐标映射到 A。"""
    if not 0 < ratio < 1 or ransac_threshold <= 0:
        raise ValueError('ratio 应在 (0,1)，RANSAC 阈值应大于 0。')
    cv2.setRNGSeed(42)
    fa, fb = features if features is not None else (extract_features(a), extract_features(b))
    matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
    knn = matcher.knnMatch(fa.descriptors, fb.descriptors, k=2)
    good = [pair[0] for pair in knn if len(pair) == 2 and pair[0].distance < ratio * pair[1].distance]
    if len(good) < 8:
        raise StitchingError(f'仅有 {len(good)} 个候选匹配，至少需要 8 个可靠候选。')
    src = np.float32([fb.keypoints[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([fa.keypoints[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransac_threshold,
                                 maxIters=5000, confidence=0.995)
    if H is None or mask is None or not np.isfinite(H).all() or abs(H[2, 2]) < 1e-12:
        raise StitchingError('单应矩阵估计失败或退化。')
    H = H / H[2, 2]
    inside = mask.ravel().astype(bool)
    if inside.sum() < 8 or inside.mean() < 0.2 or np.linalg.matrix_rank(H) < 3:
        raise StitchingError(f'几何一致性不足: {inside.sum()}/{len(good)} 个内点。')
    errors = np.linalg.norm((cv2.perspectiveTransform(src, H) - dst).reshape(-1, 2), axis=1)
    metrics = dict(keypoints_a=len(fa.keypoints), keypoints_b=len(fb.keypoints),
                   knn_pairs=len(knn), good_matches=len(good), inliers=int(inside.sum()),
                   inlier_ratio=float(inside.mean()),
                   inlier_rmse_px=float(np.sqrt(np.mean(errors[inside] ** 2))),
                   inlier_median_px=float(np.median(errors[inside])),
                   ratio=ratio, ransac_threshold_px=ransac_threshold)
    return dict(H=H, mask=inside, matches=good, features_a=fa, features_b=fb,
                errors=errors, metrics=metrics)


def corners(image):
    h, w = image.shape[:2]
    return np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)


def warp_layers(images, homographies, max_pixels=25_000_000):
    """联合角点计算画布；独立掩膜保留照片中的真实黑色像素。"""
    if len(images) != len(homographies) or not images:
        raise ValueError('图像与变换数量必须一致且非空。')
    transformed = []
    for image, H in zip(images, homographies):
        points = corners(image)
        z = np.c_[points.reshape(-1, 2), np.ones(4)] @ H[2, :]
        if np.min(np.abs(z)) < 1e-6 or (z.min() < 0 < z.max()):
            raise StitchingError('变换跨越投影无穷远线，拒绝分配画布。')
        transformed.append(cv2.perspectiveTransform(points, H))
    all_points = np.concatenate(transformed).reshape(-1, 2)
    if not np.isfinite(all_points).all():
        raise StitchingError('变换后的角点包含非有限值。')
    lower = np.floor(all_points.min(axis=0)).astype(np.int64)
    upper = np.ceil(all_points.max(axis=0)).astype(np.int64)
    width, height = (upper - lower).tolist()
    if width <= 0 or height <= 0 or width * height > max_pixels:
        raise StitchingError(f'画布尺寸异常: {width} x {height}。')
    T = np.array([[1, 0, -lower[0]], [0, 1, -lower[1]], [0, 0, 1]], dtype=np.float64)
    layers, masks = [], []
    for image, H in zip(images, homographies):
        layers.append(cv2.warpPerspective(image, T @ H, (width, height)))
        mask = np.full(image.shape[:2], 255, np.uint8)
        masks.append(cv2.warpPerspective(mask, T @ H, (width, height), flags=cv2.INTER_NEAREST) > 0)
    return layers, masks, T


def blend_layers(layers, masks, mode='feather'):
    if mode not in ('overwrite', 'feather'):
        raise ValueError('融合方式仅支持 overwrite 或 feather。')
    if mode == 'overwrite':
        result = np.zeros_like(layers[0])
        # 与参考代码一致：B 先绘制，A 最后覆盖。
        for layer, mask in reversed(list(zip(layers, masks))):
            result[mask] = layer[mask]
        return result
    numerator = np.zeros(layers[0].shape, np.float32)
    denominator = np.zeros(layers[0].shape[:2], np.float32)
    for layer, mask in zip(layers, masks):
        # 外围补零，使满幅掩膜也有可解释的边缘距离。
        distance = cv2.distanceTransform(np.pad(mask.astype(np.uint8), 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
        weight = (distance + 1e-3) * mask
        numerator += layer.astype(np.float32) * weight[..., None]
        denominator += weight
    return np.clip(numerator / np.maximum(denominator[..., None], 1e-6), 0, 255).astype(np.uint8)


def stitch_pair(a, b, ratio=0.7, ransac_threshold=5.0, features=None):
    start = time.perf_counter()
    fit = estimate_homography(a, b, ratio, ransac_threshold, features)
    layers, masks, T = warp_layers([a, b], [np.eye(3), fit['H']])
    overlap = masks[0] & masks[1]
    if int(overlap.sum()) < 100:
        raise StitchingError('有效重叠区域过小。')
    feather = blend_layers(layers, masks, 'feather')
    overwrite = blend_layers(layers, masks, 'overwrite')
    fit['metrics'].update(canvas_width=feather.shape[1], canvas_height=feather.shape[0],
                          overlap_pixels=int(overlap.sum()),
                          overlap_mae=float(np.abs(layers[0][overlap].astype(float)-layers[1][overlap]).mean()),
                          elapsed_seconds=time.perf_counter()-start)
    return dict(**fit, layers=layers, masks=masks, T=T, feather=feather, overwrite=overwrite)


def draw_matches(a, b, fit, max_matches=80, inliers_only=True):
    selected = [m for i, m in enumerate(fit['matches']) if not inliers_only or fit['mask'][i]]
    selected = sorted(selected, key=lambda m: m.distance)[:max_matches]
    return cv2.drawMatches(a, fit['features_a'].keypoints, b, fit['features_b'].keypoints,
                           selected, None, matchColor=(60, 220, 60),
                           flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
