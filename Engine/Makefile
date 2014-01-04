#
# Makefile for CuraEngine
#

CXX ?= g++
CFLAGS += -I. -c -Wall -Wextra -O3 -fomit-frame-pointer
# also include debug symbols
#CFLAGS+=-ggdb
LDFLAGS +=
SOURCES  = gcodeExport.cpp infill.cpp main.cpp settings.cpp
SOURCES += clipper/clipper.cpp utils/gettime.cpp utils/logoutput.cpp
OBJECTS = $(SOURCES:.cpp=.o)
EXECUTABLE = ./Engine
UNAME := $(shell uname)

ifeq ($(UNAME), Linux)
	OPEN_HTML=firefox
	LDFLAGS += --static
endif
ifeq ($(UNAME), Darwin)
	OPEN_HTML=open
	#For MacOS force to build
	CFLAGS += -force_cpusubtype_ALL -mmacosx-version-min=10.6 -arch x86_64 -arch i386
	LDFLAGS += -force_cpusubtype_ALL -mmacosx-version-min=10.6 -arch x86_64 -arch i386
endif
ifeq ($(UNAME), MINGW32_NT-6.1)
	#For windows make it large address aware, which allows the process to use more then 2GB of memory.
	EXECUTABLE := $(EXECUTABLE).exe
	CFLAGS += -march=pentium4
	LDFLAGS += -Wl,--large-address-aware -lm
endif

all: $(SOURCES) $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	$(CXX) $(LDFLAGS) $(OBJECTS) -o $@

.cpp.o:
	$(CXX) $(CFLAGS) $< -o $@

test: $(EXECUTABLE)
	python _tests/runtest.py $(abspath $(EXECUTABLE))

## clean stuff
clean:
	rm -f $(EXECUTABLE) $(OBJECTS)

help:
	@cat Makefile |grep \#\#| grep \: |cut -d\# -f3
