---

## 项目名称：供应链知识图谱 — Stage 1: 依赖骨架 (Dependency Backbone)

---

### 项目目标

构建一个以**公开信息**为边界、以**公司间商业依赖和大宗商品物理构成**为骨架的知识图谱，使其成为支撑多种供应链分析问题的统一数据底座。

**核心理念**：图本身不预设分析类型。实体和关系只描述"事实"，解读由查询层负责。Stage 1 聚焦依赖关系骨架，事件冲击、替代分析、地理匹配等由下游独立项目承接。

Stage 1 验证的分析范式：
- **依赖拓扑分析**：结构性的集中度风险、关键节点识别
- **商业依赖链追踪**：沿 `[:供应给]` 和 `[:提供]` 的多跳商业依赖
- **物理构成链追踪**：沿 `[:用于]` 的物料到产品的物理消耗关系
- **共同依赖暴露**：多家公司依赖同原料/中间品
- **自定义探索式查询**：用户可按任意实体和关系组合进行图探索

### 项目边界

Stage 1 是**数据底座**，不包含分析应用层。以下能力由独立项目负责：

| 能力 | 所属项目 | 与本项目的交接面 |
|------|---------|----------------|
| 事件冲击与影响传播 | Event 项目 | Event 节点 + `[:影响]` 边接入本图，本图提供带时间属性的依赖边供遍历 |
| 替代品与产品等价类 | Process (工序) 项目 | Product Category 节点 + `[:替代品]`/`[:归类于]` 边接入本图，本图提供 Product 节点 |
| 分析师可视化界面 | Demo 项目 | 消费本图的 Cypher 查询和 Neo4j 实例 |

**本项目不导入 Event 节点、`[:影响]` 边、Product Category 节点、替代关系边。** 但通过边缘预留时间属性 (`valid_from`/`valid_until`)、Company 预留 `hq_country`/`operating_countries`、Product 预留 `category` 属性，为下游项目提供零迁移扩展点。

**明确排除项**：
- **农户/种植者 (Growers/Farmers)** 不作为 Company 节点建模。作物商品 (Commodity) 节点作为供应链的聚合起点。未来若需要在特定供应链段引入农户节点，按需追加。

---

### 预期产出

1. **知识图谱数据模型**：实体定义、关系定义、属性规范文档（本文件）。
 2. **主干图谱实例**：覆盖肥料→食品链条的 Neo4j 数据库实例 (~60 边, 28 节点)，包含：
   - 化肥公司及化肥产品节点
   - 中间农产品及加工品节点（玉米、大豆、小麦、淀粉、HFCS、动物饲料、乙醇等）
   - 下游消费品公司节点
   - `[:提供]`（公司→产品）、`[:供应给]`（供给方→需求方）、`[:用于]`（物料→产品）边
3. **验证查询集**：5 条标准 Cypher 查询，验证模型多功能可查询性：
   - 商业依赖链追踪
   - 物理构成链追踪
   - 共同依赖暴露
   - 同产品替代供应
   - 图结构关键节点分析
   所有查询均内置置信度过滤、最大深度限制、节点不重复约束。
4. **数据接入指南**：公开数据源（USDA、FAO、SEC 10-K 等）如何映射到图谱结构的说明。

---

### 术语表 (Glossary)

**实体类型**

| 术语 | 定义 | 典型实例 | 关键属性 |
|------|------|----------|----------|
| **公司/组织** (Company) | 供应链上的商业实体，包括生产商、服务商、下游客户等。 | Nutrien、雀巢、泰森食品 | `hq_country`(必填)、`hq_region`(可选)、`operating_countries`(可选)、`external_id`(可选，如ticker/LEI) |
| **产品/服务** (Product) | 由公司提供的、可被下游采购或依赖的产出物，包括有形产品、软件、基础服务、加工中间品等。 | DAP化肥、动物饲料、碳酸饮料、玉米淀粉 | `external_id`(可选)、`category`(可选，预留未来产品类别映射) |
| **大宗商品/物料** (Commodity) | 作为基础工业原料或原材料交易的同质化产品，是产品的子类，用标签 `:Commodity` 区分。 | 钾肥、尿素、玉米、大豆 | `major_producing_countries`(可选) |

**Commodity 与 Product 的分类规则**：一个节点归类为 Commodity 须同时满足 (a) 同质化/可替代，(b) 在公开交易所或价格指数上有报价，(c) 无强品牌属性。不满足任意一条则为 Product。**每个节点只取一个标签**（最具体的那个），不重复加注。此规则为数据录入提供可重复的判定标准。

**关系类型**

| 关系名 | 方向 / 语义 | 已确认的用法与约束 |
|--------|-------------|-------------------|
| `[:提供]` | `(公司) -[:提供]-> (产品)` | 说明公司产出该产品。一对多，允许多家公司提供同一产品。边上可选属性：毛利率、收入占比等。**禁止自环**（公司不"提供"给自己）。 |
| `[:供应给]` | 供给方 → 需求方 | **仅用于商业供应依赖。** 硬约束：物料节点作为物理输入时使用 `[:用于]`，不得用 `[:供应给]` 表达物理构成关系。支持所有端点组合（Product→Product、Product→Company、Company→Company、Commodity→Company）。边上必含 `confidence` 三级刻度，可选 `valid_from`/`valid_until`。**禁止自环**。 |
| `[:用于]` | `(输入物料) -[:用于]-> (产品)` | 表示物理构成或主要消耗关系。输入物料不限于 Commodity 标签 — 任何节点只要在语义上是物理输入角色（如 Corn Starch 作为 Processed Food 的配料），即可作为 `[:用于]` 的源。**与 `[:供应给]` 严格分离。** 可选 `valid_from`/`valid_until`。`[:用于]` 不含 `confidence` 属性（物理构成关系在 Stage 1 范围内均为确定性关系）。**禁止自环**。

---

### 数据来源规则

- **来源优先级**：监管文件 (SEC 10-K, 年报) > 新闻报道 > 行业估算。冲突时取更高优先级来源。
- **`source` 属性**：所有边应标注数据来源。格式：`<来源类型>:<简短引用>`，如 `SEC:Corn%20Products%20segment`、`news:Bloomberg%202024`。
- **数据获取瓶颈**：将公开财报中的市场份额/业务分部描述转化为图边存在人工判断环节。初期不追求精确量化（如"供应了 X% 的玉米"），仅记录"是否存在供应关系"。

### 关系属性详表

| 属性 | 所属关系 | 类型 | 必填 | 说明 |
|------|---------|------|------|------|
| `confidence` | `[:供应给]` | 枚举 | 是 | `confirmed` / `inferred` / `associated`（见 ADR-003） |
| `valid_from` | `[:供应给]`, `[:用于]` | 日期 | 否 | 关系生效时间。留空视为"一直有效" |
| `valid_until` | `[:供应给]`, `[:用于]` | 日期 | 否 | 关系失效时间。留空视为"一直有效" |
| `gross_margin_pct` | `[:提供]` | 浮点数 | 否 | 该产品对公司的毛利率 |
| `revenue_share_pct` | `[:提供]` | 浮点数 | 否 | 该产品收入占公司总收入比例 |
| `source` | 所有边 | 字符串 | 否 | 数据来源标注 |

---

### 关键架构决策记录 (ADR)

**ADR-001: 成本/收入建模方式** [已确认]

- **决策**：成本和收入不作为独立实体节点，而作为关系属性挂在对应边上。优先挂在 `[:提供]` 边。
- **理由**：核心目标是建立可查询的依赖网络，非精确财务聚合。
- **后果**：路径查询可快速跑通，但无法直接做复杂财务归因。未来可增设 `FinancialImpactEvent` 节点。

**ADR-002: 供应关系建模粒度** [已确认]

- **决策**：采用直接边连接，不引入"供应合同/关系"中间节点。`[:供应给]` 方向固定为"供给方 → 需求方"，严格与 `[:用于]` 分离。
- **理由**：公开信息无法支撑条款级数据；直接连接查询路径最短。预留 `relationship_id` 属性供未来迁移。
- **后果**：无法表达同产品对不同客户的价格差异，符合当前数据约束。

**ADR-003: 置信度三级刻度** [已确认]

- **决策**：`[:供应给]` 关系的 `confidence` 分三级：
  - `confirmed`：L1 刚性依赖（物理/化学硬依赖、独家公告）。仅适用于 Product-Product 或 Product-Company 边。
  - `inferred`：L2 推断依赖（营收/业务结构推断）。适用于 Product-Product、Product-Company、**Commodity-Company** 边。Commodity→Company 统一归入此级（如 Corn→ADM 的关系在公开财报中有明确的业务分部依据）。
     - `associated`：L3 公司间依赖（仅知存在交易）。Company-Company 边默认归入此级。
   - **例外**：当公司间关系在公开监管文件中有明确依据（如 Nutrien 10-K 明确记载与 Cargill 的分销关系），可上调至 `inferred`。
- **查询约定**：默认只走 `confirmed` + `inferred`，`associated` 需显式指定。通过 `$confidence_levels` 参数实现：
  ```cypher
  WHERE ALL(rel IN relationships(path) WHERE rel.confidence IN $confidence_levels)
  ```

**ADR-004: 时间建模策略** [已确认]

- **决策**：`[:供应给]` 和 `[:用于]` 边增加可选 `valid_from` 和 `valid_until`。查询时以目标时间点与边的有效期做交叉判断。未填有效期的边视为一直有效。
- **理由**：供应链关系有时效性，不加时间维度将导致下游项目进行历史分析时错误关联过期关系。
- **后果**：初期大量留空不影响查询（留空边始终通过过滤）。Stage 1 暂不实现时间过滤查询——时间属性作为数据就绪，过滤逻辑由 Event 项目定义。

**ADR-005: 事件冲击建模** [推迟至 Event 项目]

- **决策**：Event 节点及其所有关联属性（`event_type`, `severity`, `scope_geo`, `scope_industry` 等）和 `[:影响]` 边不在 Stage 1 范围内。由独立的 Event 项目定义完整的 Event 模型、地理匹配规则、严重度判定标准，并接入本图的依赖网络。
- **理由**：Event 建模涉及冲击强度判定、地理匹配语义、事件影响时效等多项独立设计决策，过早并入 Stage 1 会造成模型污染。本图为 Event 项目预留 Company 的 `hq_country`/`operating_countries`、Commodity 的 `major_producing_countries`、所有关系边的 `valid_from`/`valid_until`。
- **后果**：Stage 1 不包含冲击传导类查询。地理属性已建模但无主动消费者。

**ADR-006: 实体地理位置属性** [已确认]

- **决策**：Company 节点增加 `hq_country`（必填）、`hq_region`（可选）、`operating_countries`（可选）。Commodity 节点增加 `major_producing_countries`（可选）。不建模精确产地节点。
- **地理匹配规则**：推迟至 Event 项目定义。Stage 1 仅加载地理数据，不产出地理过滤查询。
- **后果**：传导精度限制在"国家/区域"级。未来可增加产地子节点。

**ADR-007: 替代品与产品等价类** [推迟至 Process 项目]

- **决策**：替代关系（`[:替代品]`）、产品类别节点（Product Category）、`[:归类于]` 边不在 Stage 1 范围内。由独立的 Process (工序) 项目定义产品等价类和替代逻辑，并接入本图的 Product 节点。
- **理由**：替代品判定涉及功能等价性分析、工序匹配等独立建模问题。本图为 Process 项目预留 Product 的 `category` 属性。
- **后果**：Stage 1 的"替代供应"验证查询仅限于"哪些其他公司提供同一产品"（同产品替代供应），非真正意义上的功能替代。

---

### 验证查询集

5 条标准查询，每条一个独立 `.cypher` 文件：

| # | 查询类型 | Cypher 文件 | 验证目标 |
|---|---------|------------|---------|
| 1 | 商业依赖链追踪 | `01_dependency_chain.cypher` | 从化肥公司沿 `[:提供]→[:供应给]*` 追踪到消费品公司 |
| 2 | 物理构成链追踪 | `02_composition_chain.cypher` | 从大宗商品沿 `[:用于]*` 追踪加工链到最终产品 |
| 3 | 共同依赖暴露 | `03_common_dependency.cypher` | 找出依赖同一中间品或原料的多家公司 |
| 4 | 同产品替代供应 | `04_alternate_supplier.cypher` | 给定产品，找出所有提供该产品的公司（`[:提供]` 反向查询） |
| 5 | 图结构关键节点 | `05_hub_analysis.cypher` | 按出入度识别供应网络中的枢纽节点 |

**所有查询统一遵循以下约束**：

- 默认置信度 `$confidence_levels = ['confirmed', 'inferred']`
- 最大遍历深度默认 6，可通过 `$max_depth` 参数覆盖
- 单条路径内同一节点不重复访问（Cypher 默认 `isTrail` 或显式 `NODE_UNIQUENESS`）
- 不包含时间过滤逻辑（时间属性已加载，过滤由 Event 项目追加）

**每跳查询必须经过 Product/Commodity 节点切换关系类型**。标准路径签名：

| 查询类型 | 路径签名 | 约束 |
|---------|---------|------|
| 商业依赖链 | `(Company)-[:提供|供应给]->...->(Company)` | Mix of company→product (`[:提供]`) and commercial supply (`[:供应给]`). First hop from a fertilizer company may be company→company. |
| 物理构成链 | `(Commodity)-[:用于]->(Product)-[:用于]->(Product)...` | 源可以是 Commodity 或 Product（任何输入物料角色） |
| 混合遍历 | `(Company)-[:提供]->(Product)-[:用于]->...->(Product)-[:提供]->(Company)` | 每次关系切换时经过实体节点 |
| 共同依赖 | `(c1)-[*..]->(m)<-[*..]-(c2)` | 不约束关系方向，检测拓扑共同依赖 |
| 替代供应 | `(p)<-[:提供]-(c)` | 仅本体图中存在的 `[:提供]` 边 |

**数据录入校验规则**：

- `[:用于]` 和 `[:供应给]` 按语义严格分离：物理构成用 `[:用于]`，商业供应用 `[:供应给]`。同节点对可同时存在两种边（如 Corn→Ethanol `[:用于]` 物理构成 + Corn→ADM `[:供应给]` 商业销售），语义不同时不视为冲突。
- 构建 L1/L2 产品-产品边时，下游产品必须已通过 `[:提供]` 连接到某公司。
- 禁止任何自环边（source == target）。
- 所有 `[:供应给]` 边必填 `confidence`。

### 实体清单 (Stage 1 实例)

**公司 (9)**

| ID | 名称 | 国家 |
|----|------|------|
| c01 | Nutrien | CA |
| c02 | Yara International | NO |
| c03 | Mosaic | US |
| c04 | ADM | US |
| c05 | Bunge | US |
| c06 | Cargill | US |
| c07 | Tyson Foods | US |
| c08 | Nestlé | CH |
| c09 | The Coca-Cola Company | US |

**大宗商品 (6)**

| ID | 名称 | 主产国 |
|----|------|--------|
| m01 | Potash | CA, RU, BY |
| m02 | Urea | CN, IN, US |
| m03 | DAP | CN, IN, US |
| m04 | Corn | US, CN, BR |
| m05 | Soybeans | US, BR, AR |
| m06 | Wheat | CN, IN, RU |

**产品 (13)**

| ID | 名称 | 类别 |
|----|------|------|
| p01 | NPK Compound Fertilizer | fertilizer |
| p02 | Corn Starch | food-ingredient |
| p03 | High Fructose Corn Syrup (HFCS) | sweetener |
| p04 | Soybean Meal | animal-feed |
| p05 | Soybean Oil | food-oil |
| p06 | Wheat Flour | food-ingredient |
| p07 | Animal Feed | animal-feed |
| p08 | Ethanol | fuel |
| p09 | Poultry Products | meat |
| p10 | Pork Products | meat |
| p11 | Processed Food | packaged-food |
| p12 | Carbonated Soft Drinks | beverage |
| p13 | Snack Foods | packaged-food |

**总计：28 节点，60 边 (23 [:提供] + 22 [:用于] + 15 [:供应给])**

### 关系清单 (Stage 1 实例)

**[:提供] (23 边)**

| 公司 | 产品 |
|------|------|
| Nutrien | Potash, Urea, DAP |
| Yara | Urea, NPK Compound Fertilizer |
| Mosaic | Potash, DAP |
| ADM | Corn Starch, HFCS, Soybean Meal, Soybean Oil, Ethanol, Animal Feed |
| Bunge | Soybean Meal, Soybean Oil |
| Cargill | Corn Starch, Animal Feed, Soybean Meal |
| Tyson | Poultry Products, Pork Products |
| Nestlé | Processed Food, Snack Foods |
| Coca-Cola | Carbonated Soft Drinks |

**[:用于] (22 边)**

| 输入物料 | 产品 |
|----------|------|
| Potash | Corn, Soybeans |
| Urea | Corn, Wheat |
| DAP | Corn, Soybeans |
| Corn | Corn Starch, HFCS, Ethanol, Animal Feed |
| Soybeans | Soybean Meal, Soybean Oil, Animal Feed |
| Wheat | Wheat Flour, Animal Feed |
| Corn Starch | Processed Food, Snack Foods |
| HFCS | Carbonated Soft Drinks |
| Wheat Flour | Snack Foods |
| Soybean Oil | Processed Food |
| Animal Feed | Poultry Products, Pork Products |

**[:供应给] (15 边)**

| 供给方 | 需求方 | 置信度 |
|--------|--------|--------|
| Nutrien | ADM | inferred |
| Nutrien | Cargill | inferred |
| Mosaic | Cargill | inferred |
| Corn | ADM | inferred |
| Corn | Cargill | inferred |
| Soybeans | ADM | inferred |
| Soybeans | Bunge | inferred |
| Wheat | ADM | inferred |
| Wheat | Cargill | inferred |
| HFCS | Coca-Cola | inferred |
| Corn Starch | Nestlé | inferred |
| Soybean Meal | Tyson | inferred |
| Soybean Oil | Nestlé | inferred |
| Animal Feed | Tyson | inferred |
| Wheat Flour | Nestlé | inferred |
| Animal Feed | Tyson | inferred |
| Wheat Flour | Nestlé | inferred |

---

### 项目结构

```
C:\Projects\knowledge_graph\
├── design.md                     # 本文件：数据模型 + ADR
├── schema/
│   ├── constraints.cypher        # 唯一性约束 + 索引
│   └── validation.cypher         # 数据质量校验查询
├── data/
│   ├── sources.md                # 数据接入指南（公开数据源映射）
│   ├── companies.csv             # columns: id, name, type, hq_country, hq_region, operating_countries, external_id
│   ├── commodities.csv           # columns: id, name, major_producing_countries
│   ├── products.csv              # columns: id, name, category
│   ├── edges_provide.csv         # columns: company_id, product_id, gross_margin_pct, revenue_share_pct, source
│   ├── edges_supply.csv          # columns: from_id, to_id, confidence, valid_from, valid_until, source
│   └── edges_used_in.csv         # columns: from_id, to_id, valid_from, valid_until, source
├── scripts/
│   ├── 00_schema_init.ipynb      # 运行约束 + 校验脚本
│   └── 01_load_data.ipynb        # LOAD CSV 数据导入管道
├── queries/
│   └── verification/
│       ├── 01_dependency_chain.cypher
│       ├── 02_composition_chain.cypher
│       ├── 03_common_dependency.cypher
│       ├── 04_alternate_supplier.cypher
│       └── 05_hub_analysis.cypher
└── requirements.txt              # neo4j, jupyter, pandas
```

---

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 图数据库 | Neo4j Community Edition 5.x | 最成熟属性图数据库，Cypher 查询语言对多跳遍历支持最好，GDS 库 (65+ 算法) 和 APOC (350+ 过程) 免费可用 |
| 数据加载 | CSV + LOAD CSV + Jupyter 编排 | CSV 为最低摩擦手工策展格式 (Excel 可编辑)，Jupyter 提供可视化反馈和迭代开发体验 |
| 数据管道 | Python 3.11 + neo4j driver v6 | Python 生态集成 pandas 做数据清洗，neo4j 官方驱动成熟稳定 |
| 可视化探索 | Neo4j Browser | CE 免费附带，支持交互式图可视化和 Cypher 编辑 |

**开发策略**：Schema-first。先建立唯一性约束和索引（`constraints.cypher`），再增量加载边数据。验证查询集 (5 条 Cypher) 作为验收测试——若查询结果不符合预期，修复数据或模型，不修改查询以拟合错误模型。

**数据库选型确认**：Neo4j CE 5.x 单数据库实例，Stage 1 无多租户或独立开发/测试环境需求。

---

### 已知局限与下阶段扩展

- **事件冲击分析**：Stage 1 不包含 Event 节点和 `[:影响]` 边。事件建模、地理匹配规则、冲击传播查询由独立 Event 项目定义。交接面：本图提供带 `valid_from`/`valid_until` 的依赖边和带 `hq_country`/`operating_countries` 的 Company 节点。
- **替代品分析**：Stage 1 不包含 `[:替代品]` 边和 Product Category 节点。由 Process (工序) 项目定义。交接面：本图提供 Product 节点和 `category` 属性。Stage 1 的"替代供应"查询仅限于同产品多供应商。
- **精确产地与物流节点**：当前地理精度限于国家/区域级，不支持城市/港口级分析。未来可增加产地、仓储、运输节点。
- **财务归因分析**：成本/收入信息仅作为边属性，无法进行复杂的事件驱动财务归因。未来可扩展 `FinancialImpactEvent` 节点。
- **时间属性完备性**：初期 `valid_from`/`valid_until` 大量留空。建议二期对核心 L1 关系补全有效期。
- **可控词汇规范**：`hq_country` 等字段的录入值推荐 ISO 3166 国家代码，图谱层不做硬约束，通过录入规范保证查询一致性。

---
