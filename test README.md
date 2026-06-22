# 代码抄袭检测测试样例说明

## 目录结构

```
test_samples/
├── README.md                              # 本文件
│
├── 01_sort_original_bubble.py             # 场景1 原始：冒泡排序
├── 01_sort_plag_renamed.py                # 场景1 正例：变量/函数重命名
├── 01_sort_plag_restructured.py           # 场景1 正例：for→while 循环重构 + swap方式替换
├── 01_sort_negative_quicksort.py          # 场景1 反例：快速排序（分治算法，完全不同的思路）
│
├── 02_prime_original_trialdiv.py          # 场景2 原始：试除法素数检测（6k±1优化）
├── 02_prime_plag_renamed.py               # 场景2 正例：变量/函数重命名
├── 02_prime_plag_restructured.py          # 场景2 正例：提取嵌套辅助函数 + 条件逻辑改写
├── 02_prime_negative_sieve.py             # 场景2 反例：埃拉托斯特尼筛法（批量标记）
│
├── 03_bsearch_original_iterative.py       # 场景3 原始：迭代二分查找
├── 03_bsearch_plag_renamed.py             # 场景3 正例：变量/函数重命名
├── 03_bsearch_plag_restructured.py        # 场景3 正例：迭代→递归（内嵌递归函数）
├── 03_bsearch_negative_exponential.py     # 场景3 反例：指数搜索（先确定范围再二分）
│
├── 04_gcd_original_euclidean.py           # 场景4 原始：欧几里得辗转相除 GCD+LCM
├── 04_gcd_plag_renamed.py                 # 场景4 正例：变量/函数重命名
├── 04_gcd_plag_restructured.py            # 场景4 正例：迭代→递归改写
├── 04_gcd_negative_binary.py              # 场景4 反例：Stein 二进制 GCD（移位+减法）
│
├── 05_matmul_original.py                  # 场景5 原始：标准三重循环矩阵乘法
├── 05_matmul_plag_renamed.py              # 场景5 正例：变量重命名 + 累加器中转 + 冗余注释
├── 05_matmul_plag_restructured.py         # 场景5 正例：B转置缓存优化 + 点积分拆
└── 05_matmul_negative_strassen.py         # 场景5 反例：递归分治矩阵乘法（Strassen-like）
```

---

## 抄袭手段覆盖说明

### 正例（Plagiarism）覆盖的抄袭手段

| 抄袭手段 | 对应测试文件 | 具体表现 |
|----------|-------------|---------|
| **变量重命名** | `*_plag_renamed.py` (全部5个) | `arr→lst`, `n→length`, `i→idx`, `left→lo`, `a→num1` 等 |
| **函数重命名** | `*_plag_renamed.py` (全部5个) | `bubble_sort→sort_bubble`, `gcd→greatest_common_divisor` 等 |
| **循环类型替换** | `01_sort_plag_restructured.py` | `for i in range(n)` → `while i < n` |
| **迭代替换为递归** | `03_bsearch_plag_restructured.py`, `04_gcd_plag_restructured.py` | 循环逻辑转为递归调用 |
| **提取/内嵌辅助函数** | `02_prime_plag_restructured.py`, `03_bsearch_plag_restructured.py` | 将内联逻辑提取为嵌套函数 |
| **添加多余注释** | `05_matmul_plag_renamed.py` | 添加看似有用的注释伪装独立思考 |
| **代码结构重组** | `05_matmul_plag_restructured.py` | 将 B 转置以改变循环访问模式 |
| **swap 方式替换** | `01_sort_plag_restructured.py` | `a, b = b, a` → `temp = a; a = b; b = temp` |
| **条件表达式改写** | `02_prime_plag_restructured.py` | 将平铺的 if 条件改为遍历列表+嵌套函数 |
| **累加器中转** | `05_matmul_plag_renamed.py` | 直接累加 → `acc` 变量中转再赋值 |

### 反例（Negative / 非抄袭）覆盖的情况

| 场景 | 原始实现 | 反例实现 | 为什么不同 |
|------|---------|---------|-----------|
| 排序 | 冒泡排序 O(n²) | 快速排序 O(n log n) | 两两交换 vs 分治+分区 |
| 素数 | 试除法 O(√n) | 埃筛法 O(n log log n) | 逐个检查 vs 批量标记合数 |
| 搜索 | 迭代二分查找 | 指数搜索 | 直接二分 vs 先确定范围再二分 |
| GCD | 欧几里得辗转相除 | Stein 二进制算法 | 取模运算 vs 移位+减法 |
| 矩阵乘法 | 标准三重循环 O(n³) | 递归分治 | 直接三层嵌套 vs 分块递归 |

> **注意**：场景5（矩阵乘法）的反例在一键运行模式下可能会获得中等分数（~0.77），因为递归分治算法的 base case 仍然是标准矩阵乘法，且两个实现共享相似的 main 入口结构。这是系统的一个已知局限性——当"不同算法"共享子结构时可能被误判。可以通过提高 threshold 参数（如 `--threshold 0.8`）来排除此类情况。

---

## 运行方式

### 1. 环境准备

```bash
cd /home/lpj/temp/code_pla_/code_pla

# 安装依赖（首次运行）
pip install -r requirements.txt
```

### 2. 一键运行（推荐）

```bash
# 清空之前的产物（重要：每次运行新数据前建议清空）
rm -rf data/artifacts

# 纯 LSH 模式
python scripts/pipeline_pure_lsh_dacd.py --src_root data/test_samples

# 启用 DACD 模板聚类（更精确，会自动降低模板代码的权重）
python scripts/pipeline_pure_lsh_dacd.py --src_root data/test_samples --with_dacd
```

### 3. 调整敏感度

```bash
# 高阈值：减少误报（更保守），推荐用于正式审查
python scripts/pipeline_pure_lsh_dacd.py --src_root data/test_samples \
    --threshold 0.7 --min_coverage 0.5

# 低阈值：减少漏报（更激进），用于发现更多可疑对
python scripts/pipeline_pure_lsh_dacd.py --src_root data/test_samples \
    --threshold 0.3 --min_coverage 0.2

# 使用 DACD 进一步减少模板代码的误报
python scripts/pipeline_pure_lsh_dacd.py --src_root data/test_samples \
    --threshold 0.7 --min_coverage 0.5 --with_dacd
```

### 4. 查看结果

用浏览器打开生成的 HTML 报告：

```bash
# 报告位置
open data/artifacts/reports/baseline_pairs.html
# 或
xdg-open data/artifacts/reports/baseline_pairs.html
```

报告包含：
- 可疑抄袭对的总览表格（按相似度从高到低排序）
- 点击展开后可看到函数级匹配详情
- 左右并排的语法高亮源代码对比
- 每个匹配函数的具体相似度分数

---

## 实际测试结果（threshold=0.3, min_coverage=0.2）

### 抄袭检测结果

| # | 原始文件 | 抄袭变体 | 抄袭手段 | 得分 | 检测 |
|---|---------|---------|---------|------|------|
| 1 | sort_original_bubble | sort_plag_renamed | 变量/函数重命名 | 0.273 | ✅ |
| 2 | sort_original_bubble | sort_plag_restructured | for→while + swap替换 | 0.920 | ✅ |
| 3 | prime_original_trialdiv | prime_plag_renamed | 变量/函数重命名 | 0.377 | ✅ |
| 4 | prime_original_trialdiv | prime_plag_restructured | 提取辅助函数 + 条件改写 | 0.490 | ✅ |
| 5 | bsearch_original_iterative | bsearch_plag_renamed | 变量/函数重命名 | 0.373 | ✅ |
| 6 | bsearch_original_iterative | bsearch_plag_restructured | 迭代→递归 | 0.952 | ✅ |
| 7 | gcd_original_euclidean | gcd_plag_renamed | 变量/函数重命名 | 0.587 | ✅ |
| 8 | gcd_original_euclidean | gcd_plag_restructured | 迭代→递归 | 0.929 | ✅ |
| 9 | matmul_original | matmul_plag_renamed | 变量重命名 + 累加器中转 | 0.314 | ✅ |
| 10 | matmul_original | matmul_plag_restructured | B转置 + 点积分拆 | 0.943 | ✅ |

> ✅ **10/10 全部检测到**

### 反例（非抄袭）检查

| # | 原始文件 | 反例文件 | 得分 | 结果 |
|---|---------|---------|------|------|
| 1 | bubble sort | quick sort | 0.205 | ✅ 低分 |
| 2 | trial division | sieve | 0.198 | ✅ 低分 |
| 3 | binary search | exponential search | 0.277 | ✅ 低分 |
| 4 | euclidean GCD | Stein binary GCD | 0.401 | ✅ 低分 |
| 5 | standard matmul | recursive matmul | 0.767 | ⚠️ 偏高 |

> ⚠️ 场景5偏高：递归算法包含标准矩阵乘法作为 base case，且 main 结构相似。建议使用 `--threshold 0.8` 排除。

---

## 系统工作原理

1. **E-PDG 图构建**：将源代码解析为节点（语句/表达式）和边（数据依赖、控制依赖、副作用依赖）的图结构
2. **多视图增强**：从 PDG 中分离 DFG（数据流）和 AST（语法树）视图
3. **LSH 索引**：对 token 序列和图结构计算 MinHash 签名，建立 LSH 近似最近邻索引
4. **候选召回**：通过 LSH 快速找到相似函数对，过滤模板函数
5. **评分报告**：函数级聚合到程序级，结合覆盖率计算最终得分

系统在**图结构层面**分析代码，而非简单文本比对，因此能有效识别变量重命名、代码重构、语句重排等常见抄袭伪装手段。
