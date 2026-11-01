@echo off
rem Coletor de casa: deixe esta janela aberta para o site no Render conseguir buscar no KaBuM!
rem Usa o DATABASE_URL do arquivo .env (o mesmo banco do site).
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente Python pela primeira vez...
  python -m venv .venv || goto :erro
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :erro
)
echo Coletor ligado. Para desligar, feche esta janela ou aperte Ctrl+C.
".venv\Scripts\python.exe" -m app.collector
goto :eof
:erro
echo Nao foi possivel preparar o Python. Confira se o Python 3.12+ esta instalado.
pause
