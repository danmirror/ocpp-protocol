
import asyncio
import logging
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys
    sys.exit(1)

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.v16 import call_result
import requests

logging.basicConfig(level=logging.INFO)

# urls = "https://server.gowithmecs.site/api/v1/"

urls = "http://127.0.0.1:8000/api/v1/"

# url = "http://ocpp.gowithmecs.site/connect.php"
# url = "http://localhost/iot-ocpp/connect.php"
class ChargePoint(cp):
    cpID = ""

    @on(Action.Authorize)
    async def on_authorize(self, id_tag: str):
        print('\n  ============= authorized=============')
        print("id_tag", id_tag)
        url = urls+"authorized"

        # sen data
        print(url)
        payload={}
        headers = {
            'id_tag': id_tag
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)

        Dict = {
            "expiryDate": "",
            "parentIdTag": "",
            "status": response.json()["status"]
        }

        return call_result.AuthorizePayload(
            id_tag_info= Dict
        )

    @on(Action.StartTransaction)
    async def start_transaction(self, connector_id: int, id_tag: str, meter_start:int, reservation_id:int, **kwargs):
        print('\n  ============= StartTransaction=============')

        print("connector_id", connector_id)
        print("id_tag", id_tag)
        print("meter_start", meter_start)
        print("reservation_id", reservation_id)
        
        
        url = urls+"starttransaction"

        # send data
        print(url)
        payload={}
        headers = {
            'connector_id': str(connector_id),
            'id_tag': id_tag,
            'meter_start': str(meter_start),
            'reservation_id': str(reservation_id)
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)

        Dict = {
            "expiryDate": "",
            "parentIdTag": "",
            "status": response.json()["status"]
        }


        return call_result.StartTransactionPayload(
            transaction_id= 1,
            id_tag_info= Dict
        )

    @on(Action.StopTransaction)
    async def stop_transaction(self, id_tag: str, meter_stop:int, transaction_id:int, timestamp:str, **kwargs):
        print('\n  ============= StopTransaction=============')

        print("id_tag", id_tag)
        print("meter_stop", meter_stop)
        print("transaction_id", transaction_id)
        
        
        url = urls+"stoptransaction"

        # send data
        print(url)
        payload={}
        headers = {
            'id_tag': id_tag,
            'meter_stop': str(meter_stop),
            'transaction_id': str(transaction_id),
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)

        Dict = {
            "expiryDate": "",
            "parentIdTag": "",
            "status": response.json()["status"]
        }


        return call_result.StopTransactionPayload(
            id_tag_info= Dict
        )

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        # url = "http://127.0.0.1:8000/api/v1/"
        print('\n  ============= BootNotification=============')
        url = urls+"bootnotification"

        print(url)
        payload={}
        headers = {
            'model': charge_point_model,
            'id': self.cpID,
            'vendor': charge_point_vendor,
            'series': kwargs["charge_point_serial_number"],
            'firmware': kwargs["firmware_version"],
        # 'IDLog': 'avt014',
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)

        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=1000,
            status=RegistrationStatus.accepted
        )
    
    @on(Action.Heartbeat)
    async def on_heartbeat(self, **kwargs):  # receives empty payload from CP
        
        print('\n  ============= Heartbeat=============')
        print("id", self.cpID)
        print(kwargs)

        url = urls+"heartbeat"
        payload={
        
        }
        files=[
        ]
        headers = {
            'IDLog': self.cpID,
        }

        response = requests.request("POST", url, headers=headers, data=payload, files=files)
        print(response.text)

        return call_result.HeartbeatPayload(
                current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    
    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id: int,
                                     error_code: str, status: str, **kwargs):
        print('\n ============= status notification =============')

        print("id ", connector_id)
        print("error_code ", error_code)
        print("status ", status)
        print("info ",kwargs["info"])
        print("id ", connector_id)
        print("vendorId ", kwargs["vendor_id"])


        # url = "http://127.0.0.1:8000/api/v1/"
        url = urls+"statusnotification"
        payload={}
        headers = {
            'IDST': self.cpID,
            'connectorId': str(connector_id),
            'errorCode': error_code,
            'info': kwargs["info"],
            'status': status,
            'vendorId': kwargs["vendor_id"],
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)

        return call_result.StatusNotificationPayload()


async def on_connect(websocket, path):
    """ For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.

    """
    
    try:
        requested_protocols = websocket.request_headers[
            'Sec-WebSocket-Protocol']
    except KeyError:
        logging.error(
            "Client hasn't requested any Subprotocol. Closing Connection"
        )
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning('Protocols Mismatched | Expected Subprotocols: %s,'
                        ' but client supports  %s | Closing connection',
                        websocket.available_subprotocols,
                        requested_protocols)
        return await websocket.close()

    ChargePoint.cpID = path.strip('/')
    cp = ChargePoint(ChargePoint.cpID, websocket)
    


    await cp.start()


async def main():
    server = await websockets.serve(
        on_connect,
        '0.0.0.0',
        9000,
        subprotocols=['ocpp1.6']
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    futures = [main()]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(futures))

    # asyncio.run(main())