from sqlalchemy.engine import URL, make_url


def parse_database_url(value: str) -> URL:
    url = make_url(value)
    if url.drivername == "postgresql":
        return url.set(drivername="postgresql+psycopg2")
    return url
