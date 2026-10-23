import os

import psycopg2
from dotenv import load_dotenv


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    connection = psycopg2.connect(database_url)
    connection.close()
    print("Connected to the database successfully.")


if __name__ == "__main__":
    main()
