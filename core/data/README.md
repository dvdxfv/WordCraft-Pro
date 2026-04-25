# QA 词库数据

本目录存放错别字检查相关的纯文本词库。运行时由 `core/typo_lib.py` 按需加载。

## 文件清单

| 文件 | 说明 | 大小 | 是否默认启用 |
| --- | --- | --- | --- |
| `common_typos.tsv` | 项目维护的常见错别字词库（~550 条） | ~20 KB | ✅ 是 |
| `user_typos.tsv` | **用户自定义**错字（可选，会覆盖 common 中同 key 项） | - | ✅ 若存在则启用 |
| `sighan_pairs.txt` | SIGHAN 2015 衍生的 2-gram 错字对（仅供参考） | ~12 KB | ❌ opt-in |

## TSV 格式

```
错字<TAB>正字<TAB>说明（可空）
```

- `#` 开头或空白行会被忽略
- 每条词都必须满足：错字 ≠ 正字，且至少 2 个汉字（单字如 `的/地/得` 需要上下文语境，不放入词典避免刷屏）
- 说明可为空，会自动补为 `'错字'应为'正字'`

## 用户扩展

想为自己的项目加词？不要改 `common_typos.tsv`（升级时会冲突），
而是新建 `user_typos.tsv`：

```tsv
# 我的专用错字
专名错字A	专名正字A	领域专有名词
```

`user_typos.tsv` 不随项目分发，会在 `.gitignore` 中忽略。

## SIGHAN 词库（opt-in）

`sighan_pairs.txt` 由 SIGHAN 2015 拼写纠错语料衍生，格式为 `错字2字\t正字2字\t出现次数`。
默认**不启用**，因为 SIGHAN 中很多"错"形（如 `回复`、`习惯`、`多有`）本身
是合法词，仅在特定语境下错误，直接纳入会引发大量误报。

如需启用（作为低置信度参考），在配置中设置 `qa.typo_check.include_sighan = true`
或调用 `get_all_typos(include_sighan=True)`。

## 数据来源与许可

- `common_typos.tsv`：基于《现代汉语常见错别字手册》、《咬文嚼字》
  编者汇编、公文与学术写作常见错误，由本项目维护者手工整理。
- `sighan_pairs.txt`：衍生自 [shibing624/pycorrector](https://github.com/shibing624/pycorrector) Apache-2.0 许可下的
  `sighan2015_test.tsv` 语料。仅保留 2-gram 统计，不包含原始语料。
