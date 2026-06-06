@echo off
cd /d "C:\Users\Leand\OneDrive\Desktop\Projeto_Fit"
echo "--- Iniciando o script ---" > debug_log.txt 2>&1
"C:\Users\Leand\AppData\Local\Programs\Python\Python313\python.exe" api_server.py >> debug_log.txt 2>&1