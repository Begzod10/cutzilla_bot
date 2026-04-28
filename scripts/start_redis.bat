@echo off
cd /d "%~dp0redis_windows"
start redis-server.exe redis.windows.conf
timeout /t 3
redis-cli.exe config set stop-writes-on-bgsave-error no
redis-cli.exe ping
pause
