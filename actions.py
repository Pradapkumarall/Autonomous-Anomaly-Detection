import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActionSimulator:
    """
    Action Layer for Self-Healing
    Executes simulated REST APIs, SSH, and Webhooks based on the diagnosed root cause.
    """
    def __init__(self, human_in_loop=True):
        self.human_in_loop = human_in_loop

    def auto_scale(self, context: Dict[str, Any]) -> str:
        logger.info(f"Executing Auto-Scale action for context: {context['root_cause']}")
        return "Auto-scaling executed successfully via REST API."

    def restart_service(self, context: Dict[str, Any]) -> str:
        logger.info(f"Executing Service Restart via SSH for context: {context['root_cause']}")
        return "Service restarted successfully via SSH."

    def block_transaction(self, context: Dict[str, Any]) -> str:
        logger.warning(f"CRITICAL: Executing Fraud Block for context: {context['root_cause']}")
        if self.human_in_loop:
            logger.info("Human-in-the-loop flag active. Action pending manual approval.")
            return "Pending Manual Approval (Human-in-the-loop)"
        return "Transaction blocked successfully via Webhook."

    def execute_action(self, action_type: str, context: Dict[str, Any]) -> str:
        if action_type == "auto_scale":
            return self.auto_scale(context)
        elif action_type == "restart_service":
            return self.restart_service(context)
        elif action_type == "block_transaction":
            return self.block_transaction(context)
        elif action_type == "none":
            return "No action required."
        else:
            return f"Unknown action: {action_type}"
