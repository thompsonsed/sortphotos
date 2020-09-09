"""
Deletes files in a directory that is not a photo.
"""
import logging

from PIL import Image
import pathlib


def check_image_with_pil(path: pathlib.Path) -> bool:
    """
    Checks if the path is an image.

    :param pathlib.Path path: path to check the image of

    :return: true if the path is an image.
    :rtype: bool
    """
    try:
        with Image.open(path) as image:
            pass
    except IOError:
        return False
    return True


def remove_file_if_image(path: pathlib.Path, test: bool = False) -> None:
    """
    Removes files in the path recursively, if they are not images.

    :param pathlib.Path path: the path to the file or directory
    :param bool test: if true, does not delete the files.

    :return: None
    :rtype: None
    """
    if path.is_dir():
        for file in path.iterdir():
            remove_file_if_image(file, test=test)
    else:
        if not check_image_with_pil(path):
            if test:
                logging.info("Would remove {}.".format(path))
            else:
                logging.info("Removing {}.".format(path))
                path.unlink()


def main():
    import argparse

    # setup command line parsing
    parser = argparse.ArgumentParser(description="Deletes files which cannot be parsed by EXIF.")
    parser.add_argument("src_dir", type=str, help="source directory")
    parser.add_argument("-t", "--test", action="store_true", help="run a test of the removal", dest="test")
    parser.add_argument("-v", "--verbose", action="store_true", help="output logging information", dest="verbose")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(20)
    else:
        logging.getLogger().setLevel(40)
    path = pathlib.Path(args.src_dir)
    if not path.exists():
        raise IOError("Path does not exist at {}.".format(path))
    remove_file_if_image(path, test=args.test)


if __name__ == "__main__":
    main()
