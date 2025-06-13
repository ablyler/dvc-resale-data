import json
import logging
import hashlib
from typing import Dict, Any, List
from azure.storage.queue import QueueClient
from azure.core.exceptions import ResourceExistsError
from datetime import datetime, timedelta
import base64

logger = logging.getLogger(__name__)

class ROFRQueueManager:
    """Queue manager for complete thread processing."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.queue_name = "rofr-thread-processing"
        self.stats_queue_name = "rofr-statistics-update"

        self.queue_client = QueueClient.from_connection_string(
            conn_str=connection_string,
            queue_name=self.queue_name
        )

        self.stats_queue_client = QueueClient.from_connection_string(
            conn_str=connection_string,
            queue_name=self.stats_queue_name
        )

        self._ensure_queues_exist()
        logger.info("ROFR Queue Manager initialized for complete thread processing")

    def _ensure_queues_exist(self):
        """Ensure all required queues exist."""
        queues = [
            (self.queue_client, self.queue_name),
            (self.stats_queue_client, self.stats_queue_name)
        ]

        for queue_client, queue_name in queues:
            try:
                queue_client.create_queue()
                logger.info(f"Created queue: {queue_name}")
            except ResourceExistsError:
                logger.debug(f"Queue {queue_name} already exists")
            except Exception as e:
                logger.error(f"Error creating queue {queue_name}: {e}")
                raise

    def add_thread_task(self, thread_info: Dict[str, Any], session_id: str) -> bool:
        """Add a complete thread processing task to the queue."""
        try:
            # Validate input parameters
            if not thread_info or not isinstance(thread_info, dict):
                logger.error("Invalid thread_info: must be a non-empty dictionary")
                return False

            if not session_id or not isinstance(session_id, str):
                logger.error("Invalid session_id: must be a non-empty string")
                return False

            task_data = {
                "thread_info": thread_info,
                "session_id": session_id,
                "task_type": "complete_thread",
                "created_at": datetime.utcnow().isoformat(),
                "thread_title": thread_info.get("title", "Unknown Thread")
            }

            task_json = json.dumps(task_data)

            # Validate JSON is not empty
            if not task_json or task_json.strip() == "":
                logger.error("Generated JSON is empty")
                return False

            task_base64 = base64.b64encode(task_json.encode('utf-8')).decode('utf-8')

            # Validate base64 encoding worked
            if not task_base64 or task_base64.strip() == "":
                logger.error("Base64 encoding resulted in empty string")
                return False

            logger.info(f"Sending message with length: {len(task_base64)}")
            logger.debug(f"Message preview: {task_base64[:100]}...")

            self.queue_client.send_message(
                content=task_base64,
                visibility_timeout=None,
                time_to_live=86400
            )

            logger.info(f"Added complete thread task: {thread_info.get('title', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Error adding thread task: {e}")
            return False

    def add_stats_update_task(self, trigger_info: str) -> bool:
        """Add a statistics update task to the queue."""
        try:
            # Validate input parameters
            if not trigger_info or not isinstance(trigger_info, str):
                logger.error("Invalid trigger_info: must be a non-empty string")
                return False

            stats_task = {
                "task_type": "statistics_update",
                "trigger_info": trigger_info,
                "created_at": datetime.utcnow().isoformat()
            }

            task_json = json.dumps(stats_task)

            # Validate JSON is not empty
            if not task_json or task_json.strip() == "":
                logger.error("Generated stats JSON is empty")
                return False

            task_base64 = base64.b64encode(task_json.encode('utf-8')).decode('utf-8')

            # Validate base64 encoding worked
            if not task_base64 or task_base64.strip() == "":
                logger.error("Stats base64 encoding resulted in empty string")
                return False

            logger.info(f"Sending stats message with length: {len(task_base64)}")
            logger.debug(f"Stats message preview: {task_base64[:100]}...")

            self.stats_queue_client.send_message(
                content=task_base64,
                visibility_timeout=None,
                time_to_live=3600
            )

            logger.info(f"Added statistics update task: {trigger_info}")
            return True

        except Exception as e:
            logger.error(f"Error adding statistics update task: {e}")
            return False

    def create_processing_session(self, session_name: str, thread_urls: List[str]) -> str:
        """Create a new processing session for a group of threads."""
        session_id = hashlib.md5(f"{session_name}_{datetime.utcnow().isoformat()}".encode()).hexdigest()
        logger.info(f"Created processing session: {session_id} with {len(thread_urls)} threads")
        return session_id
