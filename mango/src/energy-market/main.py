import asyncio
from mango import create_container, RoleAgent
from Roles import ConsumerRole, ProducerRole, get_codecs

CYCLE_TIME = 10

async def main():
    consumers_container = await create_container(addr=("localhost", 5555), codecs=get_codecs())
    producers_container = await create_container(addr=("localhost", 5556), codecs=get_codecs())


    producers = [
        RoleAgent(producers_container, suggested_aid="producer1"),
    ]
    producers_contacts = [
        (("localhost", 5556), producers[0].aid),
    ]

    consumers = [
        RoleAgent(consumers_container, suggested_aid="consumer1"),
    ]
    consumer_contacts = [
        (("localhost", 5555), consumers[0].aid),
    ]

    for consumer in consumers:
        consumer.add_role(ConsumerRole(contacts=producers_contacts))
    for producer in producers:
        producer.add_role(ProducerRole())

if __name__ == "__main__":
    asyncio.run(main())
