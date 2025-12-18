GRAPH_FIELD_SEP = "<SEP>"

PROMPTS = {}

PROMPTS["DEFAULT_LANGUAGE"] = '繁體中文'
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = " | "
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "\n"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
PROMPTS["process_tickers"] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

PROMPTS["DEFAULT_ENTITY_TYPES"] = ["Value", "Preference", "DefenseMechanism", "CommunicationStyle", "RedFlag", "Context", "Action"]

PROMPTS["entity_extraction"] = """-角色-
你是一位精通深度心理學、博弈論與社交動力學的策略顧問。
你的目標是協助使用者構建一張「社交戰略知識圖譜」，用於精準的人際攻略（如戀愛追求、談判）。

-任務目標-
從文本中提取具備「心理動力」與「戰略意義」的實體，並構建情境化的超邊（Hyperedges）。
**核心要求：你需要將「具體事件」轉化為「抽象概念」。不要提取流水帳。**

-輸出語言-
{language}

-實體提取規則 (嚴格遵守)-

1. **名詞化 (Nominalization)**：實體名稱必須是**名詞**或**名詞短語**。
   - 錯誤： "覺得男生應該要主動買單" (句子)
   - 正確： "傳統性別角色" (概念)
   - 錯誤： "喜歡去聽NewJeans演唱會" (行為描述)
   - 正確： "K-Pop文化" 或 "現場展演體驗" (愛好/價值觀)

2. **歸納法 (Generalization)**：如果文本描述具體事件，請提取其背後的**心理模式**。
   - 文本："每次吵架他就躲回房間打電動不理人"
   - 提取實體："冷暴力" (DefenseMechanism) 或 "迴避型依附" (Pattern)
   - *不要*提取："打電動" (除非重點是遊戲本身)

3. **實體類型定義**：
   * **Value (價值觀)**: 驅動決策的核心信念 (如：公平性、財務安全感、承諾)。
   * **Preference (偏好)**: 帶有強烈情感色彩的喜好 (如：老宅、儀式感、智性交流)。
   * **DefenseMechanism (防禦機制)**: 保護自我、迴避衝突的模式 (如：自嘲、轉移焦點、理智化)。
   * **CommunicationStyle (溝通風格)**: 互動模式 (如：辯論模式、情感宣洩、暗示性溝通)。
   * **RedFlag (地雷)**: 厭惡點或反社會特質 (如：邊界感缺失、控制狂、情緒勒索)。
   * **Context (情境)**: 觸發特定心理狀態的場景 (如：高壓狀態、社交能量耗盡時)。**禁止提取單純的時間地點**。
   * **Action (行為模式)**: 反映性格的慣性動作 (如：許願/期待心理、瘋狂工作)。

-步驟-

1. **識別與概念化**：
   從文本中識別心理訊號，並將其轉化為上述的高階實體。
   提取資訊：
   - entity_name: 概念化後的名稱。
   - entity_type: 所屬類型。
   - entity_description: 該實體在文本中的具體表現，以及對應對策略的意義。
   - additional_properties: 強度 (High/Medium/Low)、正負向 (Positive/Negative)。
   格式：("Entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>{tuple_delimiter}<additional_properties>)

2. **構建低階關係 (Low-order Relationships)**：
   找出明確的 (源實體, 目標實體) 對，重點關注「心理因果」。
   提取資訊：
   - entities_pair: 實體對。
   - low_order_relationship_description: 解釋動力學 (例如：情境A 觸發了 防禦機制B)。
   - low_order_relationship_keywords: 關係標籤 (如：觸發、抑制、補償、衝突)。
   - low_order_relationship_strength: 數值 (1-10)。
   格式：("Low-order Hyperedge"{tuple_delimiter}<entity_name1>{tuple_delimiter}<entity_name2>{tuple_delimiter}<low_order_relationship_description>{tuple_delimiter}<low_order_relationship_keywords>{tuple_delimiter}<low_order_relationship_strength>)

3. **提取高階關鍵詞 (High-level Keywords)**：
   總結對象的「戀愛人格」、「依附類型」或「核心吸引力」。
   格式：("High-level keywords"{tuple_delimiter}<keyword1, keyword2, ...>)

4. **構建戰術劇本 (High-order Hyperedges / N-ary relations)**：
   將多個實體組合成一個完整的互動劇本 (Context + Trigger + Response + Outcome)。
   這將回答：「在這種情況下，千萬別做什麼，應該做什麼」。
   提取資訊：
   - entities_set: 關聯實體集。
   - high_order_relationship_description: 戰術劇本描述。
   - high_order_relationship_generalization: 一句話策略總結 (如「破解防禦機制的安撫策略」)。
   - high_order_relationship_keywords: 戰術標籤。
   - high_order_relationship_strength: 顯著程度 (1-10)。
   格式：("High-order Hyperedge"{tuple_delimiter}<entity1>{tuple_delimiter}<entity2>{tuple_delimiter}<entityN>{tuple_delimiter}<high_order_relationship_description>{tuple_delimiter}<high_order_relationship_generalization>{tuple_delimiter}<high_order_relationship_keywords>{tuple_delimiter}<high_order_relationship_strength>)

5. 輸出結果列表，使用 **{record_delimiter}** 分隔。

6. 結束時輸出 {completion_delimiter}。

######################
-範例-
######################
{examples}
######################
-實際資料-
######################
文本: {input_text}
######################
輸出:
"""

PROMPTS["entity_extraction_examples"] = [
    """範例1 (將具體行為轉化為概念):

文本:
「NEWJEANS五寶也能來高雄開一場盛大的演唱會就好了，好想在台下跟著大家一起尖叫。不過如果男朋友這時候在旁邊一直滑手機潑冷水，我真的會直接翻臉走人。」

################
輸出:
("Entity"{tuple_delimiter}K-Pop文化{tuple_delimiter}Preference{tuple_delimiter}對特定韓國流行團體及偶像文化的熱愛與認同。{tuple_delimiter}強度: High, 正向){record_delimiter}
("Entity"{tuple_delimiter}集體狂歡體驗{tuple_delimiter}Value{tuple_delimiter}重視在大型場域中與人群共享當下情緒能量的體驗 (Collective Effervescence)。{tuple_delimiter}強度: High){record_delimiter}
("Entity"{tuple_delimiter}冷漠/掃興行為{tuple_delimiter}RedFlag{tuple_delimiter}在伴侶情緒高漲時表現出不關注或潑冷水的行為，被視為缺乏情感共鳴。{tuple_delimiter}強度: High){record_delimiter}
("Entity"{tuple_delimiter}斷絕連結{tuple_delimiter}Action{tuple_delimiter}面對情感需求被忽視時的極端反應（翻臉走人），顯示出邊界感強烈且容忍度低。{tuple_delimiter}類型: 衝突反應){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}K-Pop文化{tuple_delimiter}集體狂歡體驗{tuple_delimiter}對K-Pop的喜愛具體化為對現場「共感」體驗的追求，這不是單純聽歌，而是社交儀式。{tuple_delimiter}價值觀體現{tuple_delimiter}9){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}冷漠/掃興行為{tuple_delimiter}斷絕連結{tuple_delimiter}當核心興趣（K-Pop/狂歡）被伴侶的冷漠態度（RedFlag）否定時，會直接觸發關係中斷（Action）。{tuple_delimiter}地雷引爆{tuple_delimiter}10){record_delimiter}
("High-level keywords"{tuple_delimiter}情緒價值導向, 儀式感, 情感共鳴需求, 果斷止損){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}K-Pop文化{tuple_delimiter}集體狂歡體驗{tuple_delimiter}冷漠/掃興行為{tuple_delimiter}這是一個「熱情保護機制」。當對象沈浸在核心愛好中，伴侶必須提供情緒支持或至少保持尊重。任何形式的「潑冷水」都會被視為對其價值觀的否定，導致關係危機。策略：即使不懂K-Pop，也要參與那份興奮感。{tuple_delimiter}核心愛好維護策略{tuple_delimiter}情緒同頻, 避免掃興, 參與感{tuple_delimiter}9){completion_delimiter}
#############################""",
    """範例2 (識別防禦機制):

文本:
大家誇我策展厲害，我只覺得是運氣好。比起虛偽的酒會，我寧願在路邊攤喝啤酒罵髒話討論未來。

################
輸出:
("Entity"{tuple_delimiter}自我貶抑{tuple_delimiter}DefenseMechanism{tuple_delimiter}面對讚美時習慣性歸因於運氣，以降低他人期待或避免被捧殺。{tuple_delimiter}類型: 冒名頂替症候群){record_delimiter}
("Entity"{tuple_delimiter}形式主義{tuple_delimiter}RedFlag{tuple_delimiter}對客套、虛偽社交場合的強烈排斥。{tuple_delimiter}強度: Medium){record_delimiter}
("Entity"{tuple_delimiter}真實感交流{tuple_delimiter}Preference{tuple_delimiter}偏好去精緻化、無修飾的深度溝通場景（如路邊攤）。{tuple_delimiter}類型: 社交偏好){record_delimiter}
("Entity"{tuple_delimiter}事業願景{tuple_delimiter}Value{tuple_delimiter}即使在放鬆狀態下仍關注專業發展，顯示其對工作的熱情是內在驅動力。{tuple_delimiter}強度: High){record_delimiter}
("High-level keywords"{tuple_delimiter}真誠性, 冒名頂替現象, 去階級化, 理想主義){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}自我貶抑{tuple_delimiter}形式主義{tuple_delimiter}真實感交流{tuple_delimiter}對象無法接受傳統的「商業互吹」，這會觸發其自我貶抑的防禦。要建立連結，必須打破形式主義，創造「真實感交流」的情境（如私下聚會），才能讓他放下防禦談論願景。{tuple_delimiter}卸下心防的社交路徑{tuple_delimiter}去客套, 真誠對話{tuple_delimiter}8){completion_delimiter}
#############################"""
]

PROMPTS[
    "summarize_entity_descriptions"
] = """你是一個專業的心理側寫師。
你的任務是將關於實體「{entity_name}」的多個描述片段，整合成一個深度的心理畫像。

重點要求：
1. **去重與整合**：合併重複資訊，解決表面矛盾（用「情境依賴」解釋）。
2. **動機解碼 (Why)**：不要只說他做了什麼，要解釋**這代表什麼心理需求**。
   - 例如：不要只寫「喜歡去演唱會」，要寫「透過大型展演尋求集體共鳴與情緒釋放」。
3. **戰術價值**：這對「如何與此人相處」有什麼指導意義？

#######
-資料-
實體: {entity_name}
原始描述: {description_list}
#######
輸出 (第三人稱):
"""

PROMPTS[
    "summarize_entity_additional_properties"
] = """你是一個數據分析師。請將以下屬性列表整合成精煉的描述。
重點關注：強度 (Intensity)、頻率 (Frequency)、情緒極性 (Polarity) 以及是否隨情境變化。

#######
-資料-
實體: {entity_name}
屬性列表: {additional_properties_list}
#######
輸出:
"""

PROMPTS[
    "summarize_relation_descriptions"
] = """你是一個關係動力學專家。
給定實體集 {relation_name}，請總結它們之間的互動模式。

重點要求：
1. **識別機制**：明確指出「觸發點 (Trigger)」、「反應 (Reaction)」與「調節變數 (Moderator)」。
2. **規則化**：將描述轉化為 IF-THEN 的行為規則。
   - 例如：IF 感到壓力 THEN 啟動 迴避機制。
3. **整合矛盾**：如果描述有衝突，請找出讓它們共存的特定條件。

#######
-資料-
關係描述: {relation_description_list}
#######
輸出:
"""

PROMPTS[
    "summarize_relation_keywords"
] = """從以下列表中篩選並生成最具「戰略洞察力」的關鍵詞。
優先選擇：心理學術語 (如：焦慮依附)、行為模式 (如：被動攻擊)、社交策略 (如：情緒價值)。
去除：過於通用的詞彙。

#######
-資料-
關鍵詞列表: {keywords_list}
#######
格式：{{keyword1,keyword2,...}}
輸出:
"""

PROMPTS[
    "entity_continue_extraction"
] = """上次提取可能未完整。請繼續提取剩餘的具體實體或關係，保持相同格式：
"""

PROMPTS[
    "entity_if_loop_extraction"
] = """是否還有具備戰略價值的實體或關係被遺漏？(回答 是 或 否)
"""

PROMPTS["fail_response"] = "抱歉，根據現有資料無法回答。"

PROMPTS["rag_response"] = """---角色---
你是一個社交策略顧問，根據提供的知識圖譜資料回答問題。

---目標---
基於資料表回答使用者問題。如果資料不足，請明確說明。
請將重點放在「如何應用這些資訊」來制定社交或追求策略。

---資料表---
{context_data}

---格式---
{response_type}
"""

PROMPTS["keywords_extraction"] = """---角色---
你是一個「查詢意圖轉譯器」。將使用者的自然語言問題轉化為知識圖譜的檢索關鍵詞。

---目標---
輸出 JSON 格式，包含：
1. **high_level_keywords**: 心理概念、戰略主題 (如：依附類型、防禦機制、價值觀)。
2. **low_level_keywords**: 具體名詞、場景、愛好 (如：K-Pop、酗酒、冷戰)。

---範例---
查詢: "他生氣的時候會怎樣？"
輸出: {{
  "high_level_keywords": ["衝突處理", "防禦機制", "情緒調節", "溝通模式"],
  "low_level_keywords": ["冷戰", "沈默", "封鎖", "吵架"]
}}

---實際查詢---
{query}
"""

PROMPTS["naive_rag_response"] = """你是有用的助手。
基於以下知識回答問題：
{content_data}

如果不知道，請直說。
格式：{response_type}
"""

PROMPTS["rag_define"] = """
潛在關鍵詞：{{ {ll_keywords} | {hl_keywords} }}
請利用這些關鍵詞在圖譜中檢索相關資訊，並構建有說服力的策略建議。
"""