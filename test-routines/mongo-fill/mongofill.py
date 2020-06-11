import pymongo
import random


def generate_random_data(max_rand, loop):
    result = {}
    for i in range(loop):
        result['test%d' % i] = random.randint(-max_rand, max_rand)
    return result


client = pymongo.MongoClient('mongodb://%s:%s@businessdb:27017' % ('admin', 'toor'))
first_round = 30000
second_round = 30000

l = []
for _ in range(first_round):
    l.append(generate_random_data(100000000, 100))
client.test.random.insert_many(l)

for _ in range(second_round):
    client.test.random.insert_one(generate_random_data(100000000, 100))

print('Database filled successfully with %d records' % (first_round + second_round))


