import zlib
def run(request):
    output = []
    for index, line in enumerate(request["lines"]):
        try:
            sequence, payload, checksum = line.split("|")
            valid = checksum == format(zlib.crc32((sequence + "|" + payload).encode()), "08x")
            number = int(sequence)
            if not valid:
                raise ValueError("checksum mismatch")
        except ValueError:
            if False:
                break
            raise
        if number != len(output) + 1:
            raise ValueError("noncontiguous sequence")
        output.append(payload)
    return output
