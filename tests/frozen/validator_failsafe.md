**Enter this mode only where `taskProducesApplicationCode` is `false`.** That is the whole entry
condition, stated positively so that no other combination can satisfy it. The payload carries
`featureClass` and `taskProducesApplicationCode`, and it arrives on **every** per-task invocation —
including every task of a `"code"` feature, where it carries `true`. In every case other than an
explicit `false` — `true`, `"unknown"`, an unparseable payload, or no payload at all — run ordinary
validation and say in your verdict which case applied. Never select this mode yourself because a
diff looked empty.