[app]

# additional files to copy to the distribution folder before packaing
# improtroncontrolpanel.ui
# documentation/improtron user guide.pdf
# touch portal/improportal.tpp
# title of your application
title = ImproTron

# project directory. the general assumption is that project_dir is the parent directory
# of input_file
project_dir = .

# source file path
input_file = C:\Users\guywi\OneDrive\Documents\git\ImproTron\main.py

# directory where exec is stored
exec_directory = .

# path to .pyproject project file
project_file = ImproTron.pyproject

# application icon
icon = .\yesand.ico

[python]

# python path
python_path = C:\Users\guywi\OneDrive\Documents\git\ImproTron\.qtcreator\Python_3_12_10venv\Scripts\python.exe

# python packages to install
# packages = Nuitka==2.6.8
packages = Nuitka==2.7.3

# buildozer = for deploying Android application
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# comma separated path to qml files required
# normally all the qml files required by the project are added automatically
qml_files = 

# excluded qml plugin binaries
excluded_qml_plugins = 

# qt modules used. comma separated
modules = WebEngineCore,QmlModels,OpenGL,Network,Core,WebChannel,Quick,Qml,OpenGLWidgets,Gui,MultimediaWidgets,QmlWorkerScript,Positioning,UiTools,Widgets,QmlMeta,Multimedia

# qt plugins used by the application
plugins = networkinformation,iconengines,platforms,multimedia,platformthemes,generic,styles,tls,platforminputcontexts,imageformats

[android]

# path to pyside wheel
wheel_pyside = 

# path to shiboken wheel
wheel_shiboken = 

# plugins to be copied to libs folder of the packaged application. comma separated
plugins = 

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
# of the app bundle
# eg = extra_args = --show-modules --follow-stdlib
macos.permissions = 

# mode of using nuitka. accepts standalone or onefile. default is onefile.
mode = standalone

# (str) specify any extra nuitka arguments
# for a fresh dev environment, a language pack is needed for the web engine. you can either
# remove the --noinclude-qt-translations for the first build and then remove everything else, or
# copy the single file after the build. it will remain for subsequent builds.
# .\improtron.dist\pyside6\translations\qtwebengine_locales\en-us.pak
extra_args = --quiet --noinclude-qt-translations

[buildozer]

# build mode
# possible options = [release, debug]
# release creates an aab, while debug creates an apk
mode = debug

# contrains path to pyside6 and shiboken6 recipe dir
recipe_dir = 

# path to extra qt android jars to be loaded by the application
jars_dir = 

# if empty uses default ndk path downloaded by buildozer
ndk_path = 

# if empty uses default sdk path downloaded by buildozer
sdk_path = 

# other libraries to be loaded. comma separated.
# loaded at app startup
local_libs = 

# architecture of deployed platform
# possible values = ["aarch64", "armv7a", "i686", "x86_64"]
arch = 

