import argparse
import json
import os

from time import time

from vesta import lre


def parse_args():
    parser = argparse.ArgumentParser(description='vesta probe monitor')
    parser.add_argument('-p', '--pid', type=int, help='process to monitor')
    parser.add_argument(
        '--probes',
        default='monitor__wait',
        type=str,
        help='list of comma-delimited probe names or path to a file that contains a list of probe names',
    )
    parser.add_argument(
        '--bucket_size',
        default=1000,
        type=int,
        help='millisecond bucketing size of data',
    )
    parser.add_argument(
        '--file',
        default=f'/tmp/vesta-{os.getpid()}-{int(1000 * time())}.json',
        type=str,
        help='location to write the log as a json. defaults to \'/tmp/vesta-<pid>-<unixtime>.json\'',
    )
    return parser.parse_args()


# def get_dtrace_probes():
#     with open(os.path.join(os.path.dirname(__file__), 'dtrace_probes.txt')) as f:
#         return f.read().splitlines()


def get_probes(probes):
    # dtrace_probes = get_dtrace_probes()
    if os.path.exists(probes):
        _, ext = os.path.splitext(probes)
        if ext == '.json':
            with open(probes) as f:
                probes = json.load(f)
                if isinstance(probes, dict):
                    probes['probes']
                elif not isinstance(probes, list):
                    return []
        else:
            with open(probes) as f:
                probes = list(filter(lambda l: len(
                    l) > 0, f.read().splitlines()))
    else:
        probes = probes.split(',')

    # filtered_probes = set(dtrace_probes) & set(probes)
    # if set(filtered_probes) != set(probes):
    #     print(f'removing unknown probes:')
    #     print(' '.join(list(set(probes) - set(filtered_probes))))
    return probes


def main():
    # this is here in case someone imports this file
    try:
        from .probe import VestaProbeTracer
    except ImportError as e:
        if '/bcc/' in e.msg:
            print('vesta had an error importing bcc:')
            print(e.msg)
            print('check that your installation of bpf and bcc are correct')
            return
        else:
            raise e

    args = parse_args()
    probes = get_probes(args.probes)

    print(f'monitoring probes for pid {args.pid}:')
    print(' '.join(probes))

    tracer = VestaProbeTracer(pid=args.pid, probes=probes)
    try:
        tracer.start()
        while tracer.is_running:
            tracer.wait()
        print(f'pid {args.pid} terminated')
    except KeyboardInterrupt:
        print(f'monitoring of pid {args.pid} ended by user')
    data = tracer.read()
    # print(f'writing probe data to {args.file}')
    # with open(args.file, 'w') as f:
    #     json.dump(data, f)
    print('synthesizing probes')
    probes = lre.bucket_probes(data, args.bucket_size)
    lres = lre.synthesize_probes(probes)
    lres.to_csv(args.file)


if __name__ == '__main__':
    main()
