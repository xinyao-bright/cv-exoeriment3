# 实验三：图像拼接

基于参考代码实现 **SIFT → FLANN → Lowe 比率筛选 → RANSAC 单应矩阵 → 透视变换 → 图像融合**，提供已在 **Conda 环境**中完整执行的 Jupyter Notebook 和详细 Markdown 实验报告。

## 直接查看

- **[实验 Notebook（ipynb，含全部代码和运行输出）](notebooks/image_stitching.ipynb)**：26 个单元格，其中 13 个代码单元格，包含核心算法、图片下载、完整实验、可选工具和测试，逐步展示原图、特征、匹配、画布与拼接结果。
- **[详细实验报告（Markdown）](report.md)**：实验目的、算法公式、代码设计、三场景结果、30 组参数对比、亮度实验、三图拼接、误差分析与思考题。
- [原图与来源](data/SOURCES.md)、[实测指标](results/metrics.csv)、[完整参数扫描](results/parameter_sweep.csv)。

![三图船坞拼接](results/boat_three_images.jpg)


## 文件结构

```text
requirements.txt                   实验核心依赖的固定版本
notebooks/image_stitching.ipynb    全部实验代码、工具、测试及运行输出
report.md                          详细 Markdown 报告
data/                              7 张网上获取的原始照片及来源
results/                           匹配图、拼接图、CSV 和 JSON
```

## 已验证结果

Notebook 最终在已有 Conda `cvex` 的 Python 3.10.21 中执行，使用 OpenCV 4.11.0、NumPy 2.2.6、Matplotlib 3.10.3。
实际执行时将依赖隔离到工作目录后由该 Conda Python 加载，以保留原环境中已有的 OpenCV 安装；上面的 Conda 命令可创建常规独立环境。

| 场景 | 候选匹配 | RANSAC 内点 | 内点率 | 内点 RMSE / 像素 |
| --- | ---: | ---: | ---: | ---: |
| 船坞 | 748 | 670 | 89.57% | 0.506 |
| 地图 | 626 | 599 | 95.69% | 1.486 |
| 报纸 | 1270 | 1142 | 89.92% | 0.370 |

默认 Lowe 比率 0.70、RANSAC 阈值 5 像素，处理图像最长边不超过 1200 像素；三图船坞结果为 2277 × 968。
4 项行为测试通过。完整环境信息见 [environment.json](results/environment.json)。
