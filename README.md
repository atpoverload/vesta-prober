# vesta prober

Install `bpf` and `bcc` following the instructions in [here](https://github.com/iovisor/bcc/blob/master/INSTALL.md).

The install the library with:

```bash
pip install .
```

Then you can run it on a dtrace enabled version of Java with:

```bash
dtrace-java -jar /path/to/application.jar & sudo python -m vesta --probes probes.txt --pid $! --file /output/data/vesta.json
```

The output data will contain a dictionary of probes with the probe caller and calling time:

```json
{
    "GetObjectClass__entry": [
        {"pid": 1, "event_time": 1},
        {"pid": 1, "event_time": 3},
        {"pid": 1, "event_time": 5}
    ],
    "GetObjectClass__return": [
        {"pid": 1, "event_time": 2},
        {"pid": 1, "event_time": 6},
        {"pid": 1, "event_time": 7}
    ],
    ...
}
```
