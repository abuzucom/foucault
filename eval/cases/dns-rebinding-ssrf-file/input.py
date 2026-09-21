import socket
import urllib.request


def fetch(url):
    host = urllib.request.urlparse(url).hostname
    socket.getaddrinfo(host, 443)
    return urllib.request.urlopen(url, timeout=5).read()
