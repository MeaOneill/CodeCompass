# A-D07 v3题库独立技术审查

范围仅限获授权的 `benchmarks/dev/A_D07_v3/bank.json` 与 `bank.sha256`，未访问真人记录、其他题库答案或其他worktree。审查输出位于旧干净克隆tmp。

结论：**6/6题实际执行与oracle_output及指定选项一致，且每题选项中仅一个匹配实际输出；未发现P1题库阻断问题。** bank文件SHA256与bank.sha256一致：`e7f0d1681183e923605d15c36ee7d01034976de71275adf6b41ccdc24442f709`。

六题分别检查新建迭代器与当前位置、耗尽后next默认值、自定义迭代器/StopIteration、旧式序列__getitem__/IndexError回退、callable/sentinel停止消费、__iter__返回值协议。它们在机制与代码结构上有实质差异，不是同题换数字。映射到宽泛的python.iterator_protocol可用于声明中的开发机制演示；该审核不证明教学构念效度、题目难度一致或统计独立。independence_scope对此限制有明确声明，independent=true须始终解释为非重复、一次独立作答项目资格，不可脱离该声明宣传统计独立。

仅核对固定题库自身；没有访问真人原题记录，不能另行证明与真人此前所见所有题内容不重复。实现需继续遵守已确定的六题封顶、不显示中间答案、第五题后封存before-plan后才呈现第六题。无需保证真人全pass。

执行：授权解释器提升运行 `python.exe tmp/independent-audit/bank-oracle.py`，exit0；直接compile/exec JSON解析后的每段代码，捕获stdout，与oracle_output及choices[answer]核对，并检查实际输出在choices中恰好出现一次。脚本不重写代码或规范化选择项来促成通过。

原始技术输出：`bank-oracle.py`、`bank-oracle.json`。这是独立AI技术复核，不是人类审批或正式G2签字。
