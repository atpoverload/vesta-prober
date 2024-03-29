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
