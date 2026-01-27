@echo off
cd /d D:\Workspace\Toss\hankki\backend

call toss\Scripts\activate

mkdir logs 2>nul

python manage.py seed_foodsafety --limit 30 >> logs\seed_foodsafety.log 2>&1

echo DONE %date% %time% >> logs\seed_foodsafety.log
