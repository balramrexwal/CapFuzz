"""
Main
"""
import sys
import signal
import argparse
import tornado.ioloop


from mitmproxy import (
    options,
    exceptions
)

from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.proxy.server import ProxyServer

from fuzzer.fuzz_engine import run_fuzzer

from core.proxy import (
    ProxyHandler
)
from core.utils import (
    get_flow_file
)
from web.controllers.fuzz_progress import ScanProgress
from web.controllers.main_controller import Application
import settings

APPSERVER = None
WEBSERVER = None


def signal_handler(*args, **kwargs):
    try:
        APPSERVER.shutdown()
    except:
        pass
    try:
        tornado.ioloop.IOLoop.instance().stop()
    except:
        pass
    sys.exit(0)


def start_proxy(port, mode, flow_file_name):
    """
    Start Proxy
    Capture / Intercept
    """
    mitm_proxy_opts = options.Options()
    mitm_proxy_opts.keepserving = True
    mitm_proxy_opts.listen_port = port
    if settings.UPSTREAM_PROXY:
        mitm_proxy_opts.mode = settings.UPSTREAM_PROXY_CONF
        mitm_proxy_opts.ssl_insecure = settings.UPSTREAM_PROXY_SSL_INSECURE
    APPSERVER = ProxyHandler(mitm_proxy_opts, mode, flow_file_name)
    APPSERVER.server = ProxyServer(ProxyConfig(mitm_proxy_opts))
    # needed or not?
    # proxy_server.addons.trigger("configure", mitm_proxy_opts.keys())
    # proxy_server.addons.trigger("tick")
    APPSERVER.run()


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument(
        "-m", "--mode", help="Supported modes\n1. capture: Capture requests.\n2. fuzz: Run Fuzzing Server.\n3. runfuzz: Fuzz on captured requests with default configuration.\n4. intercept: Intercept and tamper the flow in live.")
    PARSER.add_argument("-p", "--port", help="Proxy Port",
                        default=settings.PORT, type=int)
    PARSER.add_argument("-n", "--name", help="Project Name",
                        default="default")
    ARGS = PARSER.parse_args()
    if ARGS.mode:
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            if ARGS.mode == "capture" or ARGS.mode == "intercept":
                start_proxy(ARGS.port, ARGS.mode, ARGS.name)

            elif ARGS.mode == "fuzz":
                print("Running Web GUI at *:%d" % ARGS.port)
                WEBSERVER = Application()
                WEBSERVER.listen(ARGS.port)
                tornado.ioloop.IOLoop.current().start()

            elif ARGS.mode == "runfuzz":
                if ARGS.name:
                    FLOW_FILE = get_flow_file(ARGS.name)
                else:
                    FLOW_FILE = get_flow_file("default")
                FUZZ_OPTS = {}
                FUZZ_OPTS["mode"] = ARGS.mode
                FUZZ_OPTS["include_scope"] = []
                FUZZ_OPTS["exclude_scope"] = []
                FUZZ_OPTS["exclude_url_match"] = "on"
                FUZZ_OPTS["exclude_extensions"] = "on"
                FUZZ_OPTS["exclude_response_code"] = "on"
                FUZZ_OPTS["active_fuzzers"] = ["all"]
                FUZZ_OPTS["flow_file"] = FLOW_FILE
                FUZZ_OPTS["write"] = ScanProgress.write
                run_fuzzer(FUZZ_OPTS)
            else:
                PARSER.print_help()
        except (KeyboardInterrupt, RuntimeError) as e:
            pass
        except exceptions.ServerException as exp:
            print(exp)
            sys.exit(0)
        except Exception as exp:
            print("[ERROR] " + str(exp))
    else:
        PARSER.print_help()