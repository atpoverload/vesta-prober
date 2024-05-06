dtrace-jdk/bin/java  -XX:+ExtendedDTraceProbes -jar lib/dacapo.jar sunflow -n 1 & # > /dev/null 2> /dev/null &
python -m vesta --pid $! --probes probes.txt
