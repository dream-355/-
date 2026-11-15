# 三维解剖数据来源与许可

本项目的人体分层解剖浏览功能使用以下公开数据进行本地化适配。解剖数据与项目业务代码分别遵循各自许可证。

## 男性参考人体

- 来源：BodyParts3D 4.0，Database Center for Life Science（DBCLS）。
- 模型：`isa_BP3D_4.0_obj_99.zip` 的浏览器优化版本，包含 2,234 个独立源网格和 3,432 个带名称的解剖概念。
- 许可：Creative Commons Attribution 4.0 International（CC BY 4.0）。
- 数据集：https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- 许可说明：https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html
- 适配：坐标转换为网页场景使用单位，按结构合并批次，保留源网格和名称层级，并使用 GPU 状态纹理控制显示与选择。

## 女性参考人体

- 来源：HuBMAP Human Reference Atlas，*3D Reference Organ Set for Female, v1.10*。
- 作者：Kristen Browne、Heidi Schlehlein。
- 基础数据：U.S. National Library of Medicine Visible Human Project。
- 许可：Creative Commons Attribution 4.0 International（CC BY 4.0）。
- 数据门户：https://humanatlas.io/3d-reference-library
- 说明：女性生殖结构来自女性参考数据；男性参考人体中的生殖结构不会载入女性模型。
- 补充数据：女性下肢肌肉来自 Andreassen 等发布的 Visible Human Female 数据集，许可同为 CC BY 4.0。
- 来源中的男性派生替代骨骼作为独立系统列出，默认关闭，不用于表示女性自身骨骼。
- 女性数据源缺少胃和食管网格。本项目补充 BodyParts3D 中不具性别特异性的胃和食管，并使用肝、胰、脾、双肾、小肠和膀胱七个共有腹部器官的边界中心做三轴线性配准。该补充结构在界面中与女性消化系统一起显示。
- 女性数据源的口腔、咽、喉细分不足。本项目从 BodyParts3D 补充非性别特异性的口腔、腭、舌、咽、喉软骨、会厌、声带、牙列和上段气管结构，并使用舌、软腭、杓状软骨、环状软骨、甲状软骨和气管六个共有局部标志完成坐标配准。

## 模型整理与中文标签参考

- 男女模型批次整理与网页加载结构参考 `slorksmo/Human-Atlas`，代码许可 MIT，解剖数据仍遵循 CC BY 4.0。
- 部分中文解剖名称参考 `lll888666/human-atlas-chinese`。
- HRA 女性数据中剩余 925 个英文结构名使用项目已配置的 DeepSeek 按严格 JSON 批量翻译，再由本地术语覆盖表校正左右、编号和常见临床器官名称。无法确认标准的专名保留规范缩写或中文音译。
- 应用层新增了简化粒子体表、透视控制、自由框选、中文结构检索和健康咨询联动。

## 使用边界

模型用于健康咨询中的位置描述与解剖学习，不用于确定诊断、手术规划或替代专业医疗判断。不同人体的器官大小、形态和位置存在正常差异。

“体态饱满度”只改变体表轮廓，用于辅助理解不同体态下的位置关系，不代表真实 BMI、体脂率或医学肥胖分级，也不会移动内部器官。
