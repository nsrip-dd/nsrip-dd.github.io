MD_FILES = $(shell find . -type f -name '*.md')
HTML_FILES = $(patsubst %.md,%.html,$(MD_FILES))

.PHONY: all
all: $(HTML_FILES)

%.html : %.md
	pandoc $< -f markdown -t html -s -o $@
