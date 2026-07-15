---
name: repair-mota-route-balance
description: Minimally repair doors and monster placement using deterministic route-balance feedback.
---

# Repair Mota Route Balance

Repair only the supplied encounter output. Preserve every wall, stair, gem, key, potion,
tool, event, floor field, exact door quota, and total enemy-count constraint.

Use the compact route report as authoritative. Raise cost on the cheapest advantaged route
or lower cost on the expensive third route with the smallest legal change. Prefer:

1. Swap one yellow and blue door across the two routes.
2. Swap a weak and strong monster across the two routes.
3. Reorder existing monsters so a threshold monster occurs before a gem on the cheap route
   or after a gem on the expensive route.
4. Replace one route monster with a slightly stronger/weaker allowed monster.
5. Move a legal zone/repulse role between existing encounter positions.

Change at most four cells. Preserve enemy non-adjacency and zone/repulse geometry. Do not
edit monster stats or `enemys.js` in this basic flow. Do not create empty-ground detours and
do not rebuild topology or economy. Red doors have no balance weight and must stay outside
the three compared access families. Return the complete repaired floor wrapper only.
