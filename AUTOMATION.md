# AUTOMATION.md — copilot-instruction-eval

大ゴール: AIによる全自動開発の実現。人間より圧倒的に効率的に。(fleet共通)

## 発火 (Driver)
- crontab: 0本(2026-09-15 実測・crontab全74行=実行50行との突合・当repoへの言及0)
- GitHub Actions: 3本(ci.yml, quality-check.yml, release.yml / 2026-09-15 実測列挙)

## Kill Switch
`gh workflow disable ci.yml quality-check.yml release.yml`

## Status
2026-09-15 初版整備(実測: crontab突合・workflow列挙)。fleet台帳: /home/jinno/business_notes/AUTOMATION.md
