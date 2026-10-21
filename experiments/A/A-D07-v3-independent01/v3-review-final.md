# A-D07 v3独立修复复验结论

**结论：此前P1已修复，限定范围内的v3软件开发预演准备可以通过独立AI技术复核。** 原v0.2协议结果保持不变；本结论不构成人类批准、正式G2签字、真人结果或正式效果结论。未采集/读取任何真人记录，未修改主代码。

## P1关闭证据

`Pilot.plan_failure` 对两处规划阶段异常先计时、再FAILED并保存已接收答案、ledger、花费和事件；终止状态action直接返回，不能改答。已独立适配并重跑原反例，另检查no_feedback阶段失败：

- history × TIMEOUT / OSError：5份答案及证据保留，spent=10，completed为u_positive_int；状态FAILED，改成skip的重投递不改变任何持久内容。
- diagnosis × TIMEOUT / OSError：6份答案及证据保留，spent=11，completed保留；状态FAILED，改答无效。
- diagnosis的after成功、no_feedback随后TIMEOUT：同样FAILED且保留全部6份答案，不能因部分after结果而当作成功。
- 五场景均模拟增加3秒处理耗时，持久elapsed=3，末事件planning_failure；未丢处理时间。

五个独立反例断言全部通过，exit0。修复前反例仍保留，未覆盖成成功记录。

## 其余复核

正常全pass路线变化、完成前缀、费用10→11及同spent=11反事实、六个错题负例、单次作答、暂停/时钟异常/超时、HTTP答案隔离和token边界的更新回归均通过。公开view不含gate或掌握下界；第6题在before_plan封存之后呈现，仍不提供中间正确性进度。

新JS的accept按event_count及同计数elapsed拒绝陈旧响应，独立抽取该函数验证“较旧事件/时间不能覆盖已到终态，新事件仍接受”，通过；JS语法通过。普通暂停/恢复保留同stage DOM选项。上述为代码及隔离函数验证，不冒充真实浏览器验收。

未发现限定复核范围内仍需阻止开发预演的软件P1/P2。实际真人全pass、真实路线变化尚未发生于本审查，不能用夹具替代；真实结果若无变化仍须保留负结果，不加题追门。skip作为missing=true并保守记fail的实现含义须保持明确；不声称题间统计独立或模型已校准。

## 原始执行与输出

均在旧干净克隆 `tmp/independent-audit/` 写输出；PYTHONPATH指向获授权主树src/root，PYTHONDONTWRITEBYTECODE=1，Python使用授权解释器提升执行。

1. `python.exe -m pytest C:/CodeCompass/CodeCompass-A-D05/tests/A/test_pilot_d07_v3.py --basetemp tmp/independent-audit/v3-final -p no:cacheprovider -q`：**exit0，15 passed in 7.39s**。原始 `pytest-final.log`。
2. `python.exe tmp/independent-audit/v3-faults-final.py`：**exit0，5/5独立故障反例通过**。原始脚本、结果、日志：`v3-faults-final.py`、`v3-faults-final.json`、`v3-faults-final.log`。JSON逐场景绑定本次读取的六个实现/资产/题库文件SHA256。
3. `node --check C:/CodeCompass/CodeCompass-A-D05/app/A_D07_v3/app.js`：**exit0**；`node tmp/independent-audit/v3-js-final.cjs`：**exit0**。结果 `v3-js-final.json`。

题库此前独立oracle为6/6通过，报告 `bank-review.md`。本次不扩大重跑旧全套，不访问human目录。
