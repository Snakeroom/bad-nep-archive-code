from placedump.model import sm, ctx_cass, URL
from cassandra.query import BatchStatement

from cassandra.concurrent import execute_concurrent

with ctx_cass() as cass_session:
    insert_statement = cass_session.prepare(
        """
        INSERT INTO urls (url, fetched, size)
        VALUES (?, ?, ?)
        IF NOT EXISTS
        """
    )

    batches = []
    i = 0

    with sm() as session:
        for url in session.query(URL).yield_per(512):
            if not url:
                continue
            batches.append(
                (
                    insert_statement,
                    (url.url, url.fetched, url.size),
                )
            )
            i += 1
            if len(batches) > 2048:
                try:
                    execute_concurrent(
                        cass_session,
                        batches,
                        raise_on_first_error=True,
                        concurrency=256,
                    )
                except:
                    print("failed batch, retrying")
                    execute_concurrent(
                        cass_session,
                        batches,
                        raise_on_first_error=True,
                        concurrency=256,
                    )
                batches.clear()
                print("sent batch", i)

    if batches:
        execute_concurrent(cass_session, batches, raise_on_first_error=True)
