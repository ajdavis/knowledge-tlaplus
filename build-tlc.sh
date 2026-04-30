#!/bin/bash
# Build Will Schultz's TLC fork with JSON state graph dump support.
# https://github.com/will62794/tlaplus/commits/multi-inv-checking-et-al/

set -e

cd "$(dirname "$0")"

JAVA_HOME=/opt/homebrew/opt/openjdk
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

if [ ! -d "tlaplus" ]; then
    git clone --branch multi-inv-checking-et-al --single-branch \
        https://github.com/will62794/tlaplus.git
fi

cd tlaplus/tlatools/org.lamport.tlatools
# The `dist` target has a <fileset dir="test-class"> that bundles test helper
# classes into tla2tools.jar. It doesn't depend on compile-test (which would
# create the dir), so ant errors out if test-class/ is missing. Create it empty
# --- the fileset resolves to zero files, and we don't need those helpers.
mkdir -p test-class
ant -f customBuild.xml info compile dist
