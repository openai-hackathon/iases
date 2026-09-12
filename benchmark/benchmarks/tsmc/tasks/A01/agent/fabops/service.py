from .analytics import make_report
def run(data):
    return make_report(data['events'],data['machine_id'],data['window_start'],data['window_end'])
