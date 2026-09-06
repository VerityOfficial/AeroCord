import json
import threading
import time

import requests
import websocket


DISCORD_API = "https://discord.com/api/v10"


class DiscordGatewayClient(object):
    def __init__(self, token, on_ready_callback=None, on_event_callback=None):
        self.token = token
        self.on_ready_callback = on_ready_callback
        self.on_event_callback = on_event_callback

        self.ws = None
        self.heartbeat_interval = None
        self.is_running = False
        self.sequence = None
        self.session_id = None

    def get_gateway_url(self):
        try:
            response = requests.get(
                DISCORD_API + "/gateway/bot",
                headers={
                    "Authorization": "Bot " + self.token
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("url")

        except Exception as e:
            print("Gateway URL error:", e)

        return None

    def start(self):
        if self.is_running:
            return

        self.is_running = True

        gateway_url = self.get_gateway_url()

        if not gateway_url:
            print("Could not get Discord Gateway URL.")
            self.is_running = False
            return

        gateway_url += "?v=10&encoding=json"

        self.ws = websocket.WebSocketApp(
            gateway_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        thread = threading.Thread(
            target=self.ws.run_forever
        )

        thread.daemon = True
        thread.start()

    def on_open(self, ws):
        print("Connected to Discord Gateway.")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
        except Exception as e:
            print("Invalid Gateway message:", e)
            return

        op = data.get("op")
        event_type = data.get("t")
        payload = data.get("d")

        if "s" in data:
            self.sequence = data["s"]

        # HELLO
        if op == 10:
            self.heartbeat_interval = (
                payload["heartbeat_interval"] / 1000.0
            )

            heartbeat_thread = threading.Thread(
                target=self.heartbeat_loop
            )

            heartbeat_thread.daemon = True
            heartbeat_thread.start()

            self.send_identify()

        # HEARTBEAT requested by Discord
        elif op == 1:
            self.send_heartbeat()

        # HEARTBEAT ACK
        elif op == 11:
            pass

        # DISPATCH event
        elif op == 0:
            if event_type == "READY":
                self.session_id = payload.get("session_id")

                guilds = payload.get("guilds", [])

                print(
                    "Gateway READY - %d guilds received."
                    % len(guilds)
                )

                if self.on_ready_callback:
                    self.on_ready_callback(guilds)

            if self.on_event_callback:
                self.on_event_callback(
                    event_type,
                    payload
                )

        # INVALID SESSION
        elif op == 9:
            print("Discord rejected the Gateway session.")

            self.is_running = False

            try:
                self.ws.close()
            except Exception:
                pass

    def send_identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "intents": 0,
                "properties": {
                    "os": "windows",
                    "browser": "aerocord",
                    "device": "aerocord"
                }
            }
        }

        try:
            self.ws.send(json.dumps(payload))
            print("Gateway IDENTIFY sent.")
        except Exception as e:
            print("IDENTIFY error:", e)

    def send_heartbeat(self):
        if not self.ws:
            return

        payload = {
            "op": 1,
            "d": self.sequence
        }

        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            print("Heartbeat error:", e)

    def heartbeat_loop(self):
        while self.is_running:
            if not self.heartbeat_interval:
                break

            time.sleep(self.heartbeat_interval)

            if not self.is_running:
                break

            self.send_heartbeat()

    def on_error(self, ws, error):
        print("Gateway error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print(
            "Gateway closed: %s - %s"
            % (close_status_code, close_msg)
        )

        self.is_running = False

    def stop(self):
        self.is_running = False

        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

        self.ws = None