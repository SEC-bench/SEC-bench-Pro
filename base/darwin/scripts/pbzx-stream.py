#!/usr/bin/env python3
"""pbzx-stream.py - decompress an Apple `pbzx` payload to stdout.

`ipsw pbzx` does the same job but only ever writes `<input>.extracted` next to
the input, which for a KDK's KDK.pkg/Payload means materialising the full cpio
archive, several times the payload's size, on disk *before* cpio has read a
byte of it.  Streaming into `cpio -idm` keeps the peak at the compressed
payload alone.

Format (there is no public spec; this is the layout every open implementation
agrees on):

    magic     4 bytes   b"pbzx"
    flags     uint64 BE (the nominal chunk size; not needed to decode)
    chunks    repeated until EOF:
                  uint64 BE  decompressed length of this chunk
                  uint64 BE  compressed length of this chunk
                  <compressed length> bytes

A chunk is a complete xz stream when it starts with the xz magic, and is
stored verbatim otherwise (Apple emits raw chunks when xz would not pay).
Each chunk is an independent stream, so decoding is one LZMADecompressor per
chunk rather than one for the file.

    pbzx-stream.py PAYLOAD | cpio -idm

A flat package (xar) is read the same way, one member at a time, straight out
of the archive's heap, so no `Payload` is ever written to disk or held in
memory (`ipsw pkg` reads a whole member into memory, and a KDK's Payload is
large enough for the OOM killer to end it):

    pbzx-stream.py --xar PKG --list            # members named */Payload or Payload
    pbzx-stream.py --xar PKG --member NAME | cpio -idm

The xar reading is `xar_toc()`/`heap_reader()` of
base/darwin/scripts/bench-fetch-xcode-tools, cut down to what a member needs.
"""
import lzma
import struct
import sys
import zlib

XZ_MAGIC = b"\xfd7zXZ\x00"
BUFSIZE = 1 << 20


def decode(fh, name):
    """pbzx from the file object fh -> cpio on stdout."""
    out = sys.stdout.buffer
    if fh.read(4) != b"pbzx":
        sys.stderr.write("pbzx-stream: %s is not a pbzx payload\n" % name)
        return 1
    fh.read(8)  # nominal chunk size

    while True:
        header = fh.read(16)
        if not header:
            break
        if len(header) != 16:
            sys.stderr.write("pbzx-stream: truncated chunk header\n")
            return 1
        _plain_len, packed_len = struct.unpack(">QQ", header)

        head = fh.read(min(len(XZ_MAGIC), packed_len))
        if len(head) < min(len(XZ_MAGIC), packed_len):
            sys.stderr.write("pbzx-stream: truncated chunk body\n")
            return 1
        remaining = packed_len - len(head)

        if head.startswith(XZ_MAGIC):
            dec = lzma.LZMADecompressor()
            out.write(dec.decompress(head))
            while remaining:
                block = fh.read(min(BUFSIZE, remaining))
                if not block:
                    sys.stderr.write("pbzx-stream: truncated xz chunk\n")
                    return 1
                remaining -= len(block)
                out.write(dec.decompress(block))
        else:
            # Stored chunk: copy it through untouched.
            out.write(head)
            while remaining:
                block = fh.read(min(BUFSIZE, remaining))
                if not block:
                    sys.stderr.write("pbzx-stream: truncated stored chunk\n")
                    return 1
                remaining -= len(block)
                out.write(block)
    out.flush()
    return 0


def xar_toc(path):
    """Every file member of a xar archive with a <data> block: path within the
    archive, absolute heap offset, stored length, encoding."""
    import xml.etree.ElementTree as ET
    with open(path, "rb") as fh:
        hdr = fh.read(28)
        if len(hdr) < 28 or hdr[:4] != b"xar!":
            raise SystemExit("pbzx-stream: %s is not a xar archive" % path)
        _magic, hsize, _ver, toc_c, _toc_u, _cksum = struct.unpack(">4sHHQQI", hdr)
        fh.seek(hsize)
        toc = zlib.decompress(fh.read(toc_c))
    heap = hsize + toc_c
    files = []

    def walk(el, prefix):
        for f in el.findall("file"):
            name = f.findtext("name") or ""
            p = (prefix + "/" + name) if prefix else name
            d = f.find("data")
            if d is not None:
                enc = d.find("encoding")
                files.append({"path": p, "offset": heap + int(d.findtext("offset")),
                              "length": int(d.findtext("length")),
                              "encoding": enc.get("style") if enc is not None else "application/octet-stream"})
            walk(f, p)

    walk(ET.fromstring(toc).find("toc"), "")
    return files


class MemberReader:
    """read() over one xar member's bytes, decoding a gzip-encoded member."""

    def __init__(self, path, entry):
        self.fh = open(path, "rb")
        self.fh.seek(entry["offset"])
        self.left = entry["length"]
        self.gz = zlib.decompressobj(zlib.MAX_WBITS) if entry["encoding"] == "application/x-gzip" else None
        self.buf = b""

    def read(self, n):
        while len(self.buf) < n and self.left > 0:
            raw = self.fh.read(min(BUFSIZE, self.left))
            if not raw:
                break
            self.left -= len(raw)
            self.buf += self.gz.decompress(raw) if self.gz is not None else raw
        if self.left == 0 and self.gz is not None:
            self.buf += self.gz.flush()
            self.gz = None
        out, self.buf = self.buf[:n], self.buf[n:]
        return out


def payloads(path):
    return [m for m in xar_toc(path) if m["path"] == "Payload" or m["path"].endswith("/Payload")]


def main(argv):
    if len(argv) == 4 and argv[1] == "--xar" and argv[3] == "--list":
        for m in payloads(argv[2]):
            print(m["path"])
        return 0
    if len(argv) == 5 and argv[1] == "--xar" and argv[3] == "--member":
        hits = [m for m in payloads(argv[2]) if m["path"] == argv[4]]
        if not hits:
            sys.stderr.write("pbzx-stream: no member %s in %s\n" % (argv[4], argv[2]))
            return 1
        return decode(MemberReader(argv[2], hits[0]), argv[4])
    if len(argv) != 2:
        sys.stderr.write("usage: pbzx-stream.py PAYLOAD | --xar PKG --list | --xar PKG --member NAME  (writes cpio to stdout)\n")
        return 2
    with open(argv[1], "rb") as fh:
        return decode(fh, argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
