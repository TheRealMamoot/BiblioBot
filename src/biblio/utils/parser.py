import argparse


def get_parser():
    parser = argparse.ArgumentParser(description='App')
    parser.add_argument(
        '--token-env',
        type=str,
        default='prod',
        choices=['prod', 'staging'],
    )
    parser.add_argument(
        '--priorities-env',
        type=str,
        default='prod',
        choices=['prod', 'local'],
    )
    parser.add_argument(
        '--sheet-env',
        type=str,
        default='prod',
        choices=['prod', 'test', 'staging'],
    )
    parser.add_argument(
        '--auth-mode',
        type=str,
        default='prod',
        choices=['prod', 'local'],
    )
    return parser
