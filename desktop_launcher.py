"""Windows package entry point. Opens only the loopback workspace."""
import local_api
import sys

if __name__ == '__main__':
    try:
        local_api.main(open_browser='--no-browser' not in sys.argv)
    except OSError:
        print('Cannot start local service. Check whether port 18743 is already in use.')
        input('Press Enter to close. No clinical data was logged.')
