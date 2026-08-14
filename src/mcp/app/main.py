import logging

from .server import create_server

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

server = create_server()
app = server.streamable_http_app()


def main() -> None:
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
