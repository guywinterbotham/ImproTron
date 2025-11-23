@echo on
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d "C:\Users\guywi\OneDrive\Documents\git\ImproTron"
.qtcreator\Python_3_12_10venv\Scripts\activate
.qtcreator\Python_3_12_10venv\Scripts\pyside6-deploy -c ImproTron.spec