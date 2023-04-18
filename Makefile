.PHONY: build-pythonpackage dev-requirements format help release release-push \
        release-tag release-unsafe requirements test test-format test-install \
        test-lint test-pythonpackage test-types upgrade version docs

.DEFAULT_GOAL := help

SRC_DIRS = ./tutorsuperset
PACKAGE=tutorsuperset
PROJECT=tutor-contrib-superset
SOURCES=./setup.py ./$(PACKAGE)
UPGRADE=CUSTOM_COMPILE_COMMAND='make upgrade' pip-compile --upgrade
BLACK_OPTS = --exclude templates ${SRC_DIRS}

###### Development

COMMON_CONSTRAINTS_TXT=requirements/common_constraints.txt
.PHONY: $(COMMON_CONSTRAINTS_TXT)
$(COMMON_CONSTRAINTS_TXT):
	wget -O "$(@)" https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints.txt || touch "$(@)"

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: $(COMMON_CONSTRAINTS_TXT)
	## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -qr requirements/pip-tools.txt
	$(UPGRADE) --allow-unsafe --rebuild -o requirements/pip.txt requirements/pip.in
	$(UPGRADE) -o requirements/pip-tools.txt requirements/pip-tools.in
	pip install -qr requirements/pip.txt
	pip install -r requirements/pip-tools.txt
	$(UPGRADE) -o requirements/base.txt requirements/base.in
	$(UPGRADE) -o requirements/dev.txt requirements/dev.in

requirements: ## Install packages from base requirement files
	pip install -r requirements/pip.txt
	pip install -r requirements/base.txt
	pip uninstall --yes $(PROJECT)
	pip install .

dev-requirements: ## Install packages from developer requirement files
	pip install -r requirements/pip.txt
	pip install -r requirements/dev.txt
	pip uninstall --yes $(PROJECT)
	pip install -e .

build-pythonpackage: ## Build Python packages ready to upload to pypi
	python setup.py sdist bdist_wheel

# Warning: These checks are not necessarily run on every PR.
test: test-lint test-install test-types test-format test-pythonpackage ## Run all tests by decreasing order of priority

test-format: ## Run code formatting tests
	black --check --diff $(BLACK_OPTS)

test-lint: ## Run code linting tests
	pylint --errors-only --enable=unused-import,unused-argument --ignore=templates --ignore=docs/_ext ${SRC_DIRS}

test-types: ## Run type checks.
	mypy --exclude=templates --ignore-missing-imports --implicit-reexport --strict ${SRC_DIRS}

test-pythonpackage: build-pythonpackage ## Test that package can be uploaded to pypi
	twine check dist/$(PROJECT)-$(shell make version).tar.gz

format: ## Format code automatically
	black $(BLACK_OPTS)

isort: ##  Sort imports. This target is not mandatory because the output may be incompatible with black formatting. Provided for convenience purposes.
	isort --skip=templates ${SRC_DIRS}

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'

###### Deployment

release: test release-unsafe ## Create a release tag and push it to origin
release-unsafe:
	$(MAKE) release-tag release-push TAG=v$(shell make version)
release-tag:
	@echo "=== Creating tag $(TAG)"
	git tag -d $(TAG) || true
	git tag $(TAG)
release-push:
	@echo "=== Pushing tag $(TAG) to origin"
	git push origin
	git push origin :$(TAG) || true
	git push origin $(TAG)

###### Additional commands

version: ## Print the current tutor version
	@python -c 'import io, os; about = {}; exec(io.open(os.path.join("$(PACKAGE)", "__about__.py"), "rt", encoding="utf-8").read(), about); print(about["__version__"])'
