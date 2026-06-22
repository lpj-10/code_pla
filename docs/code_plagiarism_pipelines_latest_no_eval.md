# Code Plagiarism Pipelines (pure LSH, no VCoME / no eval)

本文件说明当前 `code_plagiarism` 项目在 **完全删除 VCoME 相关代码之后** 的最新运行流程。
现在的系统是一个 **“多视图 E-PDG + LSH 召回 +（可选）DACD 模板簇 + HTML 报告”** 的纯查重流水线，不再依赖
PyTorch、VCoME 模型、opcode 词表或任何 GNN 精排脚本；聚类只在可选的 DACD 模板识别阶段使用，不开启 DACD 时仍然是纯 LSH 主线。

---

## 一、目标与整体思路

目标：给一批源代码文件做查重，得到：

1. **程序对之间的查重分数**（接近 1 表示高度相似）
2. **函数级别的覆盖率信息**（A 的多少行被 B 覆盖，反之亦然）
3. **HTML 报告**，可视化高相似度的程序对和对应的函数匹配情况

整体流程分为四层：

1. **图构建层**：把源代码编译成 **效果增强的程序依赖图（E-PDG）**，并进一步构建 AST / DFG / PDG 等多视图。
2. **索引与召回层（LSH）**：对图特征做 MinHash / WL-hash 等摘要，构建 LSH 索引；快速召回候选函数对。
3. **程序级查重层（LSH + 覆盖率）**：在 LSH 的基础上，按程序聚合函数对，计算覆盖率和基于 LSH 的查重分数。
4. **HTML 报告层**：输出 `baseline_pairs.html`，展示程序对之间的查重情况。

当前版本 **不再包含**：

- VCoME 多视图编码器
- opcode 词表构建
- 候选对精排与程序聚类（`rerank_candidates_multi.py`、`cluster_m4.py`、`render_clusters_report.py`）

---

## 二、项目目录结构（与查重流水线相关）

在仓库根目录 `code_plagiarism/` 下，和本流水线直接相关的目录大致如下：

- `scripts/`
  - `build_epdg.py`：从源代码构建 E-PDG JSON
  - `enrich_graph_views.py`：在 E-PDG 基础上补充 AST / DFG / 多视图信息
  - `build_index.py`：基于多视图 JSON 构建 LSH 索引
  - `build_lsh_candidates.py`：用 LSH 召回函数级候选对
  - `search_and_rank.py`：按程序对聚合并输出查重分数与 HTML 报告
- `data/`
  - `submissions/`：你要查重的源代码，会放在这里
  - `artifacts/`
    - `json/`：`build_epdg.py` 的输出（E-PDG JSON）
    - `json_mv/`：`enrich_graph_views.py` 的输出（多视图 JSON）
    - `index/`：`build_index.py` 产生的 LSH 索引
    - `retrieval/`：LSH 候选对与最终查重结果 JSON
    - `reports/`：HTML 报告（`baseline_pairs.html`）
- `effect_summaries.yaml`：副作用库，用于给 E-PDG 增强 IO / 网络 / 随机数等边信息

---

## 三、环境准备

### 3.1 创建 Conda 环境

在仓库根目录外部的终端中执行：

```bash
conda create -n codeplag2 python=3.11 -y
conda activate codeplag2
```

### 3.2 安装依赖

在 `code_plagiarism/` 根目录下执行：

```bash
pip install -r requirements.txt
```

当前 `requirements.txt` 只包含：

- numpy / scipy / networkx：图与数值计算
- datasketch：MinHash / LSH
- scikit-learn + hdbscan：聚类（目前查重主线可不用 hdbscan，但保留不影响）
- tqdm / PyYAML / rich：进度条、配置、日志
- Jinja2 / Pygments：HTML 报告与代码高亮

**注意**：已经移除了 PyTorch、VCoME 相关依赖。

---

## 四、完整运行流水线（纯 LSH 版本）

下面假设你已经把要查重的源代码放在 `data/submissions/` 里。

### 4.1 第一步：构建 E-PDG JSON

把源代码编译成带有控制流、数据流、副作用信息的 E-PDG：

```bash
cd code_plagiarism

python scripts/build_epdg.py   -i data/submissions   -o data/artifacts/json   --effects effect_summaries.yaml
```

产物：

- `data/artifacts/json/*.epdg.json`

每个源文件会对应一个 E-PDG JSON，包含：

- 函数列表、基本块、指令序列
- 控制依赖 / 数据依赖
- 基于 `effect_summaries.yaml` 解析出的副作用信息（如 IO / 网络调用）

### 4.2 第二步：补充多视图图结构（AST / DFG / PDG）

在 E-PDG 的基础上构建多视图图结构（AST / DFG / PDG 等），统一写入 `json_mv`：

```bash
python scripts/enrich_graph_views.py   -j data/artifacts/json   -o data/artifacts/json_mv
```

产物：

- `data/artifacts/json_mv/*.epdg.json`

这些 JSON 会在原有 E-PDG 的基础上，增加：

- AST 视图：语法树结构
- DFG 视图：细粒度数据流边
- 其他辅助结构，方便后续做图摘要与 LSH

### 4.3 第三步：构建 LSH 索引

对多视图图的特征做摘要，构建 MinHash / WL-hash 索引：

```bash
python scripts/build_index.py   -j data/artifacts/json_mv   --out_index data/artifacts/index/epdg_lsh.pkl   --num_perm 128   --bands 32   --shingle_k 5   --graph_num_perm 128   --graph_bands 32   --wl_iters 2   --kpath_k 3   --kpath_per_node 32
```

说明：

- `--num_perm` / `--bands` / `--shingle_k`：控制 token 视图的 MinHash 参数
- `--graph_num_perm` / `--graph_bands`：控制图视图的 MinHash 参数
- `--wl_iters`：Weisfeiler-Lehman hash 的迭代次数
- `--kpath_k` / `--kpath_per_node`：图路径采样的相关参数

产物：

- `data/artifacts/index/epdg_lsh.pkl`
- 终端会打印索引中包含的文件数与函数数

### 4.4 第四步：LSH 召回函数候选对

在函数级别利用 LSH 索引做近邻搜索，写出候选函数对 JSON：

```bash
python scripts/build_lsh_candidates.py   -i data/artifacts/index/epdg_lsh.pkl   -j data/artifacts/json_mv   -o data/artifacts/retrieval/lsh_pairs.json   --topk_recall 128   --min_candidates 10   --min_tokens 8   --template_degree_soft 64   --template_degree_hard 128
```

重要参数解释：

- `--topk_recall`：每个查询函数至少召回这么多候选邻居，用于提高 Recall。
- `--min_candidates`：对非常孤立的函数，至少保留多少候选。
- `--min_tokens`：过滤掉极短的函数，避免无意义的模板 / 空壳函数污染。
- `--template_degree_soft` / `--template_degree_hard`：
  - 基于“某个函数在 LSH 图中的度数”识别模板函数；
  - 度数非常高的函数视为模板，在后续会被削弱权重或忽略。

产物：

- `data/artifacts/retrieval/lsh_pairs.json`

结构大致为：

```json
{
  "pairs": [
    {
      "lsh_sim": 0.98,
      "meta_i": {
        "json_path": "data/artifacts/json_mv/fileA.py.epdg.json",
        "func_idx": 0,
        "name": "foo",
        "first_lineno": 10
      },
      "meta_j": {
        "json_path": "data/artifacts/json_mv/fileB.py.epdg.json",
        "func_idx": 2,
        "name": "bar",
        "first_lineno": 5
      }
    },
    ...
  ]
}
```

### 4.5 第五步：程序级查重 + HTML 报告

最后一步是把函数级候选对聚合到程序级别，计算查重分数，并生成 HTML 报告。
当前纯 LSH 版本只使用 LSH 分数和覆盖率，不再依赖 VCoME 或重排脚本。

```bash
python scripts/search_and_rank.py   -i data/artifacts/index/epdg_lsh.pkl   -j data/artifacts/json_mv   -o data/artifacts/retrieval/baseline_pairs.json   -r data/artifacts/reports/baseline_pairs.html   --threshold 0.5   --min_coverage 0.3
```

关键参数：

- `--threshold`：程序对最终查重分数低于该阈值的会被过滤，不写入 HTML 报告。
  - 示例中 `0.5` 意味着只展示查重度 ≥ 0.5 的程序对。
- `--min_coverage`：要求在函数覆盖层面至少达到一定比例才认为“值得展示”。
  - 示例中 `0.3` 表示至少有 30% 覆盖度。

产物：

- `data/artifacts/retrieval/baseline_pairs.json`：机器可读的查重结果 JSON
- `data/artifacts/reports/baseline_pairs.html`：带可视化的查重报告

在终端里你会看到类似输出：

```text
[coverage] data/submissions/A.py vs data/submissions/B.py: base=0.987, cov_a=95.00%, cov_b=92.00%, combined=95.00% -> final=0.987
[OK] results -> data/artifacts/retrieval/baseline_pairs.json
[OK] report  -> data/artifacts/reports/baseline_pairs.html
```


### 4.6 第六步：DACD 模板簇 + 群体降权（可选）

在纯 LSH 主线的基础上，你现在可以选择性地接入 **DACD 模板簇 + 群体降权**，用来：

1. 识别“在很多文件中一模一样”的模板函数；
2. 在程序级打分时自动弱化这类模板的贡献；
3. 在 HTML 报告中对涉及模板的匹配加上标记，方便老师判断。

#### 4.6.1 运行 DACD 模板聚类

```bash
python -m clustering.hdbscan_cluster \
  --json-root data/artifacts/json_mv \
  --output data/artifacts/json_mv/dacd_clusters.json \
  --min-cluster-size 8 \
  --epsilon 0.35
```

说明：

- `--json-root`：指向前面多视图 JSON 目录 `data/artifacts/json_mv`；
- `--output`：聚类结果 JSON 路径，建议就放在 `json_root/dacd_clusters.json`；
- `--min-cluster-size`：最小簇大小，越大越“严格”才认为是模板；
- `--epsilon`：距离阈值 / 尺度，通常 `0.3~0.4` 是比较稳妥的起点。

脚本会输出若干 cluster，并对其中 `is_template_like == true` 的簇记录：

- 模板函数列表 `members`（函数级 `func_id`）；
- 簇大小、出现在多少不同文件、稳定度等信息。

#### 4.6.2 在程序级打分中启用模板降权

`search_and_rank.py` 现在多了一个可选参数 `--dacd_clusters`；如果不显式传入，它会默认尝试读取 `<json_root>/dacd_clusters.json`：

```bash
python scripts/search_and_rank.py \
  -i data/artifacts/index/epdg_lsh.pkl \
  -j data/artifacts/json_mv \
  -o data/artifacts/retrieval/baseline_pairs.json \
  -r data/artifacts/reports/baseline_pairs.html \
  --threshold 0.5 \
  --min_coverage 0.3 \
  --dacd_clusters data/artifacts/json_mv/dacd_clusters.json
```

当提供了 DACD 结果时，脚本会：

1. 为每个模板簇计算一个权重 `w ∈ (0.1, 0.8]`；
2. 把簇内函数的“语义长度”乘上这个 `w`（越常见的模板，`w` 越小）；
3. 在程序级覆盖率与最终分数聚合时，模板函数的贡献自然被弱化。

不开启 DACD（不传入 `--dacd_clusters`，也没有默认文件）时，行为与之前完全一致。

#### 4.6.3 HTML 报告中的模板标记

当 `json_root` 下存在 `dacd_clusters.json` 时，HTML 报告会自动读取其中的模板信息：

- 在函数匹配表中新增一列 **Template**；
- 对于涉及模板函数的匹配，用浅黄色的小标签标记为：

  - `A+B template`：两边函数都在模板簇中；
  - `A template`：只有左边函数在模板簇中；
  - `B template`：只有右边函数在模板簇中。

这样老师在查看高分 pair 时，可以快速分辨：

- 哪些高分主要来自公共模板；
- 哪些高分来自真正可疑的学生自写逻辑。


---

## 五、如何理解查重分数

`search_and_rank.py` 的核心逻辑可以概括为：

1. **函数级别**：基于 LSH 相似度和模板过滤，得到一批高相似度的函数对。
2. **程序级别覆盖率**：
   - 对于程序 A 与程序 B：
     - 统计 A 中有多少函数在 B 中找到了高相似度匹配；
     - 统计 B 中有多少函数在 A 中找到了高相似度匹配；
     - 得到 `cov_a`、`cov_b` 两个覆盖率百分比。
3. **基础相似度 `base_score`**：
   - 一般由 LSH 的函数对高分情况聚合而来，可理解为“语义相似度的上限”。
4. **最终查重分 `final`**：
   - 大致形如：`final = base_score`（或在某些实现中乘以覆盖率因子）。
   - 在当前版本中，你在终端看到的 `final` 数值和 HTML 里的分数是一致的。

期望行为举例：

- **A 与 B 实现相同功能，只是写法不同**：
  - 许多函数在 LSH 上能互相匹配；
  - 覆盖率 `cov_a` / `cov_b` 都接近 100%；
  - `final` 接近 1，HTML 报告中的相似度很高。

- **A 与 C 功能完全不同，只共享少量工具函数**：
  - 只有少数短函数或模板有匹配；
  - 覆盖率很低（例如 < 0.3）；
  - 即使个别函数 LSH 相似度高，程序级查重分也会被压低甚至被过滤。

---

## 六、未来可以扩展的方向（不在当前流水线中）

下面这些内容目前 **不在纯 LSH 流水线中实现**，只是为后续扩展预留方向：

1. **引入图神经网络或 VCoME 类似的多视图编码器**：
   - 在 LSH 候选对基础上做精排；
   - 利用 AST / DFG / PDG 的结构信息提升语义对齐能力。
2. **程序级聚类与相似簇报告**：
   - 在程序级 embedding 和 pair 相似度基础上，对程序做 HDBSCAN / 图聚类；
   - 输出“相似程序簇”的报告，方便老师批量查看异常群体。
3. **更细粒度的可视化**：
   - 在 HTML 中高亮对齐的 IR 块、E-PDG 子图，而不仅仅是函数列表。

除了上面已经实现的 DACD 模板簇 + 群体降权之外，本节列出的其余扩展
（基于 GNN 的精排、真正的程序级聚类、IR / E-PDG 级可视化）仍然可以在未来版本中
逐步引入新的脚本与文档说明；即便完全不启用 DACD，你也可以继续使用
**纯 LSH 流程** 完成查重任务。

---

以上就是当前 `code_plagiarism` 在“移除 VCoME 相关代码之后”的完整、重新编号的
纯 LSH 查重流水线说明。你可以直接按照第四节的 5～6 个步骤（其中第 6 步为可选的
DACD 模板簇 + 群体降权），从源代码一路跑到 `baseline_pairs.html`，进行查重分析。
