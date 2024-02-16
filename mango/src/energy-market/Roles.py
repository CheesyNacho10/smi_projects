# Roles.py
import random
from mango import Role
import mango.messages.codecs as codecs
from dataclasses import dataclass

CYCLE_TIME = 5

@codecs.json_serializable
@dataclass
class ConsumptionRequest:
    consumption_value: float

@codecs.json_serializable
@dataclass
class ProductionOffer:
    production_value: float

@codecs.json_serializable
@dataclass
class ConsumptionConfirmation:
    consumption_value: float

@codecs.json_serializable
@dataclass
class FinalConfirmation:
    final_value: float

def get_codecs():
    codec = codecs.JSON()
    codec.add_serializer(*ConsumptionRequest.__serializer__())
    codec.add_serializer(*ProductionOffer.__serializer__())
    codec.add_serializer(*ConsumptionConfirmation.__serializer__())
    codec.add_serializer(*FinalConfirmation.__serializer__())
    return codec

class ConsumerRole(Role):
    def __init__(self, contacts=[]):
        self.contacts = contacts
        self.consumption_value = 0
        self.offers_list = []
        self.requesting = False

    def setup(self):
        self.context.subscribe_message(
            self, self.handle_production_offer,
            lambda content, meta: isinstance(content, ProductionOffer)
        )
        self.context.subscribe_message(
            self, self.handle_final_confirmation,
            lambda content, meta: isinstance(content, FinalConfirmation)
        )
        self.context.schedule_periodic_task(self.request_energy, CYCLE_TIME)

    async def request_energy(self):
        if self.requesting:
            return
        self.requesting = True
        self.consumption_value = random.uniform(50, 100)
        for addr, aid in self.contacts:
            await self.context.send_acl_message(
                content=ConsumptionRequest(self.consumption_value),
                receiver_addr=addr,
                receiver_id=aid,
            )
    
    def handle_production_offer(self, content, meta):
        if not self.requesting:
            return
        if content.production_value >= self.consumption_value:
            asked_value = self.consumption_value
        else:
            asked_value = content.production_value

        self.offers_list.append((asked_value, meta["sender_addr"], meta["sender_id"]))
        if len(self.offers_list) == len(self.contacts):
            energy_to_buy = self.consumption_value
            for value, addr, aid in self.offers_list:
                if energy_to_buy > 0:
                    if value <= energy_to_buy:
                        value_to_buy = value
                    else:
                        value_to_buy = energy_to_buy
                    energy_to_buy -= value_to_buy
                    self.context.schedule_instant_task(
                        self.context.send_acl_message(
                            content=ConsumptionConfirmation(value_to_buy),
                            receiver_addr=addr,
                            receiver_id=aid,
                        )
                    )

    def handle_final_confirmation(self, content, meta):
        if not self.requesting:
            return
        self.request_energy -= content.final_value        
        print(f"Final confirmation received: {content.final_value}")

        if self.request_energy <= 0:
            self.requesting = False
            print("Cycle completed")
        

class ProducerRole(Role):
    def __init__(self, production_range=(20, 50)):
        self.production_range = production_range
        self.current_production = random.uniform(*self.production_range)

    def setup(self):
        self.context.subscribe_message(self, self.handle_consumption_request,
            lambda content, meta: isinstance(content, ConsumptionRequest))
        self.context.subscribe_message(self, self.handle_confirmation_request,
            lambda content, meta: isinstance(content, ConsumptionConfirmation))


    def handle_consumption_request(self, content, meta):
        offer = min(content.consumption_value, self.current_production)
        self.context.schedule_instant_task(
            self.context.send_acl_message(
                content=ProductionOffer(offer),
                receiver_addr=meta["sender_addr"],
                receiver_id=meta["sender_id"],
            )
        )

    def handle_confirmation_request(self, content, meta):
        self.current_production -= content.consumption_value
        self.context.schedule_instant_task(
            self.context.send_acl_message(
                content=FinalConfirmation(content.consumption_value),
                receiver_addr=meta["sender_addr"],
                receiver_id=meta["sender_id"],
            )
        )
        print(f"Final confirmation sent: {content.consumption_value}")
        self.current_production += random.uniform(*self.production_range)
