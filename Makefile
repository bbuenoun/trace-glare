# Concise introduction to GNU Make:
# https://swcarpentry.github.io/make-novice/reference.html

name = glare-trace

# Taken from https://www.client9.com/self-documenting-makefiles/
help : ## Print this help
	@awk -F ':|##' '/^[^\t].+?:.*?##/ {\
		printf "\033[36m%-30s\033[0m %s\n", $$1, $$NF \
	}' $(MAKEFILE_LIST)
.PHONY : help
.DEFAULT_GOAL := help

# --------------------- #
# Interface with Docker #
# --------------------- #

name : ## Print value of variable `name`
	@echo ${name}
.PHONY : name

build : ## Build image with name `${name}`
	docker build \
		--tag ${name} \
		--build-arg GROUP_ID=$(shell id --group) \
		--build-arg USER_ID=$(shell id --user) \
		.
.PHONY : build

remove : ## Remove image with name `${name}`
	docker rmi ${name}
.PHONY : remove

# Inspired by http://wiki.ros.org/docker/Tutorials/GUI#The_isolated_way
run : xsock = /tmp/.X11-unix
run : xauth = /tmp/.docker.xauth
run : build ## Run command `${COMMAND}` in fresh container, for example, `make COMMAND='ls --all | wc --lines' run`
	touch /tmp/.docker.xauth
	xauth nlist $${DISPLAY} | sed -e 's/^..../ffff/' | xauth -f ${xauth} nmerge -
	docker run \
		--interactive \
		--tty \
		--user $(shell id --user):$(shell id --group) \
		--mount type=bind,source=$(shell pwd),target=/app \
		--env DISPLAY \
		--env XAUTHORITY=${xauth} \
		--mount type=bind,source=${xsock},target=${xsock},readonly=false \
		--mount type=bind,source=${xauth},target=${xauth},readonly=false \
		${name} \
		bash -c "${COMMAND}"
.PHONY : run

shell : COMMAND = bash
shell : run ## Enter (B)ourne (a)gain (sh)ell, also known as Bash, in fresh container
.PHONY : shell

# ------------------------------------------------ #
# Tasks to run, for example, in a Docker container #
# ------------------------------------------------ #

tests : ## Run tests
	python3 -m pytest ./tests
.PHONY : tests

doctests: ## Run doctests
	python3 -m pytest \
		--doctest-modules \
		--doctest-continue-on-failure \
		--assert=plain \
		./glare
.PHONY : doctests

types : ## Type check the code
	mypy --strict .
.PHONY : types

lint : ## Lint the code
	pylint ./glare ./docs ./tests
.PHONY : lint

dead : ## Find dead code
	vulture .
.PHONY : dead

format: ## Format the code
	black --target-version py37 .
.PHONY : format

docs: ## Generate documentation
	rm -rf ./docs/source
	rm -rf ./docs/html
	sphinx-apidoc \
		--force \
		-o ./docs/source \
		./glare
	sphinx-build \
		-b html \
		./docs \
		./docs/html
.PHONY : docs
