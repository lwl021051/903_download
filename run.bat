@echo off
echo ==============================================
echo Starting the audio collector script(903)
echo ==============================================


echo ==============================================
echo Default the schedule list
echo 10am-12pm
echo 3pm-4pm
echo 10pm-11pm
echo ==============================================
.\code\venv\Scripts\python.exe .\code\audio_collector.py
pause