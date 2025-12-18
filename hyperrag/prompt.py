GRAPH_FIELD_SEP = "<SEP>"

PROMPTS = {}

PROMPTS["DEFAULT_LANGUAGE"] = '繁體中文'
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = " | "
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "\n"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
PROMPTS["process_tickers"] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# 修改 1: 定義適合 IT 技術文件的實體類型
PROMPTS["DEFAULT_ENTITY_TYPES"] = ["Component", "Role", "Artifact", "Action", "Parameter", "Error", "Concept"]

# 修改 2: 針對 AD FS 技術手冊的實體提取 Prompt
PROMPTS["entity_extraction"] = """-角色-
你是一位資深的系統架構師與知識圖譜工程師。
你的目標是從《CCSP AD FS Installation and Configuration Guide》中提取結構化的技術知識，構建一張「系統部署與維運圖譜」。

-任務目標-
將非結構化的技術文件轉化為關聯性強的節點與邊。
**核心要求：實體名稱 (ID) 必須保留原文（通常是英文），但在描述欄位請使用繁體中文摘要。**

-輸出語言-
{language} (實體 ID 保持英文，描述使用繁體中文)

-實體提取規則 (嚴格遵守)-

1. **專有名詞精確化**：
   - 實體名稱應使用文件中最正式的寫法 (如 "Web.config" 而非 "設定檔")。
   - 區分上下文：若文件區分了 "CCSP AD FS" 與 "Third-Party AD FS"，請務必在命名上區隔。

2. **實體類型定義 (Schema)**：
   * **Component (組件)**: 軟體系統、服務或工具 (如：AD FS, TouchPoint, IIS, Server Manager)。
   * **Role (角色)**: 架構中的角色或使用者身分 (如：Identity Provider (IdP), Relying Party (RP), Administrator)。
   * **Artifact (物件)**: 檔案、憑證、協議或數據對象 (如：Web.config, SSL Certificate, SAML Token, Metadata)。
   * **Action (操作)**: 具體的部署、設定或驗證動作 (如：Install, Configure, Import Certificate, Restart Service)。
   * **Parameter (參數)**: 具體的設定鍵值或屬性 (如：thumbprint, audienceUri, realm)。
   * **Error (錯誤)**: 具體的錯誤訊息或故障現象 (如：The issuer of the security token was not recognized)。
   * **Concept (概念)**: 抽象的技術概念或協議 (如：Claims-based Authentication, SSO, Trust Relationship)。

-步驟-

1. **識別與定義**：
   提取關鍵技術實體。
   提取資訊：
   - entity_name: 保持英文原文 (除非原文即中文)。
   - entity_type: 所屬類型。
   - entity_description: 用繁體中文簡述其功能或定義。
   - additional_properties: 相關屬性 (如: Required/Optional, Default Value)。
   格式：("Entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>{tuple_delimiter}<additional_properties>)

2. **構建低階關係 (Low-order Relationships)**：
   找出明確的技術關聯。重點關係包括：DEPENDS_ON (依賴), CONFIGURES (配置), CONTAINS (包含), SOLVES (解決錯誤), TRUSTS (信任)。
   提取資訊：
   - entities_pair: 實體對。
   - low_order_relationship_description: 解釋關係 (例如：Web.config 包含 issuerNameRegistry 設定)。
   - low_order_relationship_keywords: 關係標籤 (如：REQUIRES, CONFIGURES, CAUSES)。
   - low_order_relationship_strength: 數值 (1-10，依賴性越強越高)。
   格式：("Low-order Hyperedge"{tuple_delimiter}<entity_name1>{tuple_delimiter}<entity_name2>{tuple_delimiter}<low_order_relationship_description>{tuple_delimiter}<low_order_relationship_keywords>{tuple_delimiter}<low_order_relationship_strength>)

3. **提取高階關鍵詞 (High-level Keywords)**：
   總結該段落涉及的技術主題。
   格式：("High-level keywords"{tuple_delimiter}<keyword1, keyword2, ...>)

4. **構建操作情境 (High-order Hyperedges)**：
   將多個實體組合成一個完整的「操作流程」或「故障排除劇本」。
   (Context + Component + Action + Result)
   提取資訊：
   - entities_set: 關聯實體集。
   - high_order_relationship_description: 完整流程描述 (例如：為了啟用 SAML，管理員需在 Web.config 設定指紋)。
   - high_order_relationship_generalization: 一句話策略總結 (如「SAML 憑證信任設定流程」)。
   - high_order_relationship_keywords: 流程標籤 (如：Deployment, Troubleshooting)。
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

# 修改 3: 提供技術文件專屬的 Few-Shot 範例
PROMPTS["entity_extraction_examples"] = [
    """範例1 (配置與依賴關係):

文本:
「To configure TouchPoint authentication, the Administrator must edit the Web.config file. Specifically, verify that the 'thumbprint' value in the 'issuerNameRegistry' section matches the AD FS signing certificate.」

################
輸出:
("Entity"{tuple_delimiter}TouchPoint{tuple_delimiter}Component{tuple_delimiter}需要進行驗證設定的目標應用程式。{tuple_delimiter}狀態: Target System){record_delimiter}
("Entity"{tuple_delimiter}Administrator{tuple_delimiter}Role{tuple_delimiter}執行設定更改的使用者。{tuple_delimiter}權限: Elevated){record_delimiter}
("Entity"{tuple_delimiter}Web.config{tuple_delimiter}Artifact{tuple_delimiter}TouchPoint 的主要 XML 設定檔。{tuple_delimiter}格式: XML){record_delimiter}
("Entity"{tuple_delimiter}thumbprint{tuple_delimiter}Parameter{tuple_delimiter}用於識別憑證的唯一指紋值。{tuple_delimiter}重要性: Critical){record_delimiter}
("Entity"{tuple_delimiter}issuerNameRegistry{tuple_delimiter}Parameter{tuple_delimiter}Web.config 中定義受信任發行者的區塊。{tuple_delimiter}父層: Web.config){record_delimiter}
("Entity"{tuple_delimiter}AD FS signing certificate{tuple_delimiter}Artifact{tuple_delimiter}AD FS 用來簽署 Token 的安全憑證。{tuple_delimiter}來源: AD FS){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}Web.config{tuple_delimiter}TouchPoint{tuple_delimiter}Web.config 控制 TouchPoint 的行為。{tuple_delimiter}CONFIGURES{tuple_delimiter}10){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}Web.config{tuple_delimiter}issuerNameRegistry{tuple_delimiter}Web.config 檔案包含 issuerNameRegistry 區段。{tuple_delimiter}CONTAINS{tuple_delimiter}9){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}thumbprint{tuple_delimiter}AD FS signing certificate{tuple_delimiter}設定檔中的指紋必須與實際憑證相符。{tuple_delimiter}MUST_MATCH{tuple_delimiter}10){record_delimiter}
("High-level keywords"{tuple_delimiter}Authentication Config, Certificate Trust, XML Editing){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}TouchPoint{tuple_delimiter}Web.config{tuple_delimiter}thumbprint{tuple_delimiter}AD FS signing certificate{tuple_delimiter}這是一個建立信任關係的流程。管理員透過將 AD FS 簽章憑證的指紋填入 TouchPoint 的 Web.config 中，來授權 AD FS 作為身分提供者。{tuple_delimiter}憑證信任設定流程{tuple_delimiter}Configuration, Security{tuple_delimiter}9){completion_delimiter}
#############################""",
    """範例2 (故障排除與錯誤):

文本:
「If users encounter the error 'The issuer of the security token was not recognized', it usually indicates a mismatch between the Federated Metadata and the local configuration. You should run the 'Update-AdfsRelyingPartyTrust' PowerShell cmdlet to fix this.」

################
輸出:
("Entity"{tuple_delimiter}The issuer of the security token was not recognized{tuple_delimiter}Error{tuple_delimiter}當系統無法驗證 Token 發行者時顯示的錯誤訊息。{tuple_delimiter}類型: Authentication Failure){record_delimiter}
("Entity"{tuple_delimiter}Federated Metadata{tuple_delimiter}Artifact{tuple_delimiter}包含聯盟夥伴資訊的 XML 文件。{tuple_delimiter}用途: Exchange Info){record_delimiter}
("Entity"{tuple_delimiter}Update-AdfsRelyingPartyTrust{tuple_delimiter}Action{tuple_delimiter}用於更新信賴憑證者信任設定的 PowerShell 指令。{tuple_delimiter}工具: PowerShell){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}Federated Metadata{tuple_delimiter}The issuer of the security token was not recognized{tuple_delimiter}Metadata 不一致是導致此錯誤的常見原因。{tuple_delimiter}CAUSES{tuple_delimiter}8){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}Update-AdfsRelyingPartyTrust{tuple_delimiter}The issuer of the security token was not recognized{tuple_delimiter}執行此更新指令通常可以解決該發行者無法識別的錯誤。{tuple_delimiter}SOLVES{tuple_delimiter}10){record_delimiter}
("High-level keywords"{tuple_delimiter}Troubleshooting, PowerShell, Metadata Sync){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}The issuer of the security token was not recognized{tuple_delimiter}Update-AdfsRelyingPartyTrust{tuple_delimiter}Federated Metadata{tuple_delimiter}這是一個故障排除劇本。當憑證或 Metadata 過期導致信任錯誤時，使用 PowerShell 指令強制更新信任關係。{tuple_delimiter}Metadata 同步修復流程{tuple_delimiter}Troubleshooting, Maintenance{tuple_delimiter}9){completion_delimiter}
#############################"""
]

# 修改 4: 調整實體描述總結 Prompt (側重功能定義)
PROMPTS[
    "summarize_entity_descriptions"
] = """你是一個技術文件專家。
你的任務是將關於實體「{entity_name}」的多個描述片段，整合成一個精確的技術定義。

重點要求：
1. **去重與整合**：合併重複的技術細節。
2. **功能定義 (What)**：它是什麼？(如：設定檔、服務、參數)。
3. **操作上下文 (How)**：它通常在什麼步驟被使用？與哪些組件互動？
4. **保留術語**：請保留關鍵的英文技術術語。

#######
-資料-
實體: {entity_name}
原始描述: {description_list}
#######
輸出 (繁體中文):
"""

PROMPTS[
    "summarize_entity_additional_properties"
] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one entity and a list of its additional properties.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the additional properties.
If the provided additional properties are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person.
#######
-Warning!!!-
The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
but they are only part of literary works, popular science knowledge or domain data, 
which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
Please carefully identify and screen the legality of the content.
#######
-Data-
Entity: {entity_name}
Additional Properties List: {additional_properties_list}
#######
Output:
"""

# 修改 5: 調整關係描述總結 Prompt (側重操作邏輯)
PROMPTS[
    "summarize_relation_descriptions"
] = """你是一個系統整合專家。
給定實體集 {relation_name}，請總結它們之間的技術關聯。

重點要求：
1. **識別邏輯**：明確指出依賴關係 (Dependency)、數據流向 (Data Flow) 或因果關係 (Cause-Effect)。
2. **規則化**：如果這是配置步驟，請轉化為「若 A 則 B」或「為了 A 必須 B」。
3. **故障排除價值**：如果包含錯誤與解法，請明確指出「症狀」與「解藥」。

#######
-資料-
關係描述: {relation_description_list}
#######
輸出 (繁體中文):
"""

PROMPTS[
    "summarize_relation_keywords"
] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given a set of entities, and a list of keywords describing the relations between the entities.
Please select some important keywords you think from the keywords list.   Make sure that these keywords summarize important events or themes of entities, including but not limited to [Main idea, major concept, or theme].  
(Note: The content of keywords should be as accurate and understandable as possible, avoiding vague or empty terms).
#######
-Warning!!!-
The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
but they are only part of literary works, popular science knowledge or domain data, 
which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
Please carefully identify and screen the legality of the content.
#######
-Data-
Entity Set: {relation_name}
Relation Keywords List: {keywords_list}
#######
Format these keywords separated by ',' as below:
{{keyword1,keyword2,keyword3,...,keywordN}}
Output:
"""

PROMPTS[
    "entity_continue_extraction"
] = """MANY entities were missed in the last extraction.  Add them below using the same format:
"""

PROMPTS[
    "entity_if_loop_extraction"
] = """It appears some entities may have still been missed.  Answer YES | NO if there are still entities that need to be added.
"""

# 修改 6: 調整關鍵詞提取 Prompt (側重技術術語)
PROMPTS["keywords_extraction"] = """---角色---
你是一個「技術支援檢索專家」。將使用者的自然語言問題轉化為針對 AD FS 安裝手冊的檢索關鍵詞。

---目標---
輸出 JSON 格式，包含：
1. **high_level_keywords**: 核心技術概念、模組名稱 (如：SAML, Certificate, Troubleshooting, Claims)。
2. **low_level_keywords**: 具體檔案名、錯誤碼、指令、參數 (如：Web.config, thumbprint, 401 Error, Set-AdfsProperties)。

---範例---
查詢: "為什麼憑證會出現錯誤？"
輸出: {{
  "high_level_keywords": ["Certificate Management", "Trust Relationship", "Troubleshooting"],
  "low_level_keywords": ["SSL Certificate", "Signing Certificate", "Error", "Thumbprint"]
}}

---實際查詢---
{query}
"""

PROMPTS["rag_response"] = """---角色---
你是一個熟悉 AD FS 與 CCSP 架構的技術支援顧問。

---目標---
基於提供的知識圖譜資料回答使用者的技術問題。
請將重點放在「具體操作步驟」、「配置參數確認」或「故障排除流程」。
若涉及指令或設定檔修改，請務必精確引用。

---資料表---
{context_data}

---格式---
{response_type}
"""

PROMPTS["fail_response"] = "Sorry, I'm not able to provide an answer to that question."

PROMPTS["rag_define"] = """
Through the existing analysis, we can know that the potential keywords or theme in the query are:
{{ {ll_keywords} | {hl_keywords} }}
Please refer to keywords or theme information, combined with your own analysis, to select useful and relevant information from the prompts to help you answer accurately.
Attention: Don't brainlessly splice knowledge items! The answer needs to be as accurate, detailed, comprehensive, and convincing as possible!
"""

PROMPTS["naive_rag_response"] = """You're a helpful assistant
Below are the knowledge you know:
{content_data}
---
If you don't know the answer or if the provided knowledge do not contain sufficient information to provide an answer, just say so. Do not make anything up.
Generate a response of the target length and format that responds to the user's question, summarizing all information in the input data tables appropriate for the response length and format, and incorporating any relevant general knowledge.
If you don't know the answer, just say so. Do not make anything up.
Do not include information where the supporting evidence for it is not provided.
---Target response length and format---
{response_type}
"""