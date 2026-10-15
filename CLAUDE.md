# Item-Manage-System

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore

## Design system

- `DESIGN.md`（repo root）是設計唯一權威：色彩／字型／間距／動態 tokens 與元件契約索引。任何 UI 或視覺變更前先讀它。
- 互動規格契約：`docs/plans/2026-10-15-next-iteration-roadmap.md` §五；設計價值觀摘要：`.impeccable.md`。
- 色彩 token 一律改 `apps/web/app/globals.css` ＋ `apps/web/tailwind.config.ts`；禁止在元件中硬編色碼。
