import faulthandler

from smartswitch import SmartSwitch


faulthandler.enable()


def main():
    SmartSwitch().start()


if __name__ == '__main__':
    main()
