PYTHON ?= python

.PHONY: test verify figures slides

test:
	cd study && $(PYTHON) -m unittest discover -s tests -v

verify:
	cd study && $(PYTHON) verify_delivery.py
	cd study && $(PYTHON) verify_exploration.py
	cd study && $(PYTHON) verify_integrated_report.py

figures:
	$(PYTHON) slides/scripts/make_figures.py

slides:
	npm run slides
