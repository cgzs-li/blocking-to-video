# JSON计划格式

参考 [虚构双人计划](../examples/two-person-plan.json)。它用于演示结构检查，所列图片未随仓库提供，不能直接生成完整视频。

| 字段 | 规则 |
|---|---|
| characters | 本场角色ID数组，无重复 |
| assets | 每项有id、role、file；identity还需character。每角色一份身份图；本场scene、blocking、camera各一份，额外参考可用supplement角色 |
| cameras | 当前俯视机位图已定义的机位ID数组 |
| dialogue | 原台词有序数组，每项id、speaker、text；跨镜拆句沿用同一id |
| segments | 有序片段数组，见下 |

每段包含id、characters（参与角色）、input_assets（实际要求绑定的资产ID）、duration（秒）、entry_state、exit_state、shots。

每镜包含id、start/end（相对本段的秒数）、camera、blocking（角色ID到图上点号）、speech数组。无对白时speech为`[]`。

每条speech包含line_id、speaker、text、start/end（相对本镜的秒数）、mode（`on`画内或`off`画外）。说话窗口默认顺序且不重叠；本检查器针对顺序对白，不用于交叠争吵。若题材需要多人同时说话，先扩展明确的数据约定和检查，不静默删去重叠对白。

所有台词碎片按影片顺序拼接，与原台词比较时只忽略空白，不忽略标点/数字。每段输入要求覆盖参与角色身份及三类共享核心资产。图解ID是否真实出现在图中需目视检查，脚本只验证字段和映射，不读取图片内容。

资产路径可指向当前项目实际文件；`--check-files`按JSON所在目录解析相对路径。分享计划前，将私人绝对路径替换为可交付的相对路径，并确认有权共享对应图片。
