import logging

from src.biblio.app import build_app
from src.biblio.utils.parser import get_parser


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = get_parser()
    args = parser.parse_args()
    build_app(
        token_env=args.token_env, priorities_env=args.priorities_env, sheet_env=args.sheet_env, auth_mode=args.auth_mode
    )


if __name__ == '__main__':
    main()
