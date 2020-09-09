"""
Deletes empty folders in a directory
"""
import logging
import pathlib


def remove_empty_folder(path: pathlib.Path) -> None:
    for i in path.iterdir():
        if i.is_dir():
            remove_empty_folder(i)
            try:
                i.rmdir()
            except IOError:
                logging.info("Directory at {} is not empty.".format(i))


def main():
    import argparse

    # setup command line parsing
    parser = argparse.ArgumentParser(description="Deletes empty folders in a directory.")
    parser.add_argument("src_dir", type=str, help="source directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="output logging information", dest="verbose")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(20)
    else:
        logging.getLogger().setLevel(40)
    path = pathlib.Path(args.src_dir)
    if not path.exists():
        raise IOError("Path does not exist at {}.".format(path))
    remove_empty_folder(path)


if __name__ == "__main__":
    main()
