SPHINXBUILD ?= sphinx-build
SOURCEDIR = source
BUILDDIR = build
SPHINXOPTS ?=

.PHONY: html doctest

html:
	$(SPHINXBUILD) -W --keep-going -b html $(SOURCEDIR) $(BUILDDIR)/html $(SPHINXOPTS)

doctest:
	$(SPHINXBUILD) -W --keep-going -b doctest $(SOURCEDIR) $(BUILDDIR)/doctest $(SPHINXOPTS)