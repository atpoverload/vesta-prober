import argparse
import json
import os

import pandas as pd


def normalize_timestamps(timestamps, bucket_size_ms):
    """ normalizes ns timestamps to ms-bucketed timestamps """
    # TODO: this is producing strange behavior due to int division:
    #   2938450289096200 // 10**6 = 2938450288
    return bucket_size_ms * (timestamps // 10**6 // bucket_size_ms)


def bucket_probes(probes, bucket_size_ms):
    """ sums the number of probe events for each probe into ts buckets """
    probes = probes.copy()
    probes['ts'] = normalize_timestamps(probes.event_time, bucket_size_ms)
    probes = probes.groupby(['ts', 'probe']).event_time.count()
    probes.name = 'events'

    return probes


SYNTHESIZABLE_TOKEN_PAIRS = [
    ['begin', 'entry'],  # begin tokens
    ['end', 'return'],  # end tokens
]

PROBE_DELIM = '__'


def to_probe_kinds(probe_kinds):
    """ strips the last part of the probe names (begin/end) """
    return probe_kinds.str.split(PROBE_DELIM).str[:-1].str.join(PROBE_DELIM)


def is_synthesizable(probe_kinds):
    """ checks if a collection of probes can be synthesized """
    if len(probe_kinds) != 2:
        return False

    probe_tokens = zip(probe_kinds, SYNTHESIZABLE_TOKEN_PAIRS)
    is_synthesizable_pair = [any(token in kind for token in tokens)
                             for kind, tokens in probe_tokens]
    return all(is_synthesizable_pair)


def get_probe_kinds(probe_kinds):
    """ extracts a mapping of a probe kind """
    probe_kinds = pd.concat([to_probe_kinds(probe_kinds), probe_kinds], axis=1)
    probe_kinds.columns = ['probe_kind', 'probe']
    probe_kinds = probe_kinds.groupby('probe_kind').probe.unique().to_dict()
    probe_kinds = {kind: list(
        probe_kinds[kind]) for kind in probe_kinds if kind != '' and is_synthesizable(probe_kinds[kind])}
    return probe_kinds


# TODO: this is a mess
def synthesize_probes(probes):
    """ synthesizes a collection of probes

    Synthesis is done by grouping together probes of the same "kind" and computing
    the difference between the "begin" and "end" probes of the same kind.
    """
    probe_kinds = get_probe_kinds(probes.reset_index().probe)
    if len(probe_kinds) == 0:
        return pd.DataFrame(columns=['ts', 'probe'])

    synthesized = []
    probes = probes.unstack(fill_value=0)
    for kind, probe_names in probe_kinds.items():
        df = probes[probe_names]
        # diff will do begin - end, so we have to flip things a little bit
        df = df.min(axis=1) - df.diff(axis=1).iloc[:, -1].cumsum()
        df.name = kind
        synthesized.append(df)

    synthesized = pd.concat(synthesized, axis=1).reset_index()
    synthesized = synthesized.set_index('ts')
    synthesized.columns.name = 'event'

    return synthesized.stack()


def parse_args():
    parser = argparse.ArgumentParser(description='vesta probe monitor')
    parser.add_argument(
        '-b',
        '--bucket_size',
        type=int,
        help='millisecond bucketing size of data'
    )
    parser.add_argument(
        nargs='*',
        type=str,
        help='vesta probing data files',
        dest='files',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    for file in args.files:
        with open(file, 'r') as f:
            data = json.load(f)
        probes = bucket_probes(data, args.bucket_size)
        lres = synthesize_probes(probes)
        lres.to_csv('{}-lre.{}'.format(*os.path.splitext(file)))


if __name__ == '__main__':
    main()
