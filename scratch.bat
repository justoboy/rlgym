@echo off
cd /d D:\RLBotTraining\rlgym
git add -A
git commit -m "T10/T11: Mutator parity (widened GameConfig pass-through) + native game modes (mode-aware multi-arena engine, native goal callback edge, unified reset_kickoff, hsInfo carry)"
git push origin main
git log --oneline -5
