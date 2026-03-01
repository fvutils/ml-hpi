# Minimal makefile for Sphinx documentation

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help clean Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -rf $(BUILDDIR)

# Build PDF from whitepaper via pandoc before Sphinx so it lands in _static/
pdf:
	pandoc ml_hpi_whitepaper.md \
		-o _static/ml_hpi_whitepaper.pdf \
		--pdf-engine=xelatex \
		-V geometry:margin=1in \
		-V fontsize=11pt \
		-V colorlinks=true

html: pdf
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target — pass remaining targets to Sphinx
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
