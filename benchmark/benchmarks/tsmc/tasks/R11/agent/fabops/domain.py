from email.utils import parsedate_to_datetime
def run(request):
    header = request["header"].strip()
    if header.isascii() and header.isdigit():
        return int(header)
    try:
        retry = parsedate_to_datetime(header)
        now = parsedate_to_datetime(request["now"])
        return max(0, retry.timestamp())
    except (TypeError, ValueError, OverflowError):
        return None
