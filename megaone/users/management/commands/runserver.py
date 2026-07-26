import socket

from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand


def _get_lan_ips() -> list[str]:
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("10.254.254.254", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    return sorted(ips)


class Command(RunserverCommand):
    help = "Starts a lightweight web server for development and displays LAN URLs"

    default_addr = "0.0.0.0"

    def on_bind(self, server_port):
        super().on_bind(server_port)

        lan_ips = _get_lan_ips()
        port = server_port

        self.stdout.write("=" * 58)
        self.stdout.write("Django Development Server Started Successfully")
        self.stdout.write("=" * 58)
        self.stdout.write("")
        self.stdout.write("  Local URLs:")
        self.stdout.write(f"    http://127.0.0.1:{port}")
        self.stdout.write(f"    http://localhost:{port}")
        if lan_ips:
            self.stdout.write("")
            self.stdout.write("  Network URLs (share with LAN devices):")
            for ip in lan_ips:
                self.stdout.write(f"    http://{ip}:{port}")
            self.stdout.write("")
            self.stdout.write(
                "  Share the Network URL with devices connected to the "
                "same Wi-Fi/LAN."
            )
        self.stdout.write("")
        self.stdout.write("=" * 58)
