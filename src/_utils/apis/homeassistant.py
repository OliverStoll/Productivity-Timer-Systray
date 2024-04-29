import requests
import threading


from src._utils.logger import create_logger


class HomeAssistantHandler:
    def __init__(self, base_url: str):
        self.log = create_logger("Home Assistant")
        self.base_url = base_url

    def trigger_webhook(self, url: str):
        """Trigger a webhook using threading"""
        thread = threading.Thread(target=self._trigger_webhook, args=(url,))
        thread.start()

    def _trigger_webhook(self, url: str):
        """Trigger a webhook in Home Assistant"""
        url = f"{self.base_url}/api/webhook/{url}"
        try:
            requests.post(url, timeout=1)
        except requests.ConnectionError:
            self.log.warning(f"Connection Error sending webhook {url}")
        except Exception as e:
            self.log.error(f"Unexpected Error sending webhook {url}: {e}")