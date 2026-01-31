#!/bin/bash
# Build Will Schultz's TLC fork with JSON state graph dump support.
# https://github.com/will62794/tlaplus/commits/multi-inv-checking-et-al/

set -e

cd "$(dirname "$0")"

JAVA_HOME=/opt/homebrew/Cellar/openjdk@11/11.0.28
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

if [ ! -d "tlaplus" ]; then
    git clone --branch multi-inv-checking-et-al --single-branch \
        https://github.com/will62794/tlaplus.git
fi

cd tlaplus/tlatools/org.lamport.tlatools
mkdir -p test-class
ant -f customBuild.xml info compile dist
