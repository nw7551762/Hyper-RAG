# Hyper-RAG 技術實作指南

## 目錄
- [概述](#概述)
- [架構設計](#架構設計)
- [文檔處理流程 (Insert)](#文檔處理流程-insert)
- [查詢流程 (Query)](#查詢流程-query)
- [查詢模式詳解](#查詢模式詳解)
- [Prompt 系統](#prompt-系統)
- [儲存層實作](#儲存層實作)
- [超圖特色](#超圖特色)

---

## 概述

Hyper-RAG 是一個基於超圖 (Hypergraph) 的檢索增強生成 (RAG) 系統,通過超圖建模複雜關係來減少 LLM 幻覺。與傳統 RAG 系統相比,Hyper-RAG 的核心創新在於:

1. **超圖結構**: 支援高階關係 (3+ 個實體的關聯),而非僅限於成對關係
2. **多模態檢索**: 結合實體檢索、關係檢索和語義檢索
3. **關鍵詞分層**: 區分低階關鍵詞 (具體實體) 和高階關鍵詞 (抽象主題)

---

## 架構設計

### 核心組件

```
HyperRAG (hyperrag/hyperrag.py)
├── 儲存層
│   ├── full_docs: 完整文檔 (JsonKVStorage)
│   ├── text_chunks: 文本片段 (JsonKVStorage)
│   ├── entities_vdb: 實體向量數據庫 (NanoVectorDB)
│   ├── relationships_vdb: 關係向量數據庫 (NanoVectorDB)
│   ├── chunks_vdb: 片段向量數據庫 (NanoVectorDB)
│   └── chunk_entity_relation_hypergraph: 超圖數據庫 (HypergraphDB)
├── 操作層 (hyperrag/operate.py)
│   ├── chunking_by_token_size(): 文檔分塊
│   ├── extract_entities(): 實體和關係提取
│   ├── hyper_query(): 完整超圖查詢
│   ├── hyper_query_lite(): 輕量級超圖查詢
│   ├── graph_query(): 傳統圖查詢 (僅二元關係)
│   ├── naive_query(): 樸素向量檢索
│   └── llm_query(): 純 LLM 回答
└── Prompt 系統 (hyperrag/prompt.py)
    ├── entity_extraction: 實體提取提示詞
    ├── keywords_extraction: 關鍵詞提取提示詞
    ├── rag_response: RAG 回答提示詞
    └── 總結類提示詞
```

---

## 文檔處理流程 (Insert)

### 1. 入口函數

**文件**: `hyperrag/hyperrag.py:173-235`

```python
async def ainsert(self, string_or_strings):
    # 1. 去重 - 過濾已存在的文檔
    # 2. 分塊 - chunking_by_token_size()
    # 3. 提取實體和關係 - extract_entities()
    # 4. 存儲到各個數據庫
```

### 2. 文檔分塊

**文件**: `hyperrag/operate.py:34-52`

**函數**: `chunking_by_token_size(content, overlap_token_size=128, max_token_size=1024, tiktoken_model="gpt-4o")`

**原理**:
- 使用 tiktoken 將文本編碼為 token
- 按固定 token 數 (默認 1200) 分塊
- 支持重疊 (默認 100 tokens) 以保持上下文連續性
- 每個 chunk 包含: `tokens`, `content`, `chunk_order_index`

**配置參數** (hyperrag/hyperrag.py:68-71):
```python
chunk_token_size: int = 1200          # 每塊大小
chunk_overlap_token_size: int = 100   # 重疊大小
tiktoken_model_name: str = "gpt-4o-mini"
```

### 3. 實體和關係提取

**文件**: `hyperrag/operate.py:402-616`

**函數**: `extract_entities(chunks, knowledge_hypergraph_inst, entity_vdb, relationships_vdb, global_config)`

#### 流程:

1. **並發調用 LLM 提取** (544-546行):
   ```python
   results = await asyncio.gather(
       *[_process_single_content(c) for c in ordered_chunks]
   )
   ```

2. **單個 chunk 處理** (`_process_single_content`, 441-539行):
   - 使用 `entity_extraction` prompt 提取實體和關係
   - 支持多輪提取 (gleaning): 最多執行 `entity_extract_max_gleaning` 次
   - 解析返回的結構化數據

3. **實體合併** (`_merge_nodes_then_upsert`, 252-328行):
   - 合併同名實體的描述
   - 使用 LLM 總結描述 (如果超過 `entity_summary_to_max_tokens`)
   - 合併附加屬性 (additional_properties)

4. **關係合併** (`_merge_edges_then_upsert`, 331-399行):
   - 合併相同實體集的超邊
   - 權重累加
   - 使用 LLM 總結描述和關鍵詞

5. **存儲到數據庫** (594-614行):
   - 實體 → `entities_vdb` (向量化: entity_name + description)
   - 關係 → `relationships_vdb` (向量化: keywords + entity_set + description)
   - 超邊和頂點 → `chunk_entity_relation_hypergraph`

#### 配置參數 (hyperrag/hyperrag.py:73-78):
```python
entity_extract_max_gleaning: int = 1          # 多輪提取次數
entity_summary_to_max_tokens: int = 500       # 實體描述最大 token
entity_additional_properties_to_max_tokens: int = 250
relation_summary_to_max_tokens: int = 750     # 關係描述最大 token
relation_keywords_to_max_tokens: int = 100    # 關係關鍵詞最大 token
```

---

## 查詢流程 (Query)

### 入口函數

**文件**: `hyperrag/hyperrag.py:257-305`

```python
async def aquery(self, query: str, param: QueryParam = QueryParam()):
    if param.mode == "hyper":
        response = await hyper_query(...)
    elif param.mode == "hyper-lite":
        response = await hyper_query_lite(...)
    elif param.mode == "graph":
        response = await graph_query(...)
    elif param.mode == "naive":
        response = await naive_query(...)
    elif param.mode == "llm":
        response = await llm_query(...)
```

### QueryParam 配置

**文件**: `hyperrag/base.py`

```python
@dataclass
class QueryParam:
    mode: str = "hyper"                          # 查詢模式
    only_need_context: bool = False              # 僅返回上下文
    response_type: str = "Multiple Paragraphs"   # 回答類型
    return_type: str = "str"                     # 返回格式 (str/json)
    top_k: int = 60                              # 檢索 top-k
    max_token_for_text_unit: int = 4000         # 文本單元最大 token
    max_token_for_entity_context: int = 4000    # 實體上下文最大 token
    max_token_for_relation_context: int = 4000  # 關係上下文最大 token
```

---

## 查詢模式詳解

### 1. Hyper Query (完整超圖查詢)

**文件**: `hyperrag/operate.py:1064-1179`

**流程**:

1. **關鍵詞提取** (1077-1105行):
   ```python
   # 使用 keywords_extraction prompt
   result = await use_model_func(kw_prompt)
   keywords_data = json.loads(result)
   entity_keywords = keywords_data.get("low_level_keywords", [])      # 具體實體
   relation_keywords = keywords_data.get("high_level_keywords", [])   # 抽象主題
   ```

2. **構建實體上下文** (1111-1122行):
   - 調用 `_build_entity_query_context(entity_keywords, ...)`
   - 從 `entities_vdb` 檢索相關實體 (top_k)
   - 獲取實體的一跳鄰居超邊
   - 獲取相關文本片段
   - 返回結構化上下文 (entities + hyperedges + text_units)

3. **構建關係上下文** (1124-1132行):
   - 調用 `_build_relation_query_context(relation_keywords, ...)`
   - 從 `relationships_vdb` 檢索相關關係 (top_k)
   - 獲取關係涉及的實體
   - 獲取相關文本片段

4. **合併上下文** (1137行):
   ```python
   context = combine_contexts(relation_context, entity_context)
   ```

5. **生成回答** (1158-1165行):
   - 使用 `rag_response` prompt
   - 將上下文和查詢傳給 LLM
   - 可選返回 JSON 格式 (包含 entities, hyperedges, text_units, response)

**特點**:
- 同時利用實體和關係檢索
- 通過超圖擴展一跳鄰域
- 支持高階關係 (3+ 個實體)

### 2. Hyper Query Lite (輕量級超圖查詢)

**文件**: `hyperrag/operate.py:1182-1274`

**與 Hyper Query 的區別**:
- 僅使用低階關鍵詞 (low_level_keywords)
- 僅構建實體上下文,不構建關係上下文
- 計算更快,適合簡單查詢

### 3. Graph Query (傳統圖查詢)

**文件**: `hyperrag/operate.py:1277-1505`

**特點**:
- 僅處理二元關係 (成對關係)
- 過濾掉高階超邊 (1318-1319行):
  ```python
  def filter_pairwise_edges(edges):
      return [e for e in edges if len(e["id_set"]) == 2]
  ```
- 用於與傳統 Knowledge Graph 方法對比

### 4. Naive Query (樸素查詢)

**文件**: `hyperrag/operate.py:1583-1630`

**流程**:
1. 直接從 `chunks_vdb` 檢索相關文本片段 (top_k)
2. 不使用實體和關係信息
3. 使用 `naive_rag_response` prompt 生成回答

**特點**:
- 類似傳統向量檢索 RAG
- 無需構建知識圖譜
- 作為 baseline

### 5. LLM Query (純 LLM)

**文件**: `hyperrag/operate.py:1633-1664`

**特點**:
- 不進行任何檢索
- 直接調用 LLM
- 用於對比檢索的效果

---

## Prompt 系統

### 1. 實體提取 Prompt

**文件**: `hyperrag/prompt.py:13-71`

**Prompt 名稱**: `entity_extraction`

**核心指令**:

```
-Goal-
Given a text document and entity types, identify all entities and construct hyperedges.

-Steps-
1. Identify all entities
   - entity_name, entity_type, entity_description, additional_properties
   - Format: ("Entity"|<name>|<type>|<description>|<properties>)

2. Identify all pairs of related entities (Low-order Hyperedge)
   - entities_pair, description, keywords, strength
   - Format: ("Low-order Hyperedge"|<entity1>|<entity2>|<description>|<keywords>|<strength>)

3. Extract high-level keywords
   - Format: ("High-level keywords"|<keywords>)

4. Construct high-order entity sets (High-order Hyperedge)
   - entities_set (3+ entities), description, generalization, keywords, strength
   - Format: ("High-order Hyperedge"|<entity1>|<entity2>|...|<description>|<generalization>|<keywords>|<strength>)
```

**配置項** (prompt.py:5-11):
```python
DEFAULT_LANGUAGE = '中文'
DEFAULT_TUPLE_DELIMITER = " | "
DEFAULT_RECORD_DELIMITER = "\n"
DEFAULT_COMPLETION_DELIMITER = "<|COMPLETE|>"
DEFAULT_ENTITY_TYPES = ["organization", "person", "geo", "event", "role", "concept"]
```

**範例** (prompt.py:73-206):
- 提供 5 個完整範例,涵蓋不同領域
- 每個範例展示如何提取實體、低階超邊、高階超邊

**處理流程** (operate.py:414-431):
```python
# 選擇範例 (這裡使用第 4 個範例)
example_prompt = PROMPTS["entity_extraction_examples"][3]
example_str = example_prompt.format(**example_base)

# 構建最終 prompt
context_base = dict(
    language=PROMPTS["DEFAULT_LANGUAGE"],
    entity_types=",".join(PROMPTS["DEFAULT_ENTITY_TYPES"]),
    tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
    record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
    completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
    examples=example_str
)
hint_prompt = entity_extract_prompt.format(**context_base, input_text=content)
```

### 2. 多輪提取 Prompt

**Continue Extraction** (prompt.py:295-297):
```
MANY entities were missed in the last extraction. Add them below using the same format:
```

**If Loop Extraction** (prompt.py:300-302):
```
It appears some entities may have still been missed.
Answer YES | NO if there are still entities that need to be added.
```

**使用流程** (operate.py:453-468):
```python
for now_glean_index in range(entity_extract_max_gleaning):
    # 繼續提取
    glean_result = await use_llm_func(continue_prompt, history_messages=history)
    final_result += glean_result

    # 詢問是否還有遺漏
    if_loop_result = await use_llm_func(if_loop_prompt, history_messages=history)
    if if_loop_result.lower() != "yes":
        break
```

### 3. 總結類 Prompt

#### 3.1 實體描述總結

**Prompt**: `summarize_entity_descriptions` (prompt.py:209-228)

```
Given one entity and a list of its descriptions.
Please concatenate all into a single, comprehensive description.
Resolve contradictions if any.
```

**觸發條件** (operate.py:65-67):
```python
if len(tokens) < summary_max_tokens:  # 小於 500 tokens
    return description  # 無需總結
# 否則調用 LLM 總結
```

#### 3.2 實體附加屬性總結

**Prompt**: `summarize_entity_additional_properties` (prompt.py:230-249)

**觸發條件**: 附加屬性超過 `entity_additional_properties_to_max_tokens` (250 tokens)

#### 3.3 關係描述總結

**Prompt**: `summarize_relation_descriptions` (prompt.py:251-270)

```
Given a set of entities and relation descriptions.
Concatenate into a comprehensive description covering all entities.
```

**觸發條件**: 描述超過 `relation_summary_to_max_tokens` (750 tokens)

#### 3.4 關係關鍵詞總結

**Prompt**: `summarize_relation_keywords` (prompt.py:272-292)

```
Select important keywords from the keywords list.
Keywords should summarize important events or themes.
Avoid vague or empty terms.
```

**輸出格式**: `{keyword1,keyword2,keyword3,...,keywordN}`

### 4. 關鍵詞提取 Prompt

**Prompt**: `keywords_extraction` (prompt.py:328-382)

**目標**:
```
Identify both high-level and low-level keywords in the user's query.
- high_level_keywords: overarching concepts or themes
- low_level_keywords: specific entities or details
```

**輸出格式**:
```json
{
  "high_level_keywords": ["International trade", "Global economic stability"],
  "low_level_keywords": ["Trade agreements", "Tariffs", "Currency exchange"]
}
```

**範例** (prompt.py:346-375):
- Example 1: 國際貿易對全球經濟穩定的影響
- Example 2: 森林砍伐對生物多樣性的環境後果
- Example 3: 教育在減少貧困中的作用

**使用** (operate.py:1077-1105):
```python
kw_prompt = PROMPTS["keywords_extraction"].format(query=query)
result = await use_model_func(kw_prompt)
keywords_data = json.loads(result)
entity_keywords = keywords_data.get("low_level_keywords", [])
relation_keywords = keywords_data.get("high_level_keywords", [])
```

### 5. RAG 回答 Prompt

**Prompt**: `rag_response` (prompt.py:306-326)

```
---Role---
You are a helpful assistant responding to questions about data in tables.

---Goal---
Generate a response summarizing information in input data tables.
If you don't know, just say so. Do not make anything up.
Do not include information without supporting evidence.

---Target response length and format---
{response_type}

---Data tables---
{context_data}
```

**Context 格式** (operate.py:693-706):
```
-----Entities-----
```csv
id,entity,type,description,additional properties,rank
0,Entity1,person,Description1,Properties1,5
...
```
-----Relationships-----
```csv
id,entity set,description,keywords,weight,rank
0,(Entity1,Entity2,Entity3),Desc,Keywords,0.8,3
...
```
-----Sources-----
```csv
id,content
0,Original text chunk 1
...
```
```

**定義提示** (prompt.py:396-401):
```
Through existing analysis, the potential keywords/themes are:
{ low_level_keywords | high_level_keywords }
Please refer to keywords, select useful information to answer accurately.
Don't blindly splice knowledge! Answer needs to be accurate, detailed, comprehensive.
```

### 6. Naive RAG Prompt

**Prompt**: `naive_rag_response` (prompt.py:384-394)

```
Below are the knowledge you know:
{content_data}
---
If you don't know the answer, just say so. Do not make anything up.
```

**與 rag_response 的區別**:
- 更簡單的格式
- 直接提供文本片段,不使用表格結構

---

## 儲存層實作

### 1. JsonKVStorage (Key-Value 存儲)

**文件**: `hyperrag/storage.py:18-56`

**用途**:
- 存儲完整文檔 (`full_docs`)
- 存儲文本片段 (`text_chunks`)
- 存儲 LLM 響應緩存 (`llm_response_cache`)

**實作**:
```python
@dataclass
class JsonKVStorage(BaseKVStorage):
    _file_name: str  # e.g., "kv_store_full_docs.json"
    _data: dict      # 內存中的字典

    async def get_by_id(self, id):
        return self._data.get(id, None)

    async def upsert(self, data: dict[str, dict]):
        left_data = {k: v for k, v in data.items() if k not in self._data}
        self._data.update(left_data)
        return left_data

    async def index_done_callback(self):
        write_json(self._data, self._file_name)  # 保存到磁盤
```

### 2. NanoVectorDBStorage (向量數據庫)

**文件**: `hyperrag/storage.py:58-114`

**用途**:
- 存儲實體向量 (`entities_vdb`)
- 存儲關係向量 (`relationships_vdb`)
- 存儲片段向量 (`chunks_vdb`)

**實作**:
```python
@dataclass
class NanoVectorDBStorage(BaseVectorStorage):
    _client: NanoVectorDB  # nano-vectordb 客戶端
    cosine_better_than_threshold: float = 0.2  # 相似度閾值

    async def upsert(self, data: dict[str, dict]):
        # 1. 提取內容
        contents = [v["content"] for v in data.values()]

        # 2. 批量調用 embedding 函數
        batches = [contents[i:i+batch_size] for i in range(0, len(contents), batch_size)]
        embeddings_list = await asyncio.gather(*[self.embedding_func(batch) for batch in batches])
        embeddings = np.concatenate(embeddings_list)

        # 3. 存儲到向量數據庫
        self._client.upsert(datas=list_data)

    async def query(self, query: str, top_k=5):
        # 1. 查詢向量化
        embedding = await self.embedding_func([query])

        # 2. 向量檢索
        results = self._client.query(
            query=embedding[0],
            top_k=top_k,
            better_than_threshold=self.cosine_better_than_threshold
        )
        return results
```

**配置** (hyperrag/hyperrag.py:81-82):
```python
embedding_func: EmbeddingFunc = openai_embedding
embedding_batch_num: int = 32           # 批量大小
embedding_func_max_async: int = 16      # 最大並發數
```

### 3. HypergraphStorage (超圖數據庫)

**文件**: `hyperrag/storage.py:117-208`

**底層庫**: `hyperdb` (Hypergraph-DB)

**核心操作**:
```python
@dataclass
class HypergraphStorage(BaseHypergraphStorage):
    _hg: HypergraphDB

    # 頂點操作
    async def has_vertex(self, v_id) -> bool
    async def get_vertex(self, v_id)
    async def upsert_vertex(self, v_id, v_data)
    async def vertex_degree(self, v_id) -> int
    async def get_nbr_e_of_vertex(self, v_id)  # 獲取鄰居超邊

    # 超邊操作
    async def has_hyperedge(self, e_tuple) -> bool
    async def get_hyperedge(self, e_tuple)
    async def upsert_hyperedge(self, e_tuple, e_data)
    async def hyperedge_degree(self, e_tuple) -> int
    async def get_nbr_v_of_hyperedge(self, e_tuple)  # 獲取鄰居頂點

    # 持久化
    async def index_done_callback(self):
        self._hg.save(self._hgdb_file)  # 保存為 .hgdb 文件
```

**數據結構**:

頂點數據:
```python
{
    "entity_type": "person",
    "description": "Entity description",
    "additional_properties": "Properties",
    "source_id": "chunk-abc123<SEP>chunk-def456"
}
```

超邊數據:
```python
{
    "description": "Relation description",
    "keywords": "keyword1, keyword2",
    "weight": 0.85,
    "source_id": "chunk-abc123"
}
```

---

## 超圖特色

### 1. 什麼是超圖?

**傳統圖 (Graph)**:
- 邊連接兩個頂點: `(A, B)`
- 只能表達成對關係

**超圖 (Hypergraph)**:
- 超邊可連接任意數量頂點: `(A, B, C, D, ...)`
- 可表達高階關係

### 2. 為什麼需要超圖?

**場景示例**:

假設文本: "張三、李四、王五共同參與了項目 X"

**傳統圖表示**:
```
張三 --參與--> 項目X
李四 --參與--> 項目X
王五 --參與--> 項目X
```
問題: 丟失了"共同參與"的語義

**超圖表示**:
```
(張三, 李四, 王五, 項目X) --共同參與-->
```
優勢: 保留了完整的多方關係

### 3. Hyper-RAG 中的超圖使用

#### 低階超邊 (Low-order Hyperedge)

**定義** (operate.py:198-223):
```python
if record_attributes[0] == '"Low-order Hyperedge"':
    entities = [clean_str(record_attributes[i]) for i in range(1, entity_num)]
    # 可以是 2 個或更多實體
```

**示例**:
```
("Low-order Hyperedge"|Entity1|Entity2|description|keywords|strength)
```

#### 高階超邊 (High-order Hyperedge)

**定義** (operate.py:225-249):
```python
if record_attributes[0] == '"High-order Hyperedge"':
    entities = [clean_str(record_attributes[i]) for i in range(1, entity_num)]
    # 通常是 3+ 個實體的主題關聯
```

**示例**:
```
("High-order Hyperedge"|E1|E2|E3|E4|description|generalization|keywords|strength)
```

### 4. 超圖查詢策略

**實體擴散** (operate.py:744-824):
```python
# 1. 從實體 VDB 檢索相關實體
results = await entities_vdb.query(query, top_k=query_param.top_k)

# 2. 獲取這些實體的鄰居超邊
edges = await asyncio.gather(
    *[knowledge_hypergraph_inst.get_nbr_e_of_vertex(entity) for entity in entities]
)

# 3. 獲取一跳鄰居實體 (通過超邊連接)
all_one_hop_nodes = set()
for this_edges in edges:
    for edge_tuple in this_edges:
        all_one_hop_nodes.update(edge_tuple)  # 超邊中的所有實體

# 4. 統計文本片段與鄰居的關聯次數
for edge_tuple in edges:
    for e in edge_tuple:
        if c_id in neighbor_text_units[e]:
            relation_counts += 1  # 作為排序依據
```

**關係擴散** (operate.py:827-861):
```python
# 1. 從關係 VDB 檢索相關超邊
results = await relationships_vdb.query(keywords, top_k=top_k)

# 2. 獲取超邊數據和度數
edge_datas = await asyncio.gather(*[hypergraph.get_hyperedge(r['id_set']) for r in results])
edge_degrees = await asyncio.gather(*[hypergraph.hyperedge_degree(e['id_set']) for e in results])

# 3. 按度數和權重排序
edge_datas = sorted(edge_datas, key=lambda x: (x["rank"], x["weight"]), reverse=True)
```

### 5. 與傳統 Graph RAG 的對比

**Graph RAG** (graph_query 模式):
- 僅使用二元關係 (operate.py:1318-1319)
- 過濾掉 len(id_set) > 2 的超邊
- 適合表達簡單關聯

**Hyper RAG** (hyper_query 模式):
- 保留所有高階關係
- 可捕獲複雜的多方關聯
- 提供更豐富的上下文

---

## 最佳實踐

### 1. 選擇查詢模式

| 模式 | 適用場景 | 優點 | 缺點 |
|------|---------|------|------|
| `hyper` | 複雜問題,需要多層關聯 | 最完整的上下文 | 計算開銷最大 |
| `hyper-lite` | 簡單問題,主要查實體 | 較快,適合實體查詢 | 缺少關係視角 |
| `graph` | 對比實驗,傳統圖方法 | 與 KG 方法可比 | 丟失高階關係 |
| `naive` | Baseline,向量檢索 | 最快,無需圖 | 缺少結構化知識 |
| `llm` | 測試 LLM 能力 | 無檢索開銷 | 可能產生幻覺 |

### 2. 調優參數

**實體提取**:
```python
entity_extract_max_gleaning = 1  # 增加可提升召回,但變慢
entity_summary_to_max_tokens = 500  # 控制總結觸發閾值
```

**查詢檢索**:
```python
top_k = 60  # 增加可獲得更多上下文,但可能引入噪聲
max_token_for_text_unit = 4000  # 控制傳給 LLM 的上下文長度
cosine_better_than_threshold = 0.2  # 提高可過濾低相關結果
```

### 3. Prompt 工程

**選擇合適的範例**:
```python
# operate.py:421
example_prompt = PROMPTS["entity_extraction_examples"][3]  # 0-4 可選
```
建議: 根據領域選擇最相關的範例

**自定義實體類型**:
```python
# prompt.py:11
DEFAULT_ENTITY_TYPES = ["organization", "person", "geo", "event", "role", "concept"]
# 可根據領域添加: ["gene", "protein", "disease"] for 生物醫學
```

### 4. 向量化策略

**實體向量化** (operate.py:595-601):
```python
content = entity_name + description
# 優勢: 名稱和描述都參與檢索
```

**關係向量化** (operate.py:605-613):
```python
content = keywords + str(id_set) + description
# 優勢: 關鍵詞優先,實體集和描述補充
```

---

## 總結

Hyper-RAG 的核心創新總結:

1. **超圖建模**: 通過 `Low-order` 和 `High-order Hyperedge` 捕獲複雜關係
2. **分層關鍵詞**: 區分具體實體 (low-level) 和抽象主題 (high-level)
3. **雙重擴散**: 從實體擴散和關係擴散兩個方向檢索
4. **結構化上下文**: 以 CSV 表格形式提供 entities, relationships, sources
5. **多模查詢**: 支持 5 種查詢模式,適應不同場景

相比傳統 RAG:
- **更準確**: 結構化知識減少幻覺
- **更全面**: 超圖捕獲多方關係
- **更靈活**: 多種查詢模式可選

---

## 參考

- 核心代碼: `hyperrag/hyperrag.py`, `hyperrag/operate.py`, `hyperrag/prompt.py`
- 超圖庫: [Hypergraph-DB](https://github.com/iMoonLab/Hypergraph-DB)
- 向量庫: [nano-vectordb](https://github.com/gusye1234/nano-vectordb)
