@ECHO OFF
set SOURCEDIR=source
set BUILDDIR=build
if "%SPHINXBUILD%" == "" set SPHINXBUILD=sphinx-build

%SPHINXBUILD% -W --keep-going -b html %SOURCEDIR% %BUILDDIR%/html %SPHINXOPTS%
if errorlevel 1 exit /b 1
%SPHINXBUILD% -W --keep-going -b doctest %SOURCEDIR% %BUILDDIR%/doctest %SPHINXOPTS%