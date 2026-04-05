from fastapi import Request


def get_kafka(request: Request):
    return request.app.state.kafka_service


def get_redis(request: Request):
    return request.app.state.redis
