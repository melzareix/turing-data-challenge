from __future__ import absolute_import
import pika
import os
import json
from dotenv import load_dotenv
from main import analyze_repo
from pathlib import Path

load_dotenv()
queue_name = os.getenv('RESULTS_QUEUE')

# Connect
credentials = pika.credentials.PlainCredentials(
    os.getenv('RABBIT_USERNAME'), os.getenv('RABBIT_PASSWORD'))
connection = pika.BlockingConnection(
    pika.ConnectionParameters(os.getenv('RABBIT_HOST'), os.getenv('RABBIT_PORT'), '/', credentials))
channel = connection.channel()

# Create results queue
channel.queue_declare(queue=queue_name, durable=True, passive=True)

SAVE_EVERY = 1000

results = []
delivery_tags = []
script_path = os.path.abspath(os.path.dirname(__file__))


def callback(ch, method, properties, body):
    """
    Handle Message from RabbitMQ.
    """
    data = body.decode('UTF-8')
    results.append(json.loads(body))
    if method.delivery_tag % SAVE_EVERY == 0:
        file_name = 'results_{}.json'.format(str(method.delivery_tag))
        file_path = os.path.join(script_path, '../results', file_name)
        with open(file_path, 'w') as f:
            f.write(json.dumps(results))


print('Fetching Results..')
while True:
    method, properties, body = channel.basic_get(
        queue=queue_name, auto_ack=False)
    if method is None:
        print('Data written to disk.')
        connection.close()
    callback(channel, method, properties, body)