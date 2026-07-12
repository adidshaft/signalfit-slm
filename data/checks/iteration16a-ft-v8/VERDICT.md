# Iteration 16A verdict — prefilter stop

`ft_v8_qwen3-1.7b + answer-check-v5` is **not eligible for owner review**.

The fresh 200-case run reaches 140/200 deterministic under `sf-gates-11`, with
s1 18/18, s2 19/19, and s3 196/200. It preserves all 30 re-pinned ft_v2 strict
protects, but loses two of the 16 prior strict-gain protects:
`advs-v1-000012` invents a derived `2.5 kg` value and
`ev1x-core2-000011` invents a `30 minutes` bedtime adjustment. Both fail x1.

The predeclared hard rule therefore stops the iteration before Phase 4. No
judging, fresh packet selection, sealed mapping, owner review, promotion,
fusion, quantization, or serving-default change is allowed. The iteration-15
packet and decision remain untouched; ft_v2 remains the model of record and
serving default.
