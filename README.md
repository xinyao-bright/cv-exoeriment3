# 实验三：图像拼接

基于参考代码实现 **SIFT → FLANN → Lowe 比率筛选 → RANSAC 单应矩阵 → 透视变换 → 图像融合**，提供已在 **Conda 环境**中完整执行的 Jupyter Notebook 和详细 Markdown 实验报告。

## 直接查看

- **[实验 Notebook（ipynb，含全部代码和运行输出）](notebooks/image_stitching.ipynb)**：26 个单元格，其中 13 个代码单元格，包含核心算法、图片下载、完整实验、可选工具和测试，逐步展示原图、特征、匹配、画布与拼接结果。
- **[详细实验报告（Markdown）](report.md)**：实验目的、算法公式、代码设计、三场景结果、30 组参数对比、亮度实验、三图拼接、误差分析与思考题。
- [原图与来源](data/SOURCES.md)、[实测指标](results/metrics.csv)、[完整参数扫描](results/parameter_sweep.csv)。

![三图船坞拼接](results/boat_three_images.jpg)

## Conda 运行方法

推荐使用 Anaconda Prompt 或 Miniconda Prompt，在仓库目录执行：

```bash
git clone https://github.com/xinyao-bright/cv-exoeriment3.git
cd cv-exoeriment3
conda create -n cv-stitching python=3.10 pip -y
conda activate cv-stitching
python -m pip install -r requirements.txt
python -m pip install "notebook>=7,<8"
python -m ipykernel install --user --name cv-stitching --display-name "Python (cv-stitching)"
jupyter notebook notebooks/image_stitching.ipynb
```

在 Notebook 中选择 **Python (cv-stitching)** 内核，使用 **Restart Kernel and Run All Cells** 从头执行。
Notebook 第一段会检查当前 Python 是否来自 Conda 环境。

若已有 Conda 环境（例如 `cvex`），也可以：

```bash
conda activate cvex
python -m pip install -r requirements.txt
python -m pip install "notebook>=7,<8"
python -m ipykernel install --user --name cvex --display-name "Python (cvex)"
jupyter notebook notebooks/image_stitching.ipynb
```

此时在界面选择 **Python (cvex)**。上面的 pip 命令会安装指定版本到当前激活环境；希望隔离依赖时，使用前面的新建环境方法。

### 在 Notebook 中运行其他功能

所有 Python 代码均已合并到同一个 ipynb，无需额外的 `.py` 文件。按顺序运行全部单元格即可完成实验及四项测试。需要单独使用工具时，在 Notebook 中调用：

```python
download_images()  # 第 1 节：校验或恢复原图
summary, sweep, triple = run_experiments(ROOT)  # 第 6 节：重建全部结果
result = stitch_files('data/boat1.jpg', 'data/boat2.jpg', output='results/custom.jpg')
```

最后一节还提供可选的重新执行工具：

```python
await execute_notebook()
```

该工具使用当前 Conda Python 创建临时内核，从头运行并保存同一个 Notebook，不会在“运行全部”时自动调用。日常使用直接选择 **Restart Kernel and Run All Cells** 即可。

本项目使用 `opencv-python-headless`，通过 Notebook 内嵌图片展示结果，不需要 `cv2.imshow`。
不要在同一环境同时安装多个 OpenCV wheel（如 `opencv-python` 和 `opencv-python-headless`）。

## 文件结构

```text
requirements.txt                   实验核心依赖的固定版本
notebooks/image_stitching.ipynb     全部实验代码、工具、测试及运行输出
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

这些是所附输入上的实测结果，内点 RMSE 是拟合内点上的残差，不等于全景图的独立测试精度；渐变融合也不能消除视差、运动或所有曝光差异。

## 数据说明

照片来自 [OpenCV 官方拼接测试目录](https://github.com/opencv/opencv_extra/tree/d244584fd02b509f63db08db89b2d38c97ce990d/testdata/stitching)，固定上游提交并记录 SHA256。图片已随仓库提供，可离线运行。
`budapest` 文件是地图照片。来源、文件说明和权利信息见 [SOURCES.md](data/SOURCES.md)。
参考 PDF 用于确定实验流程，仓库没有附带该课程 PDF。
