import copy

from bcc import BPF, USDT


PAGE_COUNT = 2048

BPF_HEADER = """
#include <uapi/linux/ptrace.h>
#include <linux/types.h>

struct data_t {
    u32 pid;
    u64 ts;
    char probe[100];
    char comm[100];
};

BPF_PERF_OUTPUT(vm_shutdown);
BPF_PERF_OUTPUT(events);

int notify_shutdown(void *ctx) {
     struct data_t data = {};
     data.pid = bpf_get_current_pid_tgid();
     data.ts = bpf_ktime_get_ns();
     bpf_get_current_comm(&data.comm, sizeof(data.comm));
     vm_shutdown.perf_submit(ctx, &data, sizeof(data));
     return 0;
}
"""

BPF_PROBE_HOOK = """

int notify_%s(void *ctx) {
    struct data_t data = {};
    data.pid = bpf_get_current_pid_tgid();
    data.ts = bpf_ktime_get_ns();
    strcpy(data.probe, "%s");
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}
"""


def create_tracing_program(usdts):
    return '\n'.join([BPF_HEADER] + [BPF_PROBE_HOOK % (usdt, usdt) for usdt in usdts])


class VestaProbeTracer:
    def __init__(self, pid, probes=[], page_count=PAGE_COUNT):
        self.usdt = USDT(pid=pid)

        self.usdt_probes = [probe for probe in probes if ':' not in probes]
        self.tracepoints = [probe for probe in probes if ':' in probes]
        self.page_count = page_count

        self.data = {}
        self.code = create_tracing_program(
            self.usdt_probes + [tp.split(':')[1] for tp in self.tracepoints])

    def start(self):
        self.is_running = True
        self.usdt.enable_probe(probe='vm__shutdown', fn_name='notify_shutdown')
        for usdt_probe in self.usdt_probes:
            self.usdt.enable_probe(
                probe=usdt_probe, fn_name='notify_%s' % usdt_probe)

        self.bpf = BPF(text=self.code, usdt_contexts=[self.usdt])

        for tracepoint in self.tracepoints:
            self.bpf.attach_tracepoint(
                tp=tracepoint, fn_name=f"notify_{tracepoint.split(':')[1]}")
        self.bpf['events'].open_perf_buffer(
            self._tracing_hook, page_cnt=self.page_count)
        self.bpf['vm_shutdown'].open_perf_buffer(
            self._shutdown_hook, page_cnt=self.page_count)

    def wait(self, timeout=1):
        self.bpf.perf_buffer_poll(timeout)

    def read(self):
        return copy.copy(self.data)

    def _tracing_hook(self, cpu, data, size):
        event = self.bpf['events'].event(data)
        probe = event.probe.decode('utf-8')
        if probe not in self.data:
            self.data[probe] = []
        self.data[probe].append({
            'pid': event.pid,
            'event_time': event.ts,
        })

    def _shutdown_hook(self, cpu, data, size):
        self.is_running = False
