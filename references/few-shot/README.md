# Bundled Mota Few-Shot Corpus

`corpus.json` is the reproducible reference input used by the tower generator by default.

It contains extracted design data for every non-sample main floor in two explicit style groups:

- `traditional`: 寒云谷2103, 溯, CCW.
- `red_sea`: 红蓝的记忆2.10, 星月神话 2.10.3, dist, 剑阁2.9, 出塞V2.10.0.

- Original floor map matrices and the project-local tile legend required to decode them.
- Structural topology maps, compressed route graphs, and up to three candidate routes.
- Approximate resource reachability order and the door/enemy/hazard sequence before each resource.
- The `enemys.js` records actually used on each selected floor.
- Relevant initial hero and global gem/potion values from `data.js`.

The bundle intentionally excludes source events, scripts, saves, media, and unused floors. Source-project numeric tile codes are local identifiers and must never be copied directly into generated maps.

At runtime, `few_shot_selection.json` records a deterministic split for every floor and stage. Selection is strict by requested tower style and never falls back to the other group. With the default count of three, the generator receives one shared anchor plus two generator-only construction examples; the reviewer receives the same anchor plus two holdout examples that were not shown to the generator. Reviewer payloads also carry stage-specific contrastive rejection cases. The split is computed once and remains fixed across repair retries. If a size-specific corpus is too small for a larger requested count, the plan records `reviewer_fallback` reuse explicitly instead of silently reducing the reviewer input count.

Traditional per-floor layout generation and review use only the curated floors 寒云谷2103 MT2/3/4/7/8/11/12 and 溯 MT2/3/5/6/7/8/9. Prompt projection normalizes the specified debuff cures, money pickups, equipment, green/yellow gems, and red doors/keys into the red/blue-gem and blue-key economy without modifying the stored corpus. This curation applies to layout stages only; enemy-table few-shot selection still uses the full same-style corpus. Red-sea selection and projections are unchanged.

The enemy-table generator and its dedicated reviewer also receive separate monster-reference projections from this selection plan. Those examples calibrate relative roles and tier progression only; projected hero bands and the confirmed tower resource policy define numeric scale.

To rebuild after updating the local reference projects:

```bash
python3 scripts/export_mota_few_shot_bundle.py \
  --source-root "$HOME/Documents/例子"
```

The exporter strips absolute local paths and recalculates the corpus fingerprint. Any fingerprint change invalidates old generation caches.
