---
name: review-mota-route-balance
description: Review deterministic same-gem route-family costs for one generated mota floor.
---

# Review Mota Route Balance

Run the supplied `mota_route_balance.py` command before reviewing. Treat its route costs,
resource signatures, search status, and balance score as authoritative. Do not calculate
combat damage yourself and do not review unrelated layout or economy quality.

Pass only when every reported gem region has at least three distinct route families with
the same red/blue/green gem signature and `best_cost / third_cost >= 0.8`.

On failure, return concise encounter-owned issues. Identify the advantaged cheapest route,
the disadvantaged third route, their costs, and the pressure coordinates most suitable for
a minimal repair. Prefer a yellow/blue door swap, weak/strong monster swap, or monster-order
change around an existing gem. Never request moving a gem, wall, stair, key, potion, or tool.

Return only schema-valid review JSON. Do not edit files.
