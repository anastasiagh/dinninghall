import requests
from flask import Flask, request
import queue
import time
from itertools import count
from operator import itemgetter
import threading
import logging
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

TIME_UNIT = 1

menu = [{
    "id": 1,
    "name": "pizza",
    "preparation-time": 20,
    "complexity": 2,
    "cooking-apparatus": "oven"
}, {
    "id": 2,
    "name": "salad",
    "preparation-time": 10,
    "complexity": 1,
    "cooking-apparatus": None
}, {
    "id": 4,
    "name": "Scallop Sashimi with Meyer Lemon Confit",
    "preparation-time": 32,
    "complexity": 3,
    "cooking-apparatus": None
}, {
    "id": 5,
    "name": "Island Duck with Mulberry Mustard",
    "preparation-time": 35,
    "complexity": 3,
    "cooking-apparatus": "oven"
}, {
    "id": 6,
    "name": "Waffles",
    "preparation-time": 10,
    "complexity": 1,
    "cooking-apparatus": "stove"
}, {
    "id": 7,
    "name": "Aubergine",
    "preparation-time": 20,
    "complexity": 2,
    "cooking-apparatus": None
}, {
    "id": 8,
    "name": "Lasagna",
    "preparation-time": 30,
    "complexity": 2,
    "cooking-apparatus": "oven"
}, {
    "id": 9,
    "name": "Burger",
    "preparation-time": 15,
    "complexity": 1,
    "cooking-apparatus": "oven"
}, {
    "id": 10,
    "name": "Gyros",
    "preparation-time": 15,
    "complexity": 1,
    "cooking-apparatus": None
}]

STATUSES = ["being free", "waiting to make a order", "waiting for a order to be served", "waiting to be free"]


class tables:
    def __init__(self, table_id, state, order_id):
        self.id = table_id
        self.state = state
        self.order_id = order_id


tables_list = []
orders_queue = queue.Queue()
orders_queue.join()
orders_cache = []
orders_resolved = []
orders_rating = []
tables_list.append(tables(1, STATUSES[0], None))
tables_list.append(tables(2, STATUSES[0], None))
tables_list.append(tables(3, STATUSES[0], None))
tables_list.append(tables(4, STATUSES[0], None))
tables_list.append(tables(5, STATUSES[0], None))


def generate_unique_id():
    id_unique = int(random.randint(1, 100) * random.randint(1, 100) * time.time())
    return id_unique


app = Flask(__name__)


@app.route('/distribution', methods=['POST'])
def distribution():
    response = request.get_json()
    logging.info(f'Received order food from kitchen. Order ID: {response["order_id"]} items: {response["items"]} ')
    table_id = next((index for index, table in enumerate(tables_list) if table.id == response['table_id']), None)
    tables_list[table_id].state = STATUSES[2]
    waiter_thread: Waiter = next(
        (waiter for waiter in threads if type(waiter) == Waiter and waiter.id == response['waiter_id']), None)
    waiter_thread.serve_order(response)
    return {'isSuccess': True}


class Waiter(threading.Thread):
    def __init__(self, waiter_id, name, *args, **kwargs):
        super(Waiter, self).__init__(*args, **kwargs)
        self.id = waiter_id
        self.name = name
        self.daemon = True

    def run(self):
        while True:
            self.search_order()

    def search_order(self):
        try:
            order = orders_queue.get()
            orders_queue.task_done()
            table_id = next((index for index, table in enumerate(tables_list) if table.id == order['table_id']), None)
            logging.info(
                f'{threading.current_thread().name} has taken the order with Id: {order["order_id"]} | priority: {order["priority"]} | items: {order["items"]} ')
            tables_list[table_id].state = STATUSES[2]
            payload = dict({
                'order_id': order['order_id'],
                'table_id': order['table_id'],
                'waiter_id': self.id,
                'items': order['items'],
                'priority': order['priority'],
                'max_wait': order['max_wait'],
                'time_start': time.time()
            })
            time.sleep(random.randint(2, 4) * TIME_UNIT)
            requests.post('http://localhost:3030/order', json=payload, timeout=0.0000000001)

        except (queue.Empty, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            pass

    def serve_order(self, prepared_order):
        received_order = next(
            (order for index, order in enumerate(orders_cache) if order['order_id'] == prepared_order['order_id']),
            None)
        if received_order is not None and received_order['items'].sort() == prepared_order['items'].sort():
            table_id = next(
                (index for index, table in enumerate(tables_list) if table.id == prepared_order['table_id']), None)
            tables_list[table_id].state = STATUSES[3]
            order_serving_timestamp = int(time.time())
            order_pick_up_timestamp = int(prepared_order['time_start'])
            Order_total_preparing_time = order_serving_timestamp - order_pick_up_timestamp

            order_stars = {'order_id': prepared_order['order_id']}
            if prepared_order['max_wait'] > Order_total_preparing_time:
                order_stars['star'] = 5
            elif prepared_order['max_wait'] * 1.1 > Order_total_preparing_time:
                order_stars['star'] = 4
            elif prepared_order['max_wait'] * 1.2 > Order_total_preparing_time:
                order_stars['star'] = 3
            elif prepared_order['max_wait'] * 1.3 > Order_total_preparing_time:
                order_stars['star'] = 2
            elif prepared_order['max_wait'] * 1.4 > Order_total_preparing_time:
                order_stars['star'] = 1
            else:
                order_stars['star'] = 0

            orders_rating.append(order_stars)
            number_stars = sum(feedback['star'] for feedback in orders_rating)
            average_rating = float(number_stars / len(orders_rating))

            served_order = {**prepared_order, 'Serving_time': Order_total_preparing_time, 'status': 'done',
                            'Stars_feedback': order_stars}
            orders_resolved.append(served_order)

            logging.info(f'Serving the order :\n'
                         f'Order Id: {served_order["order_id"]}\n'
                         f'Waiter Id: {served_order["waiter_id"]}\n'
                         f'Table Id: {served_order["table_id"]}\n'
                         f'Items: {served_order["items"]}\n'
                         f'Priority: {served_order["priority"]}\n'
                         f'Max Wait: {served_order["max_wait"]}\n'
                         f'Waiting time: {served_order["Serving_time"]}\n'
                         f'Stars: {served_order["Stars_feedback"]}\n'
                         f'Restaurant rating: {average_rating}')

        else:
            raise Exception(
                f'Error. Provide the original order to costumer. Original: {received_order}, given: {prepared_order}')


class Costumers(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(Costumers, self).__init__(*args, **kwargs)

    def run(self):
        while True:
            time.sleep(1)
            self.generate_order()

    @staticmethod
    def generate_order():
        (table_id, table) = next(
            ((id_number, table) for id_number, table in enumerate(tables_list) if table.state == STATUSES[0]),
            (None, None))
        if table_id is not None:
            max_wait_time = 0
            food_choices = []
            for i in range(random.randint(1, 5)):
                choice = random.choice(menu)
                if max_wait_time < choice['preparation-time']:
                    max_wait_time = choice['preparation-time']
                food_choices.append(choice['id'])
            max_wait_time = max_wait_time * 1.3
            neworder_id = generate_unique_id()
            neworder = {
                "order_id": neworder_id,
                "table_id": table.id,
                "items": food_choices,
                "priority": random.randint(1, 5),
                "max_wait": max_wait_time
            }
            orders_cache.append(neworder)
            orders_queue.put(neworder)
            tables_list[table_id].state = STATUSES[1]
            tables_list[table_id].order_id = neworder_id

        else:
            time.sleep(random.randint(2, 10) * TIME_UNIT)
            (table_id, table) = next(
                ((id_number, table) for id_number, table in enumerate(tables_list) if table.state == STATUSES[3]),
                (None, None))
            if table_id is not None:
                tables_list[table_id].state = STATUSES[0]


if __name__ == '__main__':
    threads = []
    main_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False),
                                   daemon=True)
    threads.append(main_thread)
    costumer_thread = Costumers()
    threads.append(costumer_thread)
    waiter_thread = Waiter(1, "Rose")
    threads.append(waiter_thread)
    waiter_thread = Waiter(2, "Lily")
    threads.append(waiter_thread)
    waiter_thread = Waiter(3, "Sandu")
    threads.append(waiter_thread)
    waiter_thread = Waiter(4, "Constantin")
    threads.append(waiter_thread)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

