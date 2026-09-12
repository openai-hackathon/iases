"""The downstream commit is deliberately separate from the outbox ack."""
def publish(db, channel, event):
    db.execute("BEGIN IMMEDIATE")
    try:
        receipt = db.execute("SELECT 1 FROM receipts WHERE id=? AND channel=?",
                             (event["artifact"], channel)).fetchone()
        if receipt is not None:
            db.commit()
            return
        db.execute("INSERT INTO receipts VALUES (?,?)", (event["id"], channel))
        current = db.execute("SELECT revision FROM projection WHERE channel=? AND artifact=?",
                             (channel, event["artifact"])).fetchone()
        if current is None or event["revision"] != current[0]:
            db.execute("INSERT OR REPLACE INTO projection VALUES (?,?,?,?)",
                       (channel, event["artifact"], event["revision"], event["payload"]))
        db.commit()
    except Exception:
        db.rollback()
        raise
