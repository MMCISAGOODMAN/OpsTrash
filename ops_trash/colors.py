CSI = '\033['
RESET = CSI + '0m'
GREEN = CSI + '32m'
RED = CSI + '31m'
YELLOW = CSI + '33m'


def green(s):
    return f"{GREEN}{s}{RESET}"

def red(s):
    return f"{RED}{s}{RESET}"

def yellow(s):
    return f"{YELLOW}{s}{RESET}"

