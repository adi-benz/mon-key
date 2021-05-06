import faulthandler

from sifaka import Sifaka


faulthandler.enable()


def main():
    Sifaka().start()


if __name__ == '__main__':
    main()
