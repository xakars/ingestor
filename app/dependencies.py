from fastapi import Request


def get_kafka(request: Request):
    return request.app.state.kafka_service
