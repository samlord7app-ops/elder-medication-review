"""Windows package entry point. Opens only the loopback workspace."""
import local_api
import sys
import urllib.request
import webbrowser

if __name__ == '__main__':
    try:
        local_api.main(open_browser='--no-browser' not in sys.argv)
    except OSError:
        try:
            with urllib.request.urlopen(f'{local_api.ORIGIN}/api/session', timeout=2) as r:
                if r.status == 200 and '--no-browser' not in sys.argv:
                    print(f'Local service is already running at {local_api.ORIGIN}. Opening browser...')
                    webbrowser.open(local_api.ORIGIN)
                    raise SystemExit(0)
        except Exception:
            pass
        print('Cannot start local service. Check whether port 18743 is already in use.')
        input('Press Enter to close. No clinical data was logged.')
