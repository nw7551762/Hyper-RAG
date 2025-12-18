# Hyper-RAG 中的 Vertices 与 Hyperedges 架构说明

## 目录
1. [核心概念](#核心概念)
2. [数据结构定义](#数据结构定义)
3. [超图的数学模型](#超图的数学模型)
4. [实现细节](#实现细节)
5. [Prompt来源与实体提取](#prompt来源与实体提取)
6. [查询机制](#查询机制)
7. [应用场景](#应用场景)

---

## 核心概念

### 什么是超图 (Hypergraph)?

**传统图 (Graph)** 只能表示二元关系（一条边连接两个节点），而 **超图 (Hypergraph)** 可以表示高阶关系（一条超边可以连接任意数量的节点）。

```
传统图:              超图:
A --- B             A ─┐
                        ├─ Hyperedge1
C --- D             B ─┘

                    C ─┐
                        │
                    D ──┼─ Hyperedge2
                        │
                    E ─┘
```

### Vertices (顶点)

**定义**: 在 Hyper-RAG 中，Vertices 代表从文本中提取的**实体 (Entity)**。

**属性结构**:
```python
{
    "entity_name": str,          # 实体名称 (唯一标识符)
    "entity_type": str,          # 实体类型
    "description": str,          # 实体描述
    "source_id": str,            # 来源文档块ID
    "additional_properties": str # 附加属性（时间、空间、情感等）
}
```

**实体类型** (`hyperrag/prompt.py:11`):
```python
DEFAULT_ENTITY_TYPES = [
    "organization",  # 组织
    "person",        # 人物
    "geo",           # 地理位置
    "event",         # 事件
    "role",          # 角色
    "concept"        # 概念
]
```

### Hyperedges (超边)

**定义**: Hyperedges 表示多个实体之间的**关系**，分为两个层次：

#### 1. Low-order Hyperedge (低阶超边)
- 通常连接 **2个实体**
- 表示实体间的直接关系（成对关系）

**属性结构**:
```python
{
    "entityN": List[str],        # 实体集合 (通常2个)
    "description": str,          # 关系描述
    "keywords": str,             # 关系关键词
    "weight": float,             # 关系强度 (0-10)
    "source_id": str,            # 来源文档块ID
    "level_hg": "Low-order Hyperedge"
}
```

**示例** (`hyperrag/prompt.py:93`):
```
("Low-order Hyperedge" | Alex | Taylor | Alex's frustration with Taylor's
authority showcases tension between rebellion and control. |
tension, competitive nature | 7)
```

#### 2. High-order Hyperedge (高阶超边)
- 连接 **3个或更多实体**
- 表示复杂的多元关系和主题
- 捕获超越成对关系的高阶语义

**属性结构**:
```python
{
    "entityN": List[str],              # 实体集合 (≥3个)
    "description": str,                # 高阶关系完整描述
    "generalization": str,             # 关系概括总结
    "keywords": str,                   # 高阶主题关键词
    "weight": float,                   # 关系强度
    "source_id": str,                  # 来源文档块ID
    "level_hg": "High-order Hyperedge"
}
```

**示例** (`hyperrag/prompt.py:97`):
```
("High-order Hyperedge" | Alex | Jordan | Taylor |
The connection illustrates complex interplay of authority, collaboration,
and shared goals for innovation, framed against controlling influences. |
innovation and authority dynamics, collaboration for change |
authority, collaboration, innovation | 8)
```

---

## 数据结构定义

### 基础接口定义 (`hyperrag/base.py`)

```python
@dataclass
class BaseHypergraphStorage(StorageNameSpace):
    # 顶点操作
    async def has_vertex(self, v_id: Any) -> bool
    async def get_vertex(self, v_id: str, default: Any = None)
    async def upsert_vertex(self, v_id: Any, v_data: Optional[Dict] = None)
    async def remove_vertex(self, v_id: Any)
    async def vertex_degree(self, v_id: Any) -> int

    # 超边操作
    async def has_hyperedge(self, e_tuple: Union[List, Set, Tuple]) -> bool
    async def get_hyperedge(self, e_tuple: Union[List, Set, Tuple], default: Any = None)
    async def upsert_hyperedge(self, e_tuple: Union[List, Set, Tuple], e_data: Optional[Dict] = None)
    async def remove_hyperedge(self, e_tuple: Union[List, Set, Tuple])
    async def hyperedge_degree(self, e_tuple: Union[List, Set, Tuple]) -> int

    # 邻居查询
    async def get_nbr_e_of_vertex(self, v_id: Any) -> List  # 获取顶点的邻接超边
    async def get_nbr_v_of_hyperedge(self, e_tuple: Union[List, Set, Tuple]) -> List  # 获取超边的邻接顶点
    async def get_nbr_v_of_vertex(self, v_id: Any, exclude_self=True) -> List  # 获取顶点的邻接顶点
```

### 存储实现 (`hyperrag/storage.py`)

```python
@dataclass
class HypergraphStorage(BaseHypergraphStorage):
    """
    基于 Hypergraph-DB 的存储实现

    文件格式: hypergraph_{namespace}.hgdb
    底层引擎: HypergraphDB (from hyperdb import HypergraphDB)
    """

    def __post_init__(self):
        # 加载或创建超图数据库
        self._hgdb_file = os.path.join(
            self.global_config["working_dir"],
            f"hypergraph_{self.namespace}.hgdb"
        )
        preloaded_hypergraph = HypergraphStorage.load_hypergraph(self._hgdb_file)
        self._hg = preloaded_hypergraph or HypergraphDB()
```

**核心方法**:
- `add_v(v_id, v_data)`: 添加顶点 (`storage.py:174`)
- `add_e(e_tuple, e_data)`: 添加超边 (`storage.py:177`)
- `nbr_e_of_v(v_id)`: 返回顶点的关联超边 (`storage.py:195`)
- `nbr_v_of_e(e_tuple)`: 返回超边的关联顶点 (`storage.py:201`)

---

## 超图的数学模型

### 数学定义

**超图** `H = (V, E)` 由以下组成：
- `V = {v₁, v₂, ..., vₙ}`: 顶点集合
- `E = {e₁, e₂, ..., eₘ}`: 超边集合
- 每条超边 `eᵢ ⊆ V`，即 `eᵢ` 是顶点的子集

### 度 (Degree)

**顶点度** (`degree_v`): 顶点 `v` 关联的超边数量
```python
degree_v(v) = |{e ∈ E : v ∈ e}|
```

**超边度** (`degree_e`): 超边 `e` 包含的顶点数量
```python
degree_e(e) = |e|
```

### 邻居关系

**顶点的超边邻居** (`nbr_e_of_v`):
```python
nbr_e_of_v(v) = {e ∈ E : v ∈ e}
```

**超边的顶点邻居** (`nbr_v_of_e`):
```python
nbr_v_of_e(e) = {v ∈ V : v ∈ e}
```

**顶点的顶点邻居** (`nbr_v`):
```python
nbr_v(v) = {u ∈ V : ∃e ∈ E, v ∈ e and u ∈ e, u ≠ v}
```

---

## 实现细节

### 1. 实体提取流程 (`hyperrag/operate.py:402`)

```python
async def extract_entities(
    chunks: dict[str, TextChunkSchema],
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict,
) -> BaseHypergraphStorage | None
```

**工作流程**:

```
输入: 文档块 (Chunks)
  │
  ├─> 1. 使用 LLM 提取实体和关系
  │     └─> Prompt: PROMPTS["entity_extraction"]
  │
  ├─> 2. 解析提取结果
  │     ├─> Entity 记录 → maybe_nodes
  │     ├─> Low-order Hyperedge → maybe_edges_low
  │     └─> High-order Hyperedge → maybe_edges_high
  │
  ├─> 3. 合并和汇总
  │     ├─> _merge_nodes_then_upsert()     # 合并相同实体
  │     └─> _merge_edges_then_upsert()     # 合并相同关系
  │
  └─> 4. 存储到数据库
        ├─> HypergraphStorage (超图数据库)
        ├─> NanoVectorDB (实体向量数据库)
        └─> NanoVectorDB (关系向量数据库)
```

### 2. 实体记录解析 (`operate.py:174-195`)

```python
async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    # 格式: ("Entity" | entity_name | entity_type | description | additional_properties)
    if len(record_attributes) < 4 or record_attributes[0] != '"Entity"':
        return None

    entity_name = clean_str(record_attributes[1].upper())
    entity_type = clean_str(record_attributes[2].upper())
    entity_description = clean_str(record_attributes[3])
    entity_additional_properties = clean_str(record_attributes[4:])

    return dict(
        entity_name=entity_name,
        entity_type=entity_type,
        description=entity_description,
        source_id=chunk_key,
        additional_properties=entity_additional_properties,
    )
```

### 3. 低阶超边解析 (`operate.py:198-223`)

```python
async def _handle_single_relationship_extraction_low(
    record_attributes: list[str],
    chunk_key: str,
):
    # 格式: ("Low-order Hyperedge" | entity1 | entity2 | ... | description | keywords | weight)
    if len(record_attributes) < 6 or record_attributes[0] != '"Low-order Hyperedge"':
        return None

    entity_num = len(record_attributes) - 3
    entities = []
    for i in range(1, entity_num):
        entities.append(clean_str(record_attributes[i].upper()))

    edge_description = clean_str(record_attributes[-3])
    edge_keywords = clean_str(record_attributes[-2])
    weight = float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 0.75

    return dict(
        entityN=entities,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=chunk_key,
        level_hg="Low-order Hyperedge",
    )
```

### 4. 高阶超边解析 (`operate.py:225-249`)

```python
async def _handle_single_relationship_extraction_high(
    record_attributes: list[str],
    chunk_key: str,
):
    # 格式: ("High-order Hyperedge" | entity1 | entity2 | entity3 | ... |
    #        description | generalization | keywords | weight)
    if len(record_attributes) < 7 or record_attributes[0] != '"High-order Hyperedge"':
        return None

    entity_num = len(record_attributes) - 4
    entities = []
    for i in range(1, entity_num):
        entities.append(clean_str(record_attributes[i].upper()))

    edge_description = clean_str(record_attributes[-4])
    edge_keywords = clean_str(record_attributes[-2])
    weight = float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 0.75

    return dict(
        entityN=entities,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=chunk_key,
        level_hg="High-order Hyperedge",
    )
```

### 5. 实体合并 (`operate.py:252-328`)

```python
async def _merge_nodes_then_upsert(
    entity_name: str,
    nodes_data: list[dict],
    knowledge_hypergraph_inst,
    global_config: dict,
):
    """
    合并多个相同实体的描述和属性

    步骤:
    1. 收集已存在的实体数据
    2. 统计最常见的实体类型
    3. 合并所有描述 (使用 GRAPH_FIELD_SEP 分隔)
    4. 使用 LLM 汇总描述 (如果过长)
    5. 插入或更新超图数据库
    """
    # 获取已存在的实体
    already_node = await knowledge_hypergraph_inst.get_vertex(entity_name)

    # 选择最常见的实体类型
    entity_type = sorted(
        Counter([dp["entity_type"] for dp in nodes_data] + already_entity_types).items(),
        key=lambda x: x[1], reverse=True
    )[0][0]

    # 合并描述
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in nodes_data] + already_description))
    )

    # 汇总描述 (如果太长)
    description = await _handle_entity_summary(entity_name, description, global_config)

    # 更新到超图
    await knowledge_hypergraph_inst.upsert_vertex(entity_name, node_data)
```

### 6. 关系合并 (`operate.py:331-399`)

```python
async def _merge_edges_then_upsert(
    id_set: tuple,
    edges_data: list[dict],
    knowledge_hypergraph_inst,
    global_config: dict,
):
    """
    合并多个相同超边的描述和权重

    步骤:
    1. 收集已存在的超边数据
    2. 累加权重 (weight)
    3. 合并描述和关键词
    4. 使用 LLM 汇总 (如果过长)
    5. 确保所有顶点存在
    6. 插入或更新超边
    """
    # 累加权重
    weight = sum([dp["weight"] for dp in edges_data] + already_weights)

    # 合并描述和关键词
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in edges_data] + already_description))
    )
    keywords = GRAPH_FIELD_SEP.join(
        sorted(set([dp["keywords"] for dp in edges_data] + already_keywords))
    )

    # 确保所有顶点存在
    for need_insert_id in id_set:
        if not (await knowledge_hypergraph_inst.has_vertex(need_insert_id)):
            await knowledge_hypergraph_inst.upsert_vertex(need_insert_id, {...})

    # 更新超边
    await knowledge_hypergraph_inst.upsert_hyperedge(id_set, edge_data)
```

---

## Prompt来源与实体提取

### 主提取Prompt (`hyperrag/prompt.py:13-71`)

```python
PROMPTS["entity_extraction"] = """
-Goal-
Given a text document and a list of entity types, identify all entities
of these types from the text. Then construct hyperedges by extracting
complex relationships among the identified entities.

-Steps-

1. Identify all entities:
   Format: ("Entity" | <entity_name> | <entity_type> | <entity_description> |
            <additional_properties>)

2. Identify pairs of related entities:
   Format: ("Low-order Hyperedge" | <entity_name1> | <entity_name2> |
            <description> | <keywords> | <strength>)

3. Extract high-level keywords:
   Format: ("High-level keywords" | <high_level_keywords>)

4. Construct high-order associated entity sets:
   Format: ("High-order Hyperedge" | <entity_name1> | <entity_name2> | ... |
            <description> | <generalization> | <keywords> | <strength>)

5. Return all entities, relationships and associations.

6. When finished, output {completion_delimiter}.
"""
```

**关键参数** (`prompt.py:5-8`):
```python
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = " | "     # 字段分隔符
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "\n"     # 记录分隔符
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"  # 完成标记
```

### 提取示例 (`prompt.py:73-207`)

系统提供了5个详细的提取示例，涵盖：
1. **Example 1** (lines 74-98): 小说文本 - 人物关系与设备创新
2. **Example 2** (lines 99-118): 科幻场景 - 外星接触与任务演变
3. **Example 3** (lines 119-147): 科技对话 - 智能体通信与首次接触
4. **Example 4** (lines 148-176): 国际新闻 - 人质交换与地理位置
5. **Example 5** (lines 177-206): 金融新闻 - 政策决策与市场影响

### 汇总Prompt (`prompt.py:209-292`)

**实体描述汇总** (`prompt.py:210-228`):
```python
PROMPTS["summarize_entity_descriptions"] = """
Given one entity and a list of its descriptions.
Please concatenate all of these into a single, comprehensive description.
Make sure to include information collected from all the descriptions.
If contradictory, resolve contradictions and provide a coherent summary.
"""
```

**关系描述汇总** (`prompt.py:251-270`):
```python
PROMPTS["summarize_relation_descriptions"] = """
Given a set of entities, and a list of descriptions describing the
relations between the entities.
Please concatenate all into a single, comprehensive description.
Cover all elements of the entity set as much as possible.
"""
```

**关系关键词汇总** (`prompt.py:272-292`):
```python
PROMPTS["summarize_relation_keywords"] = """
Given a set of entities, and a list of keywords describing the relations.
Please select important keywords from the keywords list.
Keywords should summarize important events or themes, avoiding vague terms.
"""
```

---

## 查询机制

### 1. 基于实体的上下文构建 (`operate.py:619-740`)

```python
async def _build_entity_query_context(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
):
    """
    基于实体的检索 (Entity-centric Retrieval)

    流程:
    1. 向量检索相关实体 (top_k)
    2. 获取实体数据和度数 (rank)
    3. 找到相关的超边 (关系)
    4. 找到相关的文本块 (源文档)
    5. 返回结构化上下文 (CSV格式)
    """
    # 1. 向量检索实体
    results = await entities_vdb.query(query, top_k=query_param.top_k)

    # 2. 获取实体数据
    node_datas = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_vertex(r["entity_name"]) for r in results]
    )

    # 3. 获取实体度数作为排名
    node_degrees = await asyncio.gather(
        *[knowledge_hypergraph_inst.vertex_degree(r["entity_name"]) for r in results]
    )

    # 4. 查找相关超边
    use_relations = await _find_most_related_edges_from_entities(
        node_datas, query_param, knowledge_hypergraph_inst
    )

    # 5. 查找相关文本块
    use_text_units = await _find_most_related_text_unit_from_entities(
        node_datas, query_param, text_chunks_db, knowledge_hypergraph_inst
    )

    # 6. 格式化为CSV表格
    context_string = f"""
-----Entities-----
```csv
{entities_context}
```
-----Relationships-----
```csv
{relations_context}
```
-----Sources-----
```csv
{text_units_context}
```
"""
    return {"context": context_string, "entities": [...], "hyperedges": [...], ...}
```

### 2. 查找相关超边 (`operate.py:827-861`)

```python
async def _find_most_related_edges_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
):
    """
    从实体查找相关超边

    步骤:
    1. 获取每个实体的所有邻接超边
    2. 去重合并所有超边
    3. 获取超边数据和度数
    4. 按度数和权重排序
    5. 按token大小截断
    """
    # 1. 获取邻接超边
    all_related_edges = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_nbr_e_of_vertex(dp['entity_name'])
          for dp in node_datas]
    )

    # 2. 去重
    all_edges = set()
    for this_edges in all_related_edges:
        all_edges.update([tuple(sorted(e)) for e in this_edges])

    # 3. 获取超边数据
    all_edges_pack = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_hyperedge(e) for e in all_edges]
    )

    # 4. 获取超边度数
    all_edges_degree = await asyncio.gather(
        *[knowledge_hypergraph_inst.hyperedge_degree(e) for e in all_edges]
    )

    # 5. 排序和截断
    all_edges_data = sorted(
        all_edges_data,
        key=lambda x: (x["rank"], x["weight"]),
        reverse=True
    )
    all_edges_data = truncate_list_by_token_size(
        all_edges_data,
        key=lambda x: x["description"],
        max_token_size=query_param.max_token_for_relation_context,
    )

    return all_edges_data
```

### 3. 基于关系的上下文构建 (`operate.py:864-992`)

```python
async def _build_relation_query_context(
    keywords,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
):
    """
    基于关系的检索 (Relation-centric Retrieval)

    流程:
    1. 向量检索相关超边 (top_k)
    2. 获取超边数据和度数
    3. 找到相关的实体
    4. 找到相关的文本块
    5. 返回结构化上下文
    """
    # 1. 向量检索超边
    results = await relationships_vdb.query(keywords, top_k=query_param.top_k)

    # 2. 获取超边数据
    edge_datas = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_hyperedge(r['id_set']) for r in results]
    )

    # 3. 获取超边度数
    edge_degree = await asyncio.gather(
        *[knowledge_hypergraph_inst.hyperedge_degree(e['id_set']) for e in results]
    )

    # 4. 排序和截断
    edge_datas = sorted(
        edge_datas,
        key=lambda x: (x["rank"], x["weight"]),
        reverse=True
    )

    # 5. 查找相关实体
    use_entities = await _find_most_related_entities_from_relationships(
        edge_datas, query_param, knowledge_hypergraph_inst
    )

    # 6. 查找相关文本块
    use_text_units = await _find_related_text_unit_from_relationships(
        edge_datas, query_param, text_chunks_db, knowledge_hypergraph_inst
    )

    return {"context": context_string, "entities": [...], "hyperedges": [...], ...}
```

### 4. 超图查询模式 (`operate.py:1064-1179`)

```python
async def hyper_query(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    """
    完整的超图查询 (Hyper Query Mode)

    特点:
    - 同时使用实体检索和关系检索
    - 提取低阶和高阶关键词
    - 合并两种检索的结果
    """
    # 1. 提取查询关键词
    kw_prompt = PROMPTS["keywords_extraction"].format(query=query)
    result = await use_model_func(kw_prompt)
    keywords_data = json.loads(result)

    entity_keywords = keywords_data.get("low_level_keywords", [])      # 低阶关键词
    relation_keywords = keywords_data.get("high_level_keywords", [])   # 高阶关键词

    # 2. 基于实体的检索 (使用低阶关键词)
    if entity_keywords:
        entity_context = await _build_entity_query_context(
            entity_keywords, knowledge_hypergraph_inst, entities_vdb,
            text_chunks_db, query_param
        )

    # 3. 基于关系的检索 (使用高阶关键词)
    if relation_keywords:
        relation_context = await _build_relation_query_context(
            relation_keywords, knowledge_hypergraph_inst, entities_vdb,
            relationships_vdb, text_chunks_db, query_param
        )

    # 4. 合并两种检索结果
    context = combine_contexts(
        relation_context.get("context"),
        entity_context.get("context")
    )

    contextJson = {
        "entities": deduplicate_by_key(
            entity_context.get("entities", []) + relation_context.get("entities", []),
            "entity_name"
        ),
        "hyperedges": deduplicate_by_key(
            entity_context.get("hyperedges", []) + relation_context.get("hyperedges", []),
            "entity_set"
        ),
        "text_units": deduplicate_by_key(
            entity_context.get("text_units", []) + relation_context.get("text_units", []),
            "content"
        )
    }

    # 5. 使用LLM生成最终答案
    sys_prompt = PROMPTS["rag_response"].format(
        context_data=context, response_type=query_param.response_type
    )
    response = await use_model_func(query + define_str, system_prompt=sys_prompt)

    return response
```

### 5. 其他查询模式

**Hyper-Lite Query** (`operate.py:1182-1274`):
- 仅使用实体检索
- 更快但可能遗漏高阶关系

**Graph Query** (`operate.py:1277-1505`):
- 只检索成对关系（二元关系）
- 模拟传统图RAG

**Naive Query** (`operate.py:1583-1630`):
- 简单的语义搜索
- 不使用超图结构

**LLM Query** (`operate.py:1633-1664`):
- 直接调用LLM
- 不使用任何检索

---

## 应用场景

### 1. 文档理解
- **多实体关系分析**: 理解文档中多个实体的复杂关联
- **主题提取**: 通过高阶超边识别文档主题

### 2. 问答系统
- **实体驱动**: 通过实体找到相关关系和文档
- **关系驱动**: 通过关系找到相关实体和文档
- **混合检索**: 结合实体和关系进行全面检索

### 3. 知识图谱构建
- **自动提取**: 从文本自动提取实体和关系
- **关系汇总**: 合并多个文档中相同实体/关系的描述
- **高阶建模**: 捕获传统图谱无法表示的多元关系

### 4. Web UI 交互 (`web-ui/backend/`)

**数据库管理** (`db.py`):
- CRUD操作顶点和超边
- 查询超图统计信息
- 导出超图数据

**可视化** (`web-ui/frontend/src/pages/Hyper/Graph`):
- 使用 AntV G6 渲染超图
- 交互式探索实体和关系

**实时处理** (`file_manager.py`):
- 文档上传和分块
- 实体提取进度展示
- WebSocket日志推送

---

## 总结

### Vertices vs Hyperedges

| 维度 | Vertices (顶点) | Hyperedges (超边) |
|------|----------------|-------------------|
| **表示** | 实体 (Entity) | 关系 (Relationship) |
| **连接度** | 0 (独立节点) | 2个或更多顶点 |
| **类型** | organization, person, geo, event, role, concept | Low-order (2实体), High-order (3+实体) |
| **关键属性** | entity_name, entity_type, description, additional_properties | entityN, description, keywords, weight |
| **存储** | HypergraphDB.add_v() | HypergraphDB.add_e() |
| **检索** | 实体向量数据库 | 关系向量数据库 |
| **度** | degree_v (邻接超边数) | degree_e (包含顶点数) |

### 核心优势

1. **超越二元关系**: 可以表示3个或更多实体的复杂关系
2. **层次化建模**: 区分低阶（成对）和高阶（主题）关系
3. **丰富的语义**: 每个实体和关系都有详细的描述和属性
4. **可扩展性**: 基于向量数据库实现快速检索
5. **灵活查询**: 支持实体驱动、关系驱动和混合查询

### 文件位置索引

- **核心定义**: `hyperrag/base.py:86-138`
- **存储实现**: `hyperrag/storage.py:118-208`
- **实体提取**: `hyperrag/operate.py:402-616`
- **查询实现**: `hyperrag/operate.py:619-1179`
- **Prompt模板**: `hyperrag/prompt.py:1-402`
- **Web UI数据库**: `web-ui/backend/hyperdb/base.py`
- **主类入口**: `hyperrag/hyperrag.py`

---

## 参考资料

- Hypergraph-DB: [基础超图数据库引擎](https://github.com/gaoruixian/hypergraph-db)
- NanoVectorDB: 轻量级向量数据库
- GraphRAG: Microsoft的图增强检索论文
- 项目文档: `/CLAUDE.md`, `/README.md`
