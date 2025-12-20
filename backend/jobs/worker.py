from redis import Redis
from rq import Queue, Worker

redis_conn = Redis(host="localhost", port=6379)

if __name__ == "__main__":
    Worker([Queue("default")], connection=redis_conn).work()